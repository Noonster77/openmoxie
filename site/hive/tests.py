import json
import threading
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from .models import MoxieDevice, MoxieSchedule
from .mqtt.moxie_server import MoxieServer
from .mqtt.robot_data import RobotData


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
