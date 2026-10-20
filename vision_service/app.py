"""Local-only Moxie caption endpoint and object detector.

The `/api/v1/caption` transport contract and camera characteristics are based
on AppleMelonOrange/sidecar-for-openmoxie (MIT). This implementation is new
work for the Noonster77 OpenMoxie fork: bounded input handling, TLS bootstrap,
local YOLO inference, latest-frame privacy semantics, and health/status APIs.
"""

from collections import Counter
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from io import BytesIO
import ipaddress
import json
import logging
import os
from pathlib import Path
import re
import ssl
import threading
import time

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from PIL import Image, ImageStat
import cv2
import numpy as np

logging.basicConfig(level=os.environ.get('VISION_LOG_LEVEL', 'INFO'))
logger = logging.getLogger('openmoxie.vision')

DATA_DIR = Path(os.environ.get('VISION_DATA_DIR', '/data'))
MODEL_DIR = Path(os.environ.get('VISION_MODEL_DIR', '/models'))
MODEL_NAME = os.environ.get('VISION_MODEL', 'yolo11n.pt')
CONFIDENCE = float(os.environ.get('VISION_CONFIDENCE', '0.35'))
ARCHIVE_FRAMES = os.environ.get('VISION_ARCHIVE_FRAMES', '0') == '1'
FACE_RECOGNITION = os.environ.get('VISION_FACE_RECOGNITION', '1') == '1'
MAX_BODY = int(os.environ.get('VISION_MAX_BODY_BYTES', str(2 * 1024 * 1024)))
DATA_DIR.mkdir(parents=True, exist_ok=True)
MODEL_DIR.mkdir(parents=True, exist_ok=True)

_state_lock = threading.Lock()
_model_lock = threading.Lock()
_model = None
_model_error = ''
_state = {
    'captured_at': None,
    'caption': '',
    'objects': [],
    'width': None,
    'height': None,
    'frame_count': 0,
    'inference_ms': None,
    'session_id': '',
    'faces': [],
}

FACE_DIR = DATA_DIR / 'faces'
FACE_DIR.mkdir(exist_ok=True)
_face_cascade = cv2.CascadeClassifier(
    str(Path(cv2.data.haarcascades) / 'haarcascade_frontalface_default.xml')
)
_face_recognizer = None
_face_labels = {}


def _safe_face_name(name):
    clean = re.sub(r'[^A-Za-z0-9 _-]', '', str(name)).strip()[:40]
    if not clean:
        raise ValueError('Face name must contain letters or numbers.')
    return clean


def _face_samples():
    samples, ids, labels = [], [], {}
    for index, directory in enumerate(sorted(path for path in FACE_DIR.iterdir() if path.is_dir())):
        labels[index] = directory.name
        for path in directory.glob('*.png'):
            image = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
            if image is not None:
                samples.append(image)
                ids.append(index)
    return samples, np.asarray(ids, dtype=np.int32), labels


def _train_faces():
    global _face_recognizer, _face_labels
    samples, ids, labels = _face_samples()
    if not samples:
        _face_recognizer, _face_labels = None, {}
        return
    recognizer = cv2.face.LBPHFaceRecognizer_create()
    recognizer.train(samples, ids)
    _face_recognizer, _face_labels = recognizer, labels


def _face_crops(image):
    array = cv2.cvtColor(np.asarray(image), cv2.COLOR_RGB2GRAY)
    boxes = _face_cascade.detectMultiScale(array, scaleFactor=1.12, minNeighbors=5, minSize=(28, 28))
    return array, sorted(boxes, key=lambda box: box[2] * box[3], reverse=True)


def recognize_faces(image):
    if not FACE_RECOGNITION:
        return []
    gray, boxes = _face_crops(image)
    faces = []
    for x, y, width, height in boxes[:8]:
        crop = cv2.resize(gray[y:y + height, x:x + width], (100, 100))
        name, distance = 'unknown', None
        if _face_recognizer is not None:
            label_id, distance = _face_recognizer.predict(crop)
            # LBPH reports a distance, not a probability. Conservative refusal
            # prevents a low-resolution frame from assigning a wrong identity.
            if distance <= 58 and label_id in _face_labels:
                name = _face_labels[label_id]
        faces.append({
            'name': name, 'distance': round(float(distance), 1) if distance is not None else None,
            'box': [int(x), int(y), int(x + width), int(y + height)],
        })
    return faces


def enroll_latest_face(name):
    if not FACE_RECOGNITION:
        raise ValueError('Face recognition is disabled for this container.')
    frame = DATA_DIR / 'latest.jpg'
    if not frame.exists():
        raise ValueError('No current frame is available for enrollment.')
    image = Image.open(frame).convert('RGB')
    gray, boxes = _face_crops(image)
    if len(boxes) != 1:
        raise ValueError('Enrollment needs exactly one clearly visible face in the frame.')
    x, y, width, height = boxes[0]
    crop = cv2.resize(gray[y:y + height, x:x + width], (100, 100))
    safe_name = _safe_face_name(name)
    directory = FACE_DIR / safe_name
    directory.mkdir(exist_ok=True)
    index = len(list(directory.glob('*.png'))) + 1
    cv2.imwrite(str(directory / f'{index:03d}.png'), crop)
    _train_faces()
    return {'name': safe_name, 'samples': index, 'recommended_samples': 5}


