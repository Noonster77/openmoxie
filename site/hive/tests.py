import json
import threading
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from .models import HiveConfiguration, MoxieDevice, MoxieSchedule, SinglePromptChat
from .mqtt.moxie_server import MoxieServer
from .mqtt.robot_data import RobotData
from .mqtt.conversations import ChatSession, TriviaChatSession
from .mqtt.volley import Volley


class MQTTServiceTests(SimpleTestCase):
    def test_connect_is_async_and_starts_retry_loop(self):
        server = MoxieServer.__new__(MoxieServer)
        server._robot = SimpleNamespace(create_jwt=lambda project: "token")
        server._mqtt_project_id = "openmoxie"
        server._mqtt_endpoint = "mqtt"
        server._port = 8883
        server._client = MagicMock()

        server.connect(start=True)

        server._client.connect_async.assert_called_once_with("mqtt", 8883, 60)
        server._client.reconnect_delay_set.assert_called_once_with(min_delay=1, max_delay=30)
        server._client.loop_start.assert_called_once()

    def test_device_state_topic_is_parsed_without_confusing_sys_topics(self):
        server = MoxieServer.__new__(MoxieServer)
        server._status_lock = threading.Lock()
        server._status = {}
        server.on_device_state = MagicMock()
        server.on_device_event = MagicMock()
        server.on_client_metrics = MagicMock()
        server.on_sys_log_message = MagicMock()
        message = SimpleNamespace(
            topic="/devices/d_abc123/state",
            payload=json.dumps({"battery_level": 50}).encode(),
        )

        server.on_message(None, None, message)

        server.on_device_state.assert_called_once_with("d_abc123", message)
        self.assertEqual(server._status["last_device_id"], "d_abc123")

    def test_background_errors_are_exposed_in_service_status(self):
        server = MoxieServer.__new__(MoxieServer)
        server._status_lock = threading.Lock()
        server._status = {"last_processing_error": None}
        server._worker_queue = ThreadPoolExecutor(max_workers=1)

        def broken_task():
            raise ValueError("bad robot state")

        future = server._submit_worker(broken_task)
        with self.assertRaises(ValueError):
            future.result(timeout=2)
        server._worker_queue.shutdown()

        self.assertIn("bad robot state", server._status["last_processing_error"])

    @patch("hive.views.get_instance", return_value=None)
    def test_connection_status_reports_supervisor_not_started(self, get_instance):
        response = self.client.get(reverse("hive:connection_status"))

        self.assertEqual(response.status_code, 503)
        self.assertFalse(response.json()["broker_connected"])


class RobotStateTests(TestCase):
    def test_first_partial_state_does_not_crash_when_previous_state_is_null(self):
        device = MoxieDevice.objects.create(device_id="d_first_state")
        robot_data = RobotData.__new__(RobotData)

        robot_data.update_state_atomic(device.device_id, {"awake": True})

        device.refresh_from_db()
        self.assertEqual(device.state, {"awake": True})

    def test_connected_details_include_live_mode(self):
        robot_data = RobotData.__new__(RobotData)
        robot_data._robot_map = {
            "d_live": {
                "state": {"mode": "sleep"},
                "state_received_at": "2026-08-17T18:00:00+00:00",
            }
        }

        self.assertEqual(robot_data.connected_details()["d_live"]["mode"], "sleep")


class WakeControlTests(TestCase):
    def setUp(self):
        self.schedule = MoxieSchedule.objects.create(name="test", schedule={"provided_schedule": []})
        self.device = MoxieDevice.objects.create(device_id="d_wake", schedule=self.schedule)

    @patch("hive.views.get_instance")
    def test_wake_enables_button_support_before_sending_command(self, get_instance):
        service = get_instance.return_value
        service.send_wakeup_to_bot.return_value = True

        response = self.client.post(reverse("hive:moxie_wake", args=[self.device.pk]))

        self.assertEqual(response.status_code, 302)
        self.device.refresh_from_db()
        self.assertTrue(self.device.robot_config["wake_button_enabled"])
        service.handle_config_updated.assert_called_once()
        service.send_wakeup_to_bot.assert_called_once_with("d_wake")

    @patch("hive.views.get_instance")
    def test_wake_chat_creates_chat_wake_schedule(self, get_instance):
        get_instance.return_value.send_wakeup_to_bot.return_value = True

        response = self.client.post(reverse("hive:moxie_wake_chat", args=[self.device.pk]))

        self.assertEqual(response.status_code, 302)
        self.device.refresh_from_db()
        self.assertEqual(
            self.device.schedule.schedule["wake_module"],
            {"module_id": "OPENMOXIE_CHAT", "content_id": "default"},
        )


class LocalAIAndMissionTests(TestCase):
    @patch("hive.views.get_instance")
    def test_setup_saves_independent_local_chat_and_stt_choices(self, get_instance):
        response = self.client.post(reverse('hive:hive_configure'), {
            'apikey': '', 'googleapikey': '', 'hostname': 'moxie-pc',
            'chat_provider': 'lmstudio',
            'chat_base_url': 'http://host.docker.internal:1234/v1',
            'chat_model': 'qwen-local',
            'stt_provider': 'local',
            'local_stt_model': 'small.en',
        })

        self.assertEqual(response.status_code, 302)
        config = HiveConfiguration.objects.get(name='default')
        self.assertEqual(config.chat_provider, 'lmstudio')
        self.assertEqual(config.stt_provider, 'local')

    def test_history_limit_mutates_the_actual_history(self):
        session = ChatSession(max_history=2)
        session.add_history('user', 'one')
        session.add_history('assistant', 'two')
        session.add_history('user', 'three')

        self.assertEqual([item['content'] for item in session._history], ['two', 'three'])

    def test_trivia_scores_correct_answer_and_asks_next_question(self):
        session = TriviaChatSession()
        opener = Volley.request_from_speech('', device_id='test', module_id='OPENMOXIE_TRIVIA', content_id='default')
        session.handle_volley(opener)
        answer = Volley.request_from_speech('We live on Earth', device_id='test', module_id='OPENMOXIE_TRIVIA', content_id='default')
        session.handle_volley(answer)

        self.assertIn('Correct', answer.response['output']['text'])
        self.assertIn('score is 1 out of 1', answer.response['output']['text'])

    @patch("hive.views.get_instance")
    def test_launcher_sets_selected_remote_mission_as_wake_module(self, get_instance):
        schedule = MoxieSchedule.objects.create(name='base', schedule={'provided_schedule': []})
        device = MoxieDevice.objects.create(device_id='d_launch', schedule=schedule)
        SinglePromptChat.objects.create(name='Trivia', module_id='OPENMOXIE_TRIVIA', content_id='default', opener='Hi', prompt='Trivia')
        get_instance.return_value.send_wakeup_to_bot.return_value = False

        response = self.client.post(reverse('hive:launch_mission', args=[device.pk]), {
            'module_id': 'OPENMOXIE_TRIVIA', 'content_id': 'default',
        })

        self.assertEqual(response.status_code, 302)
        device.refresh_from_db()
        self.assertEqual(device.schedule.schedule['wake_module'], {
            'module_id': 'OPENMOXIE_TRIVIA', 'content_id': 'default',
        })
