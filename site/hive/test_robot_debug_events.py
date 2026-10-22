import json
import threading
from types import SimpleNamespace
from unittest.mock import MagicMock

from django.test import SimpleTestCase

from .mqtt.moxie_server import MoxieServer


class RobotDebugEventTests(SimpleTestCase):
    def setUp(self):
        self.server = MoxieServer.__new__(MoxieServer)
        self.server._debug_lock = threading.Lock()
        self.server._debug_records = {}
        self.server._status_lock = threading.Lock()
        self.server._status = {}
        self.server.on_device_state = MagicMock()
        self.server.on_client_metrics = MagicMock()

    def test_robot_telemetry_is_separate_from_broker_metrics_and_other_robots(self):
        self.server.on_message(None, None, SimpleNamespace(topic='/devices/d_a/state', payload=b'{}'))
        before = self.server.robot_debug_snapshot('d_a')
        self.server.on_message(None, None, SimpleNamespace(topic='$SYS/broker/clients/active', payload=b'2'))
        self.server.on_message(None, None, SimpleNamespace(topic='/devices/d_b/state', payload=b'{}'))
        self.assertEqual(before, self.server.robot_debug_snapshot('d_a'))
        self.assertIsNotNone(before['last_telemetry_at'])
        self.assertEqual(before['last_topic'], 'state')

    def test_events_are_bounded_and_snapshot_cannot_modify_record(self):
        for index in range(120):
            self.server._note_robot_debug('d_a', 'mode', f'Mode transition {index}')
        snapshot = self.server.robot_debug_snapshot('d_a')
        self.assertEqual(len(snapshot['events']), 80)
        snapshot['events'][0]['message'] = 'changed'
        self.assertNotEqual(self.server.robot_debug_snapshot('d_a')['events'][0]['message'], 'changed')
        for index in range(40):
            self.server._note_robot_debug(f'd_{index}', 'connection', 'Connected')
        self.assertLessEqual(len(self.server._debug_records), 32)

    def test_repeated_events_are_coalesced(self):
        for _ in range(100):
            self.server._note_robot_debug('d_a', 'assets', 'Robot reported local asset bundle activity.')
        self.assertEqual(len(self.server.robot_debug_snapshot('d_a')['events']), 1)

    def test_known_robot_fault_uses_fixed_text_without_payload(self):
        self.server.check_device_connect = MagicMock(return_value=None)
        self.server.on_device_event('d_a', 'device-logs', SimpleNamespace(payload=json.dumps({
            'message': 'std::regex_error password=private family speech secret', 'tag': 'Unity',
        }).encode()))
        snapshot = self.server.robot_debug_snapshot('d_a')
        self.assertEqual(snapshot['events'][0]['level'], 'error')
        self.assertNotIn('private', json.dumps(snapshot))
        self.assertNotIn('family speech', json.dumps(snapshot))