def delete_face(name):
    safe_name = _safe_face_name(name)
    directory = FACE_DIR / safe_name
    if directory.exists():
        for path in directory.glob('*.png'):
            path.unlink()
        directory.rmdir()
    _train_faces()


def _json_bytes(payload):
    return json.dumps(payload, separators=(',', ':')).encode('utf-8')


def _ensure_certificate():
    cert_path, key_path = DATA_DIR / 'vision.crt', DATA_DIR / 'vision.key'
    if cert_path.exists() and key_path.exists():
        return cert_path, key_path
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, 'production-ic-worker.embodied.com'),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, 'OpenMoxie local vision'),
    ])
    sans = [
        x509.DNSName('production-ic-worker.embodied.com'),
        x509.DNSName('staging-ic-worker.embodied.com'),
        x509.DNSName('localhost'),
        x509.IPAddress(ipaddress.ip_address('127.0.0.1')),
    ]
    now = datetime.now(timezone.utc)
    cert = (
        x509.CertificateBuilder().subject_name(subject).issuer_name(issuer)
        .public_key(key.public_key()).serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(days=1)).not_valid_after(now + timedelta(days=3650))
        .add_extension(x509.SubjectAlternativeName(sans), critical=False)
        .sign(key, hashes.SHA256())
    )
    key_path.write_bytes(key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.TraditionalOpenSSL,
        serialization.NoEncryption(),
    ))
    cert_path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    os.chmod(key_path, 0o600)
    return cert_path, key_path


def _load_model():
    global _model, _model_error
    with _model_lock:
        if _model is not None:
            return _model
        try:
            from ultralytics import YOLO
            model_path = MODEL_DIR / MODEL_NAME
            if not model_path.exists():
                previous = Path.cwd()
                try:
                    os.chdir(MODEL_DIR)
                    _model = YOLO(MODEL_NAME)
                finally:
                    os.chdir(previous)
            else:
                _model = YOLO(str(model_path))
            _model_error = ''
            logger.info('Object detector ready: %s', MODEL_NAME)
        except Exception as exc:
            _model_error = str(exc)
            logger.exception('Could not load object detector')
            raise
        return _model


def _position(box, width, height):
    x1, y1, x2, y2 = box
    x, y = (x1 + x2) / 2 / width, (y1 + y2) / 2 / height
    horizontal = 'left' if x < .34 else ('right' if x > .66 else 'center')
    vertical = 'top' if y < .34 else ('bottom' if y > .66 else 'middle')
    return horizontal, vertical


_COLORS = {
    'black': (25, 25, 25), 'white': (230, 230, 230), 'gray': (128, 128, 128),
    'red': (190, 45, 45), 'orange': (220, 120, 35), 'yellow': (215, 195, 45),
    'green': (55, 145, 65), 'blue': (50, 90, 185), 'purple': (125, 65, 155),
    'pink': (220, 130, 165), 'brown': (110, 75, 45),
}


def _dominant_color(image, box):
    crop = image.crop(tuple(max(0, int(v)) for v in box)).convert('RGB').resize((1, 1))
    rgb = ImageStat.Stat(crop).mean[:3]
    return min(_COLORS, key=lambda name: sum((rgb[i] - _COLORS[name][i]) ** 2 for i in range(3)))


def _caption(objects):
    if not objects:
        return "I don't recognize a clear object in this view yet."
    counts = Counter(item['label'] for item in objects)
    phrases = []
    for label, count in counts.most_common(8):
        phrases.append(label if count == 1 else f'{count} {label}s')
    if len(phrases) == 1:
        return f'I can see {phrases[0]}.'
    return 'I can see ' + ', '.join(phrases[:-1]) + ', and ' + phrases[-1] + '.'


def detect(jpeg):
    image = Image.open(BytesIO(jpeg)).convert('RGB')
    model = _load_model()
    started = time.monotonic()
    result = model.predict(image, conf=CONFIDENCE, verbose=False, device='cpu')[0]
    objects = []
    for box in result.boxes:
        coords = [float(v) for v in box.xyxy[0].tolist()]
        confidence = float(box.conf[0])
        label = str(result.names[int(box.cls[0])]).replace('_', ' ')
        horizontal, vertical = _position(coords, image.width, image.height)
        objects.append({
            'label': label,
            'confidence': round(confidence, 3),
            'box': [round(v, 1) for v in coords],
            'position': horizontal,
            'vertical_position': vertical,
            'color': _dominant_color(image, coords),
        })
    objects.sort(key=lambda item: item['confidence'], reverse=True)
    return image, objects[:30], round((time.monotonic() - started) * 1000)


