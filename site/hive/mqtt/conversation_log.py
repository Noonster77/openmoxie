import re
import threading
from datetime import timedelta
from pathlib import Path
from django.conf import settings
from django.utils import timezone
from ..models import ConversationEvent, MoxieDevice

_FILE_LOCK = threading.Lock()
_SAFETY_PATTERNS = {
    'self-harm': r'\b(kill myself|hurt myself|suicide|want to die|do not want to live)\b',
    'weapons or violence': r'\b(make (?:a )?(?:bomb|gun|weapon)|shoot someone|stab someone|kill someone|hide a body)\b',
    'sexual content': r'\b(sex|porn|naked pictures?|touch my private|private parts?)\b',
    'drugs or alcohol': r'\b(get high|take drugs?|make meth|drink alcohol|vape|cigarettes?)\b',
    'abuse or immediate danger': r'\b(someone hit me|hurting me|touched me|i am in danger|call 911|emergency)\b',
}


def safety_categories(text):
    lowered = (text or '').lower()
    return [name for name, pattern in _SAFETY_PATTERNS.items() if re.search(pattern, lowered)]


def safety_redirect(text):
    categories = safety_categories(text)
    if not categories:
        return None
    if 'self-harm' in categories or 'abuse or immediate danger' in categories:
        return "I'm really glad you told me. Please get Daddy, Mom, or another trusted grown-up right now. If anyone is in immediate danger, ask them to call emergency services."
    return "I can't help with instructions about that. Let's tell Daddy, Mom, or another trusted grown-up and choose something safe to talk about."


def record_conversation(device_id, role, text, module_id='', content_id=''):
    text = (text or '').strip()
    if not text:
        return None
    try:
        device = MoxieDevice.objects.get(device_id=device_id)
    except MoxieDevice.DoesNotExist:
        return None
    # Robot notify messages can repeat a just-recorded request/response.
    cutoff = timezone.now() - timedelta(seconds=8)
    duplicate = ConversationEvent.objects.filter(
        device=device, role=role, text=text, created_at__gte=cutoff
    ).exists()
    if duplicate:
        return None
    categories = safety_categories(text) if role == 'user' else []
    event = ConversationEvent.objects.create(
        device=device, role=role, text=text, module_id=module_id or '', content_id=content_id or '',
        safety_flagged=bool(categories), safety_categories=categories,
    )
    day = timezone.localtime(event.created_at).date().isoformat()
    safe_device = re.sub(r'[^A-Za-z0-9_.-]', '_', device.device_id)
    transcript_dir = Path(settings.DATA_STORE_DIR) / 'transcripts' / safe_device
    transcript_dir.mkdir(parents=True, exist_ok=True)
    line = f"[{timezone.localtime(event.created_at).strftime('%H:%M:%S')}] {role.upper()}: {text}"
    if categories:
        line += f" [PARENT REVIEW: {', '.join(categories)}]"
    with _FILE_LOCK:
        with (transcript_dir / f'{day}.txt').open('a', encoding='utf-8') as transcript:
            transcript.write(line + '\n')
    return event
