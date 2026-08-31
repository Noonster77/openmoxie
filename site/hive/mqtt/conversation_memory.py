"""Speaker-scoped conversation memory with auditable provenance."""

from django.utils import timezone


MEMORY_VERSION = 2
MAX_ITEMS_PER_SPEAKER = 20


def _memory_store(persist_data):
    memory = persist_data.setdefault('conversation_memory', {})
    legacy = memory.pop('recent', None)
    if legacy and not memory.get('legacy_unscoped'):
        # Old entries have no trustworthy speaker attribution. Keep them for a
        # parent to audit, but never put them into an AI prompt.
        memory['legacy_unscoped'] = legacy
    memory['version'] = MEMORY_VERSION
    memory.setdefault('profiles', {})
    return memory


def speaker_items(persist_data, speaker):
    """Return only memory belonging to the named active speaker."""
    speaker = (speaker or '').strip()
    if not speaker:
        return []
    memory = _memory_store(persist_data)
    return memory['profiles'].get(speaker, {}).get('items', [])


def remember_exchange(persist_data, speaker, speech, response, request):
    """Save one exchange under a single speaker with its source metadata."""
    speaker = (speaker or '').strip()
    if not speaker:
        return
    memory = _memory_store(persist_data)
    profile = memory['profiles'].setdefault(speaker, {'items': []})
    items = profile.setdefault('items', [])
    provenance = {
        'source': 'conversation',
        'source_event_id': request.get('event_id', ''),
        'module_id': request.get('module_id', ''),
        'content_id': request.get('content_id', ''),
        'captured_at': timezone.now().isoformat(),
        'speaker': speaker,
    }
    items.extend([
        {
            'kind': 'conversation_turn',
            'role': 'user',
            'content': speech,
            'provenance': dict(provenance),
        },
        {
            'kind': 'conversation_turn',
            'role': 'assistant',
            'content': response,
            'provenance': dict(provenance),
        },
    ])
    del items[:-MAX_ITEMS_PER_SPEAKER]


def memory_audit(persist_data):
    """Return the scoped store in a template-friendly, stable order."""
    memory = _memory_store(persist_data)
    profiles = [
        {'speaker': speaker, 'items': profile.get('items', [])}
        for speaker, profile in sorted(memory['profiles'].items(), key=lambda item: item[0].lower())
    ]
    return profiles, memory.get('legacy_unscoped', [])


def clear_memory(persist_data, speaker=None):
    """Clear one speaker's memory, or the complete memory store."""
    if not speaker:
        persist_data.pop('conversation_memory', None)
        return
    memory = _memory_store(persist_data)
    memory['profiles'].pop(speaker, None)