def _multipart_value(body, field):
    pattern = rb'name="' + re.escape(field.encode()) + rb'"\r?\n\r?\n([^\r\n]+)'
    match = re.search(pattern, body)
    return match.group(1).decode('utf-8', 'replace') if match else ''


def process_frame(body):
    start, end = body.find(b'\xff\xd8'), body.rfind(b'\xff\xd9')
    if start < 0 or end < start:
        raise ValueError('Multipart body did not contain a complete JPEG.')
    jpeg = body[start:end + 2]
    image, objects, inference_ms = detect(jpeg)
    captured_at = datetime.now(timezone.utc).isoformat()
    session_id = _multipart_value(body, 'session-id')
    latest_tmp = DATA_DIR / 'latest.tmp.jpg'
    latest_tmp.write_bytes(jpeg)
    latest_tmp.replace(DATA_DIR / 'latest.jpg')
    if ARCHIVE_FRAMES:
        stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
        (DATA_DIR / f'frame_{stamp}.jpg').write_bytes(jpeg)
    faces = recognize_faces(image)
    with _state_lock:
        _state.update({
            'captured_at': captured_at, 'caption': _caption(objects),
            'objects': objects, 'width': image.width, 'height': image.height,
            'frame_count': _state['frame_count'] + 1,
            'inference_ms': inference_ms, 'session_id': session_id,
            'faces': faces,
        })
        snapshot = dict(_state)
    (DATA_DIR / 'latest.json').write_bytes(_json_bytes(snapshot))
    return snapshot


class Handler(BaseHTTPRequestHandler):
    server_version = 'OpenMoxieVision/1.0'

    def log_message(self, fmt, *args):
        logger.info('%s - %s', self.client_address[0], fmt % args)

    def _send(self, status, body, content_type='application/json'):
        if not isinstance(body, bytes):
            body = _json_bytes(body)
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == '/health':
            health = {
                'ready': True, 'model_loaded': _model is not None,
                'model': MODEL_NAME, 'model_error': _model_error,
                'frames_received': _state['frame_count'],
                'archive_frames': ARCHIVE_FRAMES,
                'face_recognition': FACE_RECOGNITION,
            }
            # Do not reveal enrolled family names on the robot-facing LAN
            # listener. The Django service gets them over Docker's internal
            # port for the Parent Corner UI.
            if self.server.server_port == 8080:
                health['enrolled_faces'] = sorted(_face_labels.values())
            self._send(200, health)
        elif self.path == '/api/v1/latest':
            if self.server.server_port != 8080:
                self._send(404, {'error': 'Not found.'})
            else:
                with _state_lock:
                    self._send(200, dict(_state))
        elif self.path == '/api/v1/frame':
            if self.server.server_port != 8080:
                self._send(404, {'error': 'Not found.'})
            else:
                frame = DATA_DIR / 'latest.jpg'
                self._send(200, frame.read_bytes(), 'image/jpeg') if frame.exists() else self._send(404, {'error': 'No frame received yet.'})
        else:
            self._send(404, {'error': 'Not found.'})

    def do_POST(self):
        if self.path in ('/api/v1/faces/enroll', '/api/v1/faces/delete'):
            if self.server.server_port != 8080:
                self._send(404, {'error': 'Management API is internal only.'})
                return
            try:
                length = min(int(self.headers.get('Content-Length', '0')), 4096)
                payload = json.loads(self.rfile.read(length) or b'{}')
                if self.path.endswith('/enroll'):
                    self._send(200, enroll_latest_face(payload.get('name', '')))
                else:
                    delete_face(payload.get('name', ''))
                    self._send(200, {'deleted': True})
            except Exception as exc:
                self._send(422, {'error': str(exc)})
            return
        if self.path != '/api/v1/caption':
            self._send(404, {'error': 'Not found.'})
            return
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if length <= 0 or length > MAX_BODY:
                self._send(413, {'error': 'Invalid or oversized request.'})
                return
            snapshot = process_frame(self.rfile.read(length))
            self._send(200, {
                'caption': snapshot['caption'],
                'description': snapshot['caption'],
                'objects': snapshot['objects'],
            })
        except Exception as exc:
            logger.exception('Frame processing failed')
            self._send(422, {'error': str(exc)})


def _serve_http():
    logger.info('Internal vision API listening on http://0.0.0.0:8080')
    ThreadingHTTPServer(('0.0.0.0', 8080), Handler).serve_forever()


def main():
    _train_faces()
    cert, key = _ensure_certificate()
    threading.Thread(target=_serve_http, name='vision-http', daemon=True).start()
    if os.environ.get('VISION_WARM_MODEL', '1') == '1':
        threading.Thread(target=lambda: _load_model(), name='vision-model-warmup', daemon=True).start()
    server = ThreadingHTTPServer(('0.0.0.0', 443), Handler)
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(cert, key)
    server.socket = context.wrap_socket(server.socket, server_side=True)
    logger.info('Moxie caption receiver listening on https://0.0.0.0:443')
    server.serve_forever()


if __name__ == '__main__':
    main()
