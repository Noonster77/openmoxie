from openai import OpenAI
import logging
import requests
import time

logger = logging.getLogger(__name__)

_OPENAPI_KEY=None
_CHAT_PROVIDER='openai'
_CHAT_BASE_URL=''
_CHAT_MODEL='gpt-4o-mini'
_STT_PROVIDER='openai'
_LOCAL_STT_MODEL='small.en'
_CHAT_HTTP_SESSION = requests.Session()

def set_openai_key(key):
    global _OPENAPI_KEY
    _OPENAPI_KEY = key

def create_openai():
    global _OPENAPI_KEY
    return OpenAI(api_key=_OPENAPI_KEY)

def configure_ai(chat_provider='openai', chat_base_url='', chat_model='gpt-4o-mini',
                 stt_provider='openai', local_stt_model='small.en'):
    global _CHAT_PROVIDER, _CHAT_BASE_URL, _CHAT_MODEL, _STT_PROVIDER, _LOCAL_STT_MODEL
    _CHAT_PROVIDER = chat_provider
    _CHAT_BASE_URL = chat_base_url.rstrip('/')
    _CHAT_MODEL = chat_model
    _STT_PROVIDER = stt_provider
    _LOCAL_STT_MODEL = local_stt_model
    logger.info('AI configured: chat=%s model=%s base_url=%s stt=%s stt_model=%s',
                _CHAT_PROVIDER, _CHAT_MODEL, _CHAT_BASE_URL or 'OpenAI', _STT_PROVIDER, _LOCAL_STT_MODEL)

def create_chat_client():
    if _CHAT_PROVIDER == 'lmstudio':
        if not _CHAT_BASE_URL:
            raise ValueError('LM Studio base URL is not configured')
        return OpenAI(api_key='lm-studio', base_url=_CHAT_BASE_URL)
    return create_openai()

def get_chat_model(fallback=None):
    return _CHAT_MODEL or fallback or 'gpt-4o-mini'

def chat_completion(messages, fallback_model=None, max_tokens=70, temperature=0.5,
                    reasoning='off'):
    """Return text from OpenAI or LM Studio, using LM Studio's native API to control reasoning."""
    model = get_chat_model(fallback_model)
    if _CHAT_PROVIDER == 'lmstudio':
        system_prompt = '\n\n'.join(item.get('content', '') for item in messages if item.get('role') == 'system')
        transcript = '\n'.join(
            f"{item.get('role', 'user').upper()}: {item.get('content', '')}"
            for item in messages if item.get('role') != 'system'
        )
        native_root = _CHAT_BASE_URL[:-3] if _CHAT_BASE_URL.endswith('/v1') else _CHAT_BASE_URL
        native_url = native_root.rstrip('/') + '/api/v1/chat'
        started = time.monotonic()
        response = _CHAT_HTTP_SESSION.post(native_url, json={
            'model': model,
            'system_prompt': system_prompt,
            'input': transcript,
            # Respect the conversation's speaking budget. The previous 120-token
            # minimum almost doubled ordinary 70-token turns on a local model.
            'max_output_tokens': max(1, int(max_tokens)),
            'temperature': temperature,
            'reasoning': reasoning,
        }, timeout=(5, 90))
        response.raise_for_status()
        payload = response.json()
        output = payload.get('output', [])
        text = ''.join(item.get('content', '') for item in output if item.get('type') == 'message').strip()
        if not text:
            raise ValueError('LM Studio returned no spoken message content')
        stats = payload.get('stats', {})
        logger.info(
            'LLM completed in %.2fs (ttft=%ss, input=%s, output=%s, rate=%s tok/s)',
            time.monotonic() - started,
            stats.get('time_to_first_token_seconds', '?'),
            stats.get('input_tokens', '?'),
            stats.get('total_output_tokens', '?'),
            stats.get('tokens_per_second', '?'),
        )
        return text
    client = create_openai()
    return client.chat.completions.create(
        model=model,
        messages=messages,
        max_tokens=max_tokens,
        temperature=temperature,
    ).choices[0].message.content

def get_stt_config():
    return _STT_PROVIDER, _LOCAL_STT_MODEL
