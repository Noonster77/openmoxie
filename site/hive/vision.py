"""Optional vision-extension client, privacy state, and Docker controls."""

from copy import deepcopy
from datetime import datetime, timezone
import http.client
import json
import logging
import os
import socket
from urllib.parse import quote

import requests

from .models import HiveConfiguration, MoxieDevice

logger = logging.getLogger(__name__)

VISION_URL = os.environ.get('OPENMOXIE_VISION_URL', 'http://vision:8080').rstrip('/')
VISION_CONTAINER = os.environ.get('OPENMOXIE_VISION_CONTAINER', 'openmoxie-vision')
DOCKER_SOCKET = '/var/run/docker.sock'
_MISSING = {'present': False}


def extension_enabled():
    cfg = HiveConfiguration.objects.filter(name='default').first()
    return bool(cfg and cfg.vision_extension_enabled)


def _request_json(path, timeout=1.5):
    response = requests.get(VISION_URL + path, timeout=timeout)
    response.raise_for_status()
    return response.json()


def service_status():
    try:
        payload = _request_json('/health')
        payload['reachable'] = True
        return payload
    except Exception as exc:
        return {'reachable': False, 'ready': False, 'error': str(exc)}


def latest_observation(max_age=20):
    try:
        payload = _request_json('/api/v1/latest')
    except Exception as exc:
        return {'ready': False, 'fresh': False, 'objects': [], 'error': str(exc)}
    captured = payload.get('captured_at')
    try:
        age = (datetime.now(timezone.utc) - datetime.fromisoformat(captured)).total_seconds()
    except (TypeError, ValueError):
        age = None
    payload['age_seconds'] = age
    payload['fresh'] = age is not None and age <= max_age
    payload['ready'] = bool(payload.get('objects')) and payload['fresh']
    return payload


def latest_frame():
    response = requests.get(VISION_URL + '/api/v1/frame', timeout=2)
    response.raise_for_status()
    return response.content, response.headers.get('Content-Type', 'image/jpeg')


def _post_json(path, payload):
    response = requests.post(VISION_URL + path, json=payload, timeout=3)
    data = response.json()
    if response.status_code >= 400:
        raise ValueError(data.get('error', f'Vision service returned {response.status_code}.'))
    return data


def enroll_face(name):
    return _post_json('/api/v1/faces/enroll', {'name': name})


def remove_face(name):
    return _post_json('/api/v1/faces/delete', {'name': name})


def _remember(container, key):
    return {'present': key in container, 'value': deepcopy(container.get(key))}


def _restore(container, key, record):
    if record.get('present'):
        container[key] = deepcopy(record.get('value'))
    else:
        container.pop(key, None)


def set_device_vision(device, enabled, mode='', service=None):
    """Apply or restore only vision-owned config keys, then push them live."""
    config = deepcopy(device.robot_config or {})
    settings = deepcopy(device.robot_settings or {})
    props = settings.setdefault('props', {})
    keys = ('image_captioning', 'ic_by_rb', 'gcp_upload_disable')

    if enabled:
        # The firmware caption endpoint does not identify the sender in a way
        # this service can reliably map back to one of several robots. Keep
        # ownership explicit so one Moxie's image can never answer another.
        for other in MoxieDevice.objects.filter(vision_active=True).exclude(pk=device.pk):
            set_device_vision(other, False, service=service)
        if not device.vision_active or not device.vision_config_backup:
            device.vision_config_backup = {
                'data_sharing': _remember(config, 'data_sharing'),
                'props': {key: _remember(props, key) for key in keys},
            }
        config['data_sharing'] = 'full'
        props.update({
            'image_captioning': '1',
            'ic_by_rb': '1',
            'gcp_upload_disable': '0',
        })
        device.vision_active = True
        device.vision_mode = mode or 'vision'
    else:
        backup = device.vision_config_backup or {}
        _restore(config, 'data_sharing', backup.get('data_sharing', _MISSING))
        prop_backup = backup.get('props', {})
        for key in keys:
            _restore(props, key, prop_backup.get(key, _MISSING))
        device.vision_active = False
        device.vision_mode = ''
        device.vision_config_backup = {}

    device.robot_config = config
    device.robot_settings = settings
    device.save(update_fields=[
        'robot_config', 'robot_settings', 'vision_active', 'vision_mode',
        'vision_config_backup',
    ])
    if service:
        service.handle_config_updated(device)
        service.set_vision_gate(device.device_id, enabled)
    return device


class _UnixHTTPConnection(http.client.HTTPConnection):
    def __init__(self):
        super().__init__('localhost', timeout=3)

    def connect(self):
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.settimeout(self.timeout)
        self.sock.connect(DOCKER_SOCKET)


def docker_control_available():
    return os.environ.get('OPENMOXIE_DOCKER_CONTROL') == '1' and os.path.exists(DOCKER_SOCKET)


def _docker_request(method, path):
    if not docker_control_available():
        raise RuntimeError('Docker controls are not installed; run setup-vision.bat first.')
    conn = _UnixHTTPConnection()
    try:
        conn.request(method, path, headers={'Content-Length': '0'})
        response = conn.getresponse()
        raw = response.read()
        if response.status >= 400:
            raise RuntimeError(f'Docker returned {response.status}: {raw.decode("utf-8", "replace")}')
        return json.loads(raw) if raw else {}
    finally:
        conn.close()


def docker_container_status():
    if not docker_control_available():
        return {'available': False, 'state': 'unavailable'}
    try:
        data = _docker_request('GET', f'/containers/{quote(VISION_CONTAINER)}/json')
        return {
            'available': True,
            'state': data.get('State', {}).get('Status', 'unknown'),
            'running': bool(data.get('State', {}).get('Running')),
        }
    except Exception as exc:
        return {'available': True, 'state': 'missing', 'running': False, 'error': str(exc)}


def control_vision_container(action):
    if action not in ('start', 'stop', 'restart'):
        raise ValueError('Unsupported vision container action.')
    suffix = {'start': 'start', 'stop': 'stop?t=10', 'restart': 'restart?t=10'}[action]
    _docker_request('POST', f'/containers/{quote(VISION_CONTAINER)}/{suffix}')
    logger.info('Vision container %s requested from the dashboard', action)
