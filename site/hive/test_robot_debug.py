from datetime import timedelta
from unittest.mock import Mock, patch

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import MoxieDevice, RobotCommandEvent
from .robot_debug import build_robot_debug


class RobotDebugTests(TestCase):
    def setUp(self):
        self.device = MoxieDevice.objects.create(device_id='d_test', name='Moxie')
        self.now = timezone.now()
        self.service = Mock()
        self.service.service_status.return_value = {
            'broker_connected': True, 'connected_devices': ['d_test'],
            'devices': {'d_test': {'mode': 'sleep'}},
        }
        self.service.robot_debug_snapshot.return_value = {'events': []}

    def test_browser_poll_does_not_create_robot_telemetry(self):
        first = build_robot_debug(self.device, self.service, self.now)
        second = build_robot_debug(self.device, self.service, self.now + timedelta(seconds=5))
        self.assertIsNone(first['connection']['last_telemetry_at'])
        self.assertIsNone(second['connection']['last_telemetry_at'])
        self.assertEqual(second['summary']['title'], 'Connected; waiting for telemetry')
        self.assertNotEqual(first['generated_at'], second['generated_at'])

    def test_fresh_robot_activity_is_distinct_from_old_state(self):
        self.device.state_updated = self.now - timedelta(minutes=5)
        self.device.state = {'mode': 'sleep', 'battery_level': 0.8}
        self.service.robot_debug_snapshot.return_value = {
            'last_telemetry_at': self.now.isoformat(), 'events': [],
        }
        data = build_robot_debug(self.device, self.service, self.now)
        self.assertEqual(data['connection']['telemetry_age_seconds'], 0)
        self.assertEqual(data['summary']['title'], 'Robot reports sleep')
        self.assertEqual(data['state']['battery_level'], 0.8)
        self.assertEqual(data['connection']['last_state_at'], self.device.state_updated.isoformat())

    def test_broker_outage_overrides_cached_online_flag(self):
        self.service.service_status.return_value['broker_connected'] = False
        data = build_robot_debug(self.device, self.service, self.now)
        self.assertFalse(data['connection']['online'])
        self.assertEqual(data['connection']['mode'], 'offline')

    def test_connection_placeholder_does_not_override_last_reported_mode(self):
        self.device.state = {'mode': 'sleep'}
        self.device.state_updated = self.now - timedelta(minutes=5)
        self.service.service_status.return_value['devices']['d_test'] = {
            'mode': 'connecting', 'last_state': None,
        }
        data = build_robot_debug(self.device, self.service, self.now)
        self.assertEqual(data['connection']['mode'], 'sleep')
        self.assertEqual(data['connection']['last_mode_at'], self.device.state_updated.isoformat())

    def test_private_payloads_and_other_robot_commands_are_excluded(self):
        self.device.state = {'mode': 'sleep', 'battery_level': 50,
                             'api_key': 'private-key', 'text': 'private conversation',
                             'software_version': 'secret phrase with spaces'}
        RobotCommandEvent.objects.create(device=self.device, action='wake', status='queued',
                                         label='private label', detail='private payload')
        other = MoxieDevice.objects.create(device_id='d_other')
        RobotCommandEvent.objects.create(device=other, action='other_robot_command')
        data = build_robot_debug(self.device, self.service, self.now)
        self.assertEqual(data['state'], {'mode': 'sleep', 'battery_level': 50})
        self.assertEqual(len(data['commands']), 1)
        self.assertNotIn('private', str(data))
        self.assertNotIn('other_robot_command', str(data))

    def test_quiet_and_offline_are_separate(self):
        self.device.state_updated = self.now - timedelta(minutes=10)
        quiet = build_robot_debug(self.device, self.service, self.now)
        self.assertTrue(quiet['connection']['online'])
        self.assertTrue(quiet['connection']['telemetry_stale'])
        self.service.service_status.return_value['connected_devices'] = []
        offline = build_robot_debug(self.device, self.service, self.now)
        self.assertFalse(offline['connection']['online'])
        self.assertEqual(offline['summary']['title'], 'Robot offline')

    @patch('hive.views.get_instance')
    def test_endpoint_is_read_only_and_never_cached(self, get_instance):
        get_instance.return_value = self.service
        url = reverse('hive:robot_debug', args=[self.device.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Cache-Control'], 'no-store')
        self.assertEqual(self.client.post(url).status_code, 405)
        self.assertEqual(RobotCommandEvent.objects.count(), 0)

    @patch('hive.views.get_instance', return_value=None)
    def test_endpoint_handles_unstarted_service(self, _get_instance):
        response = self.client.get(reverse('hive:robot_debug', args=[self.device.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()['connection']['online'])
