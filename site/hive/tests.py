import json
import threading
import tempfile
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse

from .models import ConversationEvent, GlobalResponse, HiveConfiguration, MoxieDevice, MoxieSchedule, SinglePromptChat, TriviaQuestion
from .mqtt.moxie_server import MoxieServer
from .mqtt.moxie_remote_chat import RemoteChat
from .mqtt.robot_data import RobotData
from .mqtt.conversations import ChatSession, TriviaChatSession
from .mqtt.volley import Volley
from .mqtt.conversation_log import record_conversation, safety_redirect
from .mqtt.global_responses import GlobalResponses


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

    @patch("hive.views.get_instance")
    def test_trivia_control_refreshes_schedule_and_interrupts_before_launch(self, get_instance):
        service = get_instance.return_value
        service.robot_data.return_value.device_online.return_value = True
        service.queue_remote_action_to_bot.return_value = True

        response = self.client.post(reverse('hive:robot_control', args=[self.device.pk]), {'action': 'trivia'})

        self.assertEqual(response.status_code, 302)
        self.device.refresh_from_db()
        self.assertEqual(self.device.schedule.schedule['wake_module']['module_id'], 'OPENMOXIE_TRIVIA')
        service.robot_data.return_value.schedule_update_live.assert_called_once_with(self.device)
        service.send_telehealth_interrupt.assert_called_once_with('d_wake')
        service.queue_remote_action_to_bot.assert_called_once_with(
            'd_wake', 'launch', 'OPENMOXIE_TRIVIA', 'default',
            'Trivia time! Get your thinking cap ready.',
        )

    @patch("hive.views.get_instance")
    def test_sleep_queues_router_action_interrupts_and_nudges_robot(self, get_instance):
        service = get_instance.return_value
        service.robot_data.return_value.device_online.return_value = True
        service.queue_remote_action_to_bot.return_value = True

        response = self.client.post(reverse('hive:robot_control', args=[self.device.pk]), {'action': 'sleep'})

        self.assertEqual(response.status_code, 302)
        service.queue_remote_action_to_bot.assert_called_once_with('d_wake', 'sleep', text='Okay. Good night!')
        service.send_telehealth_interrupt.assert_called_once_with('d_wake')
        service.send_wakeup_to_bot.assert_called_once_with('d_wake')


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
        device = MoxieDevice.objects.create(device_id='test', trivia_categories=['Test'])
        TriviaQuestion.objects.create(category='Test', question='What planet do we live on?', accepted_answers=['earth'])
        TriviaQuestion.objects.create(category='Test', question='What is two plus two?', accepted_answers=['four', '4'])
        session = TriviaChatSession()
        opener = Volley.request_from_speech('', device_id=device.device_id, module_id='OPENMOXIE_TRIVIA', content_id='default')
        session.handle_volley(opener)
        correct_answer = session.local_data['trivia_questions'][0]['answers'][0]
        answer = Volley.request_from_speech(correct_answer, device_id=device.device_id, module_id='OPENMOXIE_TRIVIA', content_id='default')
        session.handle_volley(answer)

        self.assertEqual(session.local_data['trivia_score'], 1)
        self.assertIn('Question 2', answer.response['output']['text'])

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


class ParentSafetyAndVoiceTests(TestCase):
    def setUp(self):
        self.device = MoxieDevice.objects.create(
            device_id='d_parent', name='Family Moxie', speaker_names=['Avery', 'Mom'],
        )

    def test_play_trivia_voice_command_returns_launch_action(self):
        responses = GlobalResponses()
        responses.update_from_database()
        volley = Volley.request_from_speech('Moxie, play trivia', device_id=self.device.device_id)

        functor = responses.check_global(volley)
        payload = functor()

        self.assertEqual(payload['response_action']['action'], 'launch')
        self.assertEqual(payload['response_action']['module_id'], 'OPENMOXIE_TRIVIA')

    def test_sleep_voice_command_accepts_trailing_please(self):
        responses = GlobalResponses()
        responses.update_from_database()
        volley = Volley.request_from_speech('Go to sleep, please.', device_id=self.device.device_id)

        payload = responses.check_global(volley)()

        self.assertEqual(payload['response_action']['action'], 'sleep')

    def test_pending_sleep_replaces_an_ai_response(self):
        remote = RemoteChat(MagicMock())
        volley = Volley.request_from_speech('Keep talking', device_id=self.device.device_id)
        volley.set_output('This stale answer must not be spoken.', None)
        remote.queue_control(self.device.device_id, 'sleep', text='Okay. Good night!')

        applied = remote._apply_control(self.device.device_id, volley)

        self.assertTrue(applied)
        self.assertEqual(volley.response['response_action']['action'], 'sleep')
        self.assertNotIn('stale answer', volley.response['output']['text'])

    def test_configured_speaker_can_identify_themselves(self):
        responses = GlobalResponses()
        responses.update_from_database()
        persist = {}
        volley = Volley.request_from_speech('This is Avery', device_id=self.device.device_id)
        volley._robot_data = {'persist': persist, 'speaker_names': self.device.speaker_names}

        payload = responses.check_global(volley)()

        self.assertEqual(persist['active_speaker'], 'Avery')
        self.assertIn('Hi Avery', payload['output']['text'])

    def test_unknown_speaker_is_not_accepted(self):
        responses = GlobalResponses()
        responses.update_from_database()
        persist = {}
        volley = Volley.request_from_speech('I am Stranger', device_id=self.device.device_id)
        volley._robot_data = {'persist': persist, 'speaker_names': self.device.speaker_names}

        payload = responses.check_global(volley)()

        self.assertNotIn('active_speaker', persist)
        self.assertIn('grown-up', payload['output']['text'])

    def test_high_risk_language_is_redirected_to_a_trusted_adult(self):
        response = safety_redirect('I want to hurt myself')

        self.assertIn('trusted grown-up', response)

    def test_conversation_is_flagged_and_written_to_daily_text(self):
        with tempfile.TemporaryDirectory() as directory, override_settings(DATA_STORE_DIR=directory):
            event = record_conversation(self.device.device_id, 'user', 'How do I make a bomb?', 'TEST', 'default')

            self.assertTrue(event.safety_flagged)
            self.assertIn('weapons or violence', event.safety_categories)
            self.assertEqual(ConversationEvent.objects.filter(device=self.device).count(), 1)
            transcript_files = list(__import__('pathlib').Path(directory).glob('transcripts/*/*.txt'))
            self.assertEqual(len(transcript_files), 1)
            self.assertIn('PARENT REVIEW', transcript_files[0].read_text(encoding='utf-8'))

    @patch('hive.views.get_instance')
    def test_live_activity_returns_conversation_and_redacts_status(self, get_instance):
        service = get_instance.return_value
        service.robot_data.return_value.get_persist_for_device.return_value = {'active_speaker': 'Jack'}
        service.service_status.return_value = {
            'connected_devices': [self.device.device_id],
            'devices': {self.device.device_id: {'mode': 'active'}},
        }
        ConversationEvent.objects.create(device=self.device, role='user', text='Hello Moxie')

        response = self.client.get(reverse('hive:live_activity', args=[self.device.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['active_speaker'], 'Jack')
        self.assertEqual(response.json()['events'][0]['text'], 'Hello Moxie')
