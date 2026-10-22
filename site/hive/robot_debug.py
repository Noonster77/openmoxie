"""Read-only robot diagnostics assembled from evidence, never browser polling."""
import math
import re

from django.utils import timezone
from django.utils.dateparse import parse_datetime


def _iso(value):
    return value.isoformat() if value else None


def _time(value):
    if isinstance(value, str):
        try:
            value = parse_datetime(value)
        except ValueError:
            return None
    if value and timezone.is_naive(value):
        value = timezone.make_aware(value)
    return value


def _token(value):
    """Only identifiers belong in diagnostics; never arbitrary robot text."""
    if isinstance(value, str) and re.fullmatch(r'[A-Za-z0-9_.:/-]{1,80}', value):
        return value
    return None


def safe_state(raw):
    result = {}
    if not isinstance(raw, dict):
        return result
    for key in ('mode', 'power_state', 'charging', 'is_charging', 'battery_level',
                'battery_voltage', 'software_version', 'firmware_version'):
        value = raw.get(key)
        if isinstance(value, bool) or isinstance(value, (int, float)) and math.isfinite(value):
            result[key] = value
        elif _token(value) is not None:
            result[key] = value
    return result


COMMAND_DETAILS = {
    'sent': 'Command sent; robot confirmation may still be pending.',
    'pending': 'Waiting for the robot to receive or confirm this command.',
    'confirmed': 'Robot activity confirmed this command.',
    'failed': 'Command could not be delivered or completed.',
    'offline': 'Robot was disconnected when this command was requested.',
    'queued': 'Command queued; delivery is not confirmation.',
}


def build_robot_debug(device, service, now=None):
    now = now or timezone.now()
    status = service.service_status() if service else {}
    diagnostics = service.robot_debug_snapshot(device.device_id) if service else {}
    broker_connected = bool(status.get('broker_connected'))
    online = broker_connected and device.device_id in status.get('connected_devices', [])
    detail = status.get('devices', {}).get(device.device_id, {})
    state = safe_state(device.state)
    # "connecting" is the cache's default, not a mode reported by the robot.
    live_mode = _token(detail.get('mode')) if detail.get('last_state') else None
    mode = (live_mode or state.get('mode') or 'unknown') if online else 'offline'
    reported = _time(diagnostics.get('last_telemetry_at'))
    state_time = _time(device.state_updated)
    latest = max([value for value in (reported, state_time) if value], default=None)
    age = max(0, round((now - latest).total_seconds())) if latest else None
    stale = age is not None and age > 90
    if not service or not broker_connected:
        summary = ('warning', 'Server disconnected from broker',
                   'The server cannot currently verify the robot connection.')
    elif not online:
        summary = ('warning', 'Robot offline', 'No current robot connection is registered with the broker.')
    elif latest is None:
        summary = ('waiting', 'Connected; waiting for telemetry',
                   'The connection is registered, but no robot activity has been received yet.')
    elif stale:
        summary = ('warning', 'Connected; telemetry is quiet',
                   'The robot connection is registered, but no telemetry has arrived for over 90 seconds. Quiet periods can be normal during sleep.')
    elif str(mode).lower() in ('sleep', 'sleeping', 'asleep'):
        summary = ('ok', 'Robot reports sleep', 'Recent robot activity is arriving. The reported mode is sleep.')
    else:
        summary = ('ok', 'Robot is communicating',
                   'Recent robot activity is arriving. This confirms communication, not every robot function.')

    commands = []
    events = []
    for command in device.command_events.all()[:20]:
        action = _token(command.action) or 'command'
        command_status = _token(command.status) or 'unknown'
        commands.append({
            'id': command.pk, 'time': _iso(command.created_at),
            'updated_at': _iso(command.updated_at), 'action': action,
            'label': action.replace('_', ' ').title(), 'status': command_status,
            'detail': COMMAND_DETAILS.get(command_status, 'Command status recorded by the server.'),
        })
        events.append({'time': _iso(command.updated_at), 'level': 'warning' if command_status == 'failed' else 'info',
                       'kind': 'command', 'message': f'{action}: {command_status}'})
    for field, message in (('last_connect', 'Robot connected to the broker.'),
                           ('last_disconnect', 'Robot disconnected from the broker.')):
        if getattr(device, field):
            events.append({'time': _iso(getattr(device, field)), 'level': 'info',
                           'kind': 'connection', 'message': message})
    # These events are generated from fixed safe templates in MoxieServer;
    # arbitrary log lines, payloads and conversation records are never included.
    events.extend(diagnostics.get('events', [])[-60:])
    events.sort(key=lambda event: event.get('time') or '')
    return {
        'generated_at': _iso(now),
        'device': {'id': device.pk, 'name': device.name or device.device_id, 'device_id': device.device_id},
        'broker': {'connected': broker_connected, 'last_connect': status.get('last_broker_connect'),
                   'last_disconnect': status.get('last_broker_disconnect')},
        'connection': {'online': online, 'mode': mode, 'last_telemetry_at': _iso(latest),
                       'telemetry_age_seconds': age, 'telemetry_stale': stale,
                       'last_state_at': _iso(state_time), 'last_connect': _iso(device.last_connect),
                       'last_mode_at': _iso(_time(detail.get('last_state')) or state_time),
                       'last_disconnect': _iso(device.last_disconnect)},
        'summary': dict(zip(('level', 'title', 'detail'), summary)),
        'state': state, 'commands': commands, 'events': events[-60:],
        'limitations': [
            'Telemetry time advances only when the robot reports activity; refreshing this page does not count.',
            'A progress icon alone does not reveal a download, startup stage, or hardware fault. Those require a robot report.',
            'The event timeline starts when this server process starts; saved connection, state and command times may be older.',
        ],
    }
