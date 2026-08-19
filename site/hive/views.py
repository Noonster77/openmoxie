from django.forms import model_to_dict
from django.shortcuts import redirect
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.views import generic
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.http import Http404, HttpResponseBadRequest, JsonResponse
from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse,HttpResponseRedirect
from django.conf import settings
from django.utils import timezone
import qrcode
from PIL import Image
from io import BytesIO
from copy import deepcopy

from .models import ConversationEvent, GlobalResponse, HiveConfiguration, Joke, MentorBehavior, MoxieDevice, MoxieSchedule, RobotCommandEvent, SinglePromptChat, TriviaQuestion
from .content.data import DM_MISSION_CONTENT_IDS, MISSION_DESCRIPTIONS, RECOMMENDABLE_MODULES, get_moxie_customization_groups
from .data_import import update_import_status, import_content
from .mqtt.moxie_server import get_instance
from .mqtt.robot_data import DEFAULT_ROBOT_CONFIG, DEFAULT_ROBOT_SETTINGS
from .mqtt.volley import Volley
from .mqtt.conversation_log import rewrite_daily_transcript
from .mqtt.ai_factory import create_chat_client, get_chat_model
import json
import uuid
import logging
import re
from collections import deque
from datetime import date

logger = logging.getLogger(__name__)

# ROOT - Show setup if we have no config record, dashboard otherwise
def root_view(request):
    cfg = HiveConfiguration.objects.filter(name='default')
    if cfg:
        return HttpResponseRedirect(reverse("hive:dashboard"))
    else:
        return HttpResponseRedirect(reverse("hive:setup"))

# SETUP - Edit systemn configuration record
class SetupView(generic.TemplateView):
    template_name = "hive/setup.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        User = get_user_model()
        context['needs_admin'] = not User.objects.filter(is_superuser=True).exists()
        curr_cfg = HiveConfiguration.objects.filter(name='default').first()
        if curr_cfg:
            context['object'] = curr_cfg
        return context

# SETUP-POST - Save system config changes
@require_http_methods(["POST"])
def hive_configure(request):
    cfg, created = HiveConfiguration.objects.get_or_create(name='default')
    openai = request.POST['apikey']
    if openai:
        cfg.openai_api_key = openai
    google = request.POST['googleapikey']
    if google:
        # Moxie likes compact json, so rewrite json input to be safe
        cfg.google_api_key = json.dumps(json.loads(google))
    cfg.external_host = request.POST['hostname']
    cfg.chat_provider = request.POST.get('chat_provider', 'openai')
    cfg.chat_base_url = request.POST.get('chat_base_url', '').strip()
    cfg.chat_model = request.POST.get('chat_model', 'gpt-4o-mini').strip() or 'gpt-4o-mini'
    cfg.stt_provider = request.POST.get('stt_provider', 'openai')
    cfg.local_stt_model = request.POST.get('local_stt_model', 'small.en').strip() or 'small.en'
    if cfg.chat_provider not in ('openai', 'lmstudio') or cfg.stt_provider not in ('openai', 'local'):
        return HttpResponseBadRequest('Unsupported AI provider selection.')
    if cfg.chat_provider == 'lmstudio' and not cfg.chat_base_url.startswith(('http://', 'https://')):
        return HttpResponseBadRequest('LM Studio base URL must begin with http:// or https://')
    cfg.allow_unverified_bots = request.POST.get('allowall') == "on"
    # Bootstrap any default data if not present
    if not cfg.common_config:
        cfg.common_config = DEFAULT_ROBOT_CONFIG
    if not cfg.common_settings:
        cfg.common_settings = DEFAULT_ROBOT_SETTINGS
    cfg.save()

    # Create Admin User if data exists and we dont have one
    User = get_user_model()
    if not User.objects.filter(is_superuser=True).exists():
        admin = request.POST.get("adminUser")
        adminPassword = request.POST.get("adminPassword")
        if admin and adminPassword:
            User.objects.create_superuser(admin, None, adminPassword)
            logger.info(f"Created superuser '{admin}'")
        else:
            logger.warning(f"Couldn't create missing superuser")

    logger.info("Updated default Hive Configuration")
    # reload any cached db objects
    get_instance().update_from_database()
    return HttpResponseRedirect(reverse("hive:dashboard"))

# DASHBOARD - View and overview of the system
class DashboardView(generic.TemplateView):
    template_name = "hive/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        alert_message = kwargs.get('alert_message', None)
        if alert_message:
            context['alert'] = alert_message
        context['recent_devices'] = MoxieDevice.objects.all()
        context['conversations'] = SinglePromptChat.objects.all()
        context['schedules'] = MoxieSchedule.objects.all()
        service = get_instance()
        context['live'] = service.robot_data().connected_list() if service else []
        context['service_status'] = service.service_status() if service else {
            'broker_connected': False,
            'last_connect_error': 'MQTT service has not started.',
        }
        hive_config = HiveConfiguration.objects.filter(name='default').first()
        context['openai_configured'] = bool(hive_config and (hive_config.openai_api_key or '').strip())
        context['ai_config'] = hive_config
        context['recent_conversation'] = ConversationEvent.objects.select_related('device').order_by('-created_at')[:20]
        context['safety_alerts_today'] = ConversationEvent.objects.filter(safety_flagged=True, created_at__date=date.today()).count()
        return context


class GuideView(generic.TemplateView):
    template_name = 'hive/guide.html'

# STATUS - Lightweight, credential-free diagnostics used by the dashboard.
def connection_status(request):
    service = get_instance()
    if not service:
        return JsonResponse({
            'broker_connected': False,
            'last_connect_error': 'MQTT service has not started.',
            'connected_devices': [],
        }, status=503)
    return JsonResponse(service.service_status())


def _safe_debug_tail(limit=80):
    path = settings.DATA_STORE_DIR / 'debug.log'
    if not path.exists():
        return []
    with path.open('r', encoding='utf-8', errors='replace') as stream:
        lines = list(deque(stream, maxlen=limit))
    redacted = []
    for line in lines:
        line = re.sub(r'sk-[A-Za-z0-9_-]{12,}', 'sk-[REDACTED]', line.rstrip())
        line = re.sub(r'("?(?:password|api[_-]?key)"?\s*[:=]\s*)\S+', r'\1[REDACTED]', line, flags=re.I)
        redacted.append(line)
    return redacted


def live_activity(request, pk):
    device = get_object_or_404(MoxieDevice, pk=pk)
    events = ConversationEvent.objects.filter(device=device).order_by('-created_at')[:60]
    persist = get_instance().robot_data().get_persist_for_device(device)
    service_status = get_instance().service_status()
    detail = service_status.get('devices', {}).get(device.device_id, {})
    return JsonResponse({
        'online': device.device_id in service_status.get('connected_devices', []),
        'mode': detail.get('mode', 'offline'),
        'active_speaker': persist.get('active_speaker', 'Not identified'),
        'events': [{
            'id': event.pk, 'time': event.created_at.isoformat(), 'role': event.role,
            'text': event.text, 'module_id': event.module_id, 'content_id': event.content_id,
            'safety_flagged': event.safety_flagged, 'safety_categories': event.safety_categories,
        } for event in reversed(events)],
        'debug': _safe_debug_tail(),
        'commands': [{
            'id': command.pk, 'time': command.created_at.isoformat(), 'action': command.action,
            'label': command.label or command.action.title(), 'status': command.status,
            'detail': command.detail,
        } for command in device.command_events.all()[:12]],
    })


class LiveMonitorView(generic.DetailView):
    template_name = 'hive/monitor.html'
    model = MoxieDevice


class TranscriptView(generic.DetailView):
    template_name = 'hive/transcripts.html'
    model = MoxieDevice

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        selected = self.request.GET.get('date') or timezone.localdate().isoformat()
        try:
            selected_date = date.fromisoformat(selected)
        except ValueError:
            selected_date = timezone.localdate()
        context['selected_date'] = selected_date
        context['events'] = ConversationEvent.objects.filter(device=self.object, created_at__date=selected_date)
        context['days'] = list(ConversationEvent.objects.filter(device=self.object).dates('created_at', 'day', order='DESC'))
        return context


def transcript_download(request, pk, day):
    device = get_object_or_404(MoxieDevice, pk=pk)
    try:
        selected_date = date.fromisoformat(day)
    except ValueError:
        raise Http404('Invalid transcript date')
    events = ConversationEvent.objects.filter(device=device, created_at__date=selected_date)
    lines = [f'OpenMoxie conversation transcript - {device} - {selected_date}', '']
    for event in events:
        local_time = timezone.localtime(event.created_at).strftime('%H:%M:%S')
        line = f'[{local_time}] {event.role.upper()}: {event.text}'
        if event.safety_flagged:
            line += f" [PARENT REVIEW: {', '.join(event.safety_categories)}]"
        lines.append(line)
    response = HttpResponse('\n'.join(lines) + '\n', content_type='text/plain; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="moxie-{selected_date}.txt"'
    return response


@require_http_methods(['POST'])
def transcript_manage(request, pk):
    device = get_object_or_404(MoxieDevice, pk=pk)
    action = request.POST.get('action')
    affected_days = set()
    if action == 'delete_event':
        event = get_object_or_404(ConversationEvent, pk=request.POST.get('event_id'), device=device)
        affected_days.add(timezone.localtime(event.created_at).date())
        event.delete()
        message = 'Conversation entry deleted.'
    elif action == 'delete_day':
        try:
            selected_day = date.fromisoformat(request.POST.get('date', ''))
        except ValueError:
            return HttpResponseBadRequest('Invalid transcript date.')
        affected_days.add(selected_day)
        ConversationEvent.objects.filter(device=device, created_at__date=selected_day).delete()
        message = f'Transcript for {selected_day} deleted.'
    elif action == 'delete_all':
        affected_days.update(ConversationEvent.objects.filter(device=device).dates('created_at', 'day'))
        ConversationEvent.objects.filter(device=device).delete()
        message = 'All recorded conversations deleted.'
    else:
        return HttpResponseBadRequest('Unknown transcript action.')
    for affected_day in affected_days:
        rewrite_daily_transcript(device, affected_day)
    return redirect(f"{reverse('hive:transcripts', args=[device.pk])}?saved={message}")


@require_http_methods(["POST"])
def test_ai_connection(request):
    cfg = HiveConfiguration.objects.filter(name='default').first()
    if not cfg:
        return redirect('hive:dashboard_alert', alert_message='AI is not configured yet.')
    try:
        models = create_chat_client().models.list()
        model_ids = [model.id for model in models.data]
        selected = get_chat_model()
        if cfg.chat_provider == 'lmstudio' and selected not in model_ids:
            sample = ', '.join(model_ids[:5]) or 'none reported'
            message = f'LM Studio is reachable, but model "{selected}" was not reported. Available: {sample}'
        else:
            message = f'{cfg.chat_provider.title()} is reachable and model "{selected}" is configured.'
    except Exception as exc:
        logger.exception('AI connection test failed')
        message = f'AI connection failed: {exc}'
    return redirect('hive:dashboard_alert', alert_message=message.replace('/', ' - '))

# INTERACT - Chat with a remote conversation
class InteractionView(generic.DetailView):
    template_name = "hive/interact.html"
    model = SinglePromptChat

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['token'] = uuid.uuid4().hex
        return context

# INTERACT-POST - Handle user input during interact
@require_http_methods(["POST"])
@csrf_exempt
def interact_update(request):
    speech = request.POST['speech']
    token = request.POST['token']
    module_id = request.POST['module_id']
    content_id = request.POST['content_id'].split('|')[0]
    session = get_instance().get_web_session_for_module(token, module_id, content_id)
    volley = Volley.request_from_speech(speech, device_id=token, module_id=module_id, content_id=content_id, local_data=session.local_data)
    # Check global responses manually
    gresp = get_instance().get_web_session_global_response(volley) if speech else None
    if gresp:
        line = gresp
        details = {}
    else:
        session.handle_volley(volley)
        line = volley.debug_response_string()
        details = volley.response
    return JsonResponse({'message': line, 'details': details})

# RELOAD - Reload any records initialized from the database
@require_http_methods(["POST"])
def reload_database(request):
    get_instance().update_from_database()
    return redirect('hive:dashboard_alert', alert_message='Updated from database.')

# ENDPOINT - Render QR code to migrate Moxie
def endpoint_qr(request):
    img = qrcode.make(get_instance().get_endpoint_qr_data())
    buffer = BytesIO()
    img.save(buffer, 'PNG')
    buffer.seek(0)
    return HttpResponse(buffer, content_type='image/png')

# WIFI EDIT - Edit wifi params to create QR Code
class WifiQREditView(generic.TemplateView):
    template_name = "hive/wifi.html"

# WIFI-POST - Render QR code for Wifi Creds
@require_http_methods(["POST"])
def wifi_qr(request):
    ssid = request.POST['ssid']
    password = request.POST['password']
    band_id = request.POST['frequency']
    hidden = 'hidden' in request.POST
    img = qrcode.make(get_instance().get_wifi_qr_data(ssid, password, band_id, hidden))
    buffer = BytesIO()
    img.save(buffer, 'PNG')
    buffer.seek(0)
    return HttpResponse(buffer, content_type='image/png')

# MOXIE - View Moxie Params and config
class MoxieView(generic.DetailView):
    template_name = "hive/moxie.html"
    model = MoxieDevice

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['active_config'] = get_instance().robot_data().get_config_for_device(self.object)
        context['schedules'] = MoxieSchedule.objects.all()
        return context

# MOXIE-POST - Save changes to a Moxie record
@require_http_methods(["POST"])
def moxie_edit(request, pk):
    try:
        device = MoxieDevice.objects.get(pk=pk)
        # changes to base model
        device.name = request.POST["moxie_name"]
        device.conversation_profile = request.POST.get('conversation_profile', '').strip()
        device.conversation_memory_enabled = request.POST.get('conversation_memory_enabled') == 'on'
        device.speaker_names = [name.strip() for name in request.POST.get('speaker_names', '').splitlines() if name.strip()]
        device.schedule = MoxieSchedule.objects.get(pk=request.POST["schedule"])
        # changes to json field inside config
        if device.robot_config == None:
           # robot_config optional, create a new one to hold these
           device.robot_config = {}
        device.robot_config["screen_brightness"] = float(request.POST["screen_brightness"])
        device.robot_config["audio_volume"] = float(request.POST["audio_volume"])
        if device.robot_settings is None:
            device.robot_settings = {}
        props = device.robot_settings.setdefault('props', {})
        props['cloud_tts_voice_id'] = request.POST.get('tts_voice', 'Joanna')
        try:
            props['cloud_tts_speech_rate'] = str(max(80, min(115, int(request.POST.get('tts_speech_rate', 96)))))
        except ValueError:
            return HttpResponseBadRequest('Speech rate must be a number.')
        if "child_pii" in device.robot_config:
            device.robot_config["child_pii"]["nickname"] = request.POST["nickname"]
        else:
            device.robot_config["child_pii"] = { "nickname": request.POST["nickname"] }
        # pairing/unpairing
        device.robot_config["pairing_status"] = request.POST["pairing_status"]
        device.save()
        get_instance().handle_config_updated(device)
    except MoxieDevice.DoesNotExist as e:
        logger.warning("Moxie update for unfound pk {pk}")
    return HttpResponseRedirect(reverse("hive:dashboard"))


@require_http_methods(["POST"])
def clear_conversation_memory(request, pk):
    device = get_object_or_404(MoxieDevice, pk=pk)
    pdata = get_instance().robot_data().get_persist_for_device(device)
    pdata.pop('conversation_memory', None)
    persistent = getattr(device, 'persistentdata', None)
    if persistent:
        persistent.data = pdata
        persistent.save(update_fields=['data'])
    return redirect('hive:dashboard_alert', alert_message=f'Cleared conversation memory for {device}.')


class MoxieLauncherView(generic.DetailView):
    template_name = 'hive/launcher.html'
    model = MoxieDevice

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['built_in_modules'] = [dict(
            item,
            title=MISSION_DESCRIPTIONS.get(item['module_id'], (item['module_id'], 'Built-in Moxie activity.'))[0],
            description=MISSION_DESCRIPTIONS.get(item['module_id'], (item['module_id'], 'Built-in Moxie activity.'))[1],
        ) for item in RECOMMENDABLE_MODULES]
        remote_descriptions = {
            ('OPENMOXIE_CHAT', 'default'): 'Open-ended conversation using your selected local or cloud AI, family profile, and recent memory.',
            ('OPENMOXIE_HOMEWORK', 'default'): 'Fast, answer-first help with math, science, history, language arts, and other schoolwork—without follow-up questions.',
            ('OPENMOXIE_TRIVIA', 'default'): 'A configurable, API-free trivia game with categories, score, fun facts, and playful interludes.',
            ('OPENMOXIE_JOKES', 'default'): 'A family-managed, API-free joke mix with collections and no repeats during a run.',
            ('OPENCONVO', 'reading'): 'Talk about a book, favorite characters, and what might happen next while reading together.',
            ('OPENCONVO', 'storytelling'): 'Invent a new story together, taking turns adding characters, places, and surprising events.',
        }
        remote_names = {
            ('OPENMOXIE_CHAT', 'default'): 'Talk with Moxie',
            ('OPENMOXIE_HOMEWORK', 'default'): 'Homework help',
            ('OPENMOXIE_TRIVIA', 'default'): 'Trivia game',
            ('OPENMOXIE_JOKES', 'default'): 'Family joke time',
            ('OPENCONVO', 'reading'): 'Reading companion',
            ('OPENCONVO', 'storytelling'): 'Make a story together',
        }
        visible_remote = set(remote_descriptions)
        seen = set()
        context['remote_modules'] = []
        for chat in SinglePromptChat.objects.order_by('module_id', 'name'):
            for content_id in chat.content_id.split('|'):
                key = (chat.module_id, content_id)
                if key in seen or key not in visible_remote:
                    continue
                seen.add(key)
                context['remote_modules'].append({
                    'name': remote_names[key], 'module_id': chat.module_id, 'content_id': content_id,
                    'description': remote_descriptions[key],
                })
        context['online'] = get_instance().robot_data().device_online(self.object.device_id)
        return context


class TriviaSettingsView(generic.DetailView):
    template_name = 'hive/trivia_settings.html'
    model = MoxieDevice

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['questions'] = TriviaQuestion.objects.all()
        context['categories'] = list(
            TriviaQuestion.objects.order_by('category').values_list('category', flat=True).distinct()
        )
        return context


class JokeSettingsView(generic.DetailView):
    template_name = 'hive/joke_settings.html'
    model = MoxieDevice

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        selected = (self.object.robot_config or {}).get('joke_collections', [])
        context['selected_collections'] = selected
        context['collections'] = list(Joke.objects.order_by('collection').values_list('collection', flat=True).distinct())
        context['jokes'] = Joke.objects.all()
        return context


@require_http_methods(['POST'])
def joke_configure(request, pk):
    device = get_object_or_404(MoxieDevice, pk=pk)
    action = request.POST.get('action', 'save_options')
    if action == 'save_options':
        if device.robot_config is None:
            device.robot_config = {}
        device.robot_config['joke_collections'] = request.POST.getlist('collections')
        device.save(update_fields=['robot_config'])
        get_instance().handle_config_updated(device)
        message = 'Joke mix saved.'
    elif action == 'save_joke':
        joke_id = request.POST.get('joke_id')
        item = get_object_or_404(Joke, pk=joke_id) if joke_id else Joke()
        item.collection = request.POST.get('collection', '').strip().title()
        item.setup = request.POST.get('setup', '').strip()
        item.punchline = request.POST.get('punchline', '').strip()
        item.enabled = request.POST.get('enabled') == 'on'
        if not item.collection or not item.setup or not item.punchline:
            return HttpResponseBadRequest('Collection, setup, and punchline are required.')
        item.save()
        message = 'Joke saved.'
    elif action == 'delete_joke':
        get_object_or_404(Joke, pk=request.POST.get('joke_id')).delete()
        message = 'Joke deleted.'
    elif action == 'bulk_jokes':
        ids = request.POST.getlist('joke_ids')
        operation = request.POST.get('operation')
        query = Joke.objects.filter(pk__in=ids)
        if operation == 'enable':
            query.update(enabled=True)
        elif operation == 'disable':
            query.update(enabled=False)
        elif operation == 'delete':
            query.delete()
        else:
            return HttpResponseBadRequest('Choose a bulk action.')
        message = f'{len(ids)} jokes updated.'
    else:
        return HttpResponseBadRequest('Unknown joke configuration action.')
    return redirect(f"{reverse('hive:joke_settings', args=[device.pk])}?saved={message}")


@require_http_methods(['POST'])
def trivia_configure(request, pk):
    device = get_object_or_404(MoxieDevice, pk=pk)
    action = request.POST.get('action', 'save_options')
    if action == 'save_options':
        device.trivia_categories = request.POST.getlist('categories')
        try:
            device.trivia_question_count = max(3, min(20, int(request.POST.get('question_count', 10))))
        except ValueError:
            return HttpResponseBadRequest('Question count must be a number.')
        device.save(update_fields=['trivia_categories', 'trivia_question_count'])
        message = 'Trivia categories and game length saved.'
    elif action == 'save_question':
        question_id = request.POST.get('question_id')
        item = get_object_or_404(TriviaQuestion, pk=question_id) if question_id else TriviaQuestion()
        item.category = request.POST.get('category', '').strip().title()
        item.question = request.POST.get('question', '').strip()
        item.accepted_answers = [value.strip().lower() for value in re.split(r'[,\n]+', request.POST.get('answers', '')) if value.strip()]
        item.fun_fact = request.POST.get('fun_fact', '').strip()
        item.enabled = request.POST.get('enabled') == 'on'
        if not item.category or not item.question or not item.accepted_answers:
            return HttpResponseBadRequest('Category, question, and at least one accepted answer are required.')
        item.save()
        message = 'Trivia question saved.'
    elif action == 'delete_question':
        get_object_or_404(TriviaQuestion, pk=request.POST.get('question_id')).delete()
        message = 'Trivia question deleted.'
    elif action == 'bulk_questions':
        ids = request.POST.getlist('question_ids')
        operation = request.POST.get('operation')
        query = TriviaQuestion.objects.filter(pk__in=ids)
        if operation == 'enable':
            query.update(enabled=True)
        elif operation == 'disable':
            query.update(enabled=False)
        elif operation == 'delete':
            query.delete()
        else:
            return HttpResponseBadRequest('Choose a bulk action.')
        message = f'{len(ids)} trivia questions updated.'
    else:
        return HttpResponseBadRequest('Unknown trivia configuration action.')
    return redirect(f"{reverse('hive:trivia_settings', args=[device.pk])}?saved={message}")


@require_http_methods(["POST"])
def launch_mission(request, pk):
    device = get_object_or_404(MoxieDevice, pk=pk)
    module_id = request.POST.get('module_id', '').strip()
    content_id = request.POST.get('content_id', '').strip()
    allowed_native = {item['module_id'] for item in RECOMMENDABLE_MODULES}
    allowed_remote = SinglePromptChat.objects.filter(module_id=module_id).exists()
    if not module_id or (module_id not in allowed_native and not allowed_remote):
        return HttpResponseBadRequest('Unknown mission module.')
    base_schedule = deepcopy(device.schedule.schedule) if device.schedule else {'provided_schedule': []}
    wake_module = {'module_id': module_id}
    if content_id:
        wake_module['content_id'] = content_id
    base_schedule['wake_module'] = wake_module
    launch_schedule, _ = MoxieSchedule.objects.update_or_create(
        name=f'Launch {module_id} - {device.device_id}',
        defaults={'schedule': base_schedule, 'source_version': 1},
    )
    device.schedule = launch_schedule
    if device.robot_config is None:
        device.robot_config = {}
    device.robot_config['wake_button_enabled'] = True
    device.save(update_fields=['schedule', 'robot_config'])
    service = get_instance()
    service.handle_config_updated(device)
    service.robot_data().schedule_update_live(device)
    sent = _interrupt_and_launch(service, device, module_id, content_id or None, f'Starting {module_id}.')
    message = f'Launching {module_id}' + (f' - {content_id}' if content_id else '')
    message += ' now.' if sent else ' on the next wake; Moxie is currently offline.'
    return redirect('hive:dashboard_alert', alert_message=message)


def _set_quick_launch_schedule(device, module_id, content_id='default', label='Activity'):
    base_schedule = deepcopy(device.schedule.schedule) if device.schedule else {'provided_schedule': []}
    base_schedule['wake_module'] = {'module_id': module_id, 'content_id': content_id}
    launch_schedule, _ = MoxieSchedule.objects.update_or_create(
        name=f'Quick {label} - {device.device_id}',
        defaults={'schedule': base_schedule, 'source_version': 1},
    )
    device.schedule = launch_schedule
    if device.robot_config is None:
        device.robot_config = {}
    device.robot_config['wake_button_enabled'] = True
    device.save(update_fields=['schedule', 'robot_config'])


def _interrupt_and_launch(service, device, module_id, content_id='default', text='Starting now.'):
    """Interrupt the current activity, wake if needed, and launch with a schedule fallback."""
    if not service.robot_data().device_online(device.device_id):
        return False
    service.queue_remote_action_to_bot(device.device_id, 'launch', module_id, content_id, text)
    service.send_telehealth_interrupt(device.device_id)
    service.send_wakeup_to_bot(device.device_id)
    service.send_remote_action_to_bot(device.device_id, 'launch', module_id, content_id, text)
    return True


@require_http_methods(["POST"])
def robot_control(request, pk):
    device = get_object_or_404(MoxieDevice, pk=pk)
    action = request.POST.get('action', '')
    service = get_instance()
    online = service.robot_data().device_online(device.device_id)
    message = ''
    if action in ('wake', 'chat', 'homework', 'trivia', 'jokes', 'stop', 'interrupt'):
        target = action if action in ('homework', 'trivia', 'jokes') else 'chat'
        module_id = {
            'chat': 'OPENMOXIE_CHAT',
            'homework': 'OPENMOXIE_HOMEWORK',
            'trivia': 'OPENMOXIE_TRIVIA',
            'jokes': 'OPENMOXIE_JOKES',
        }[target]
        _set_quick_launch_schedule(device, module_id, label=target.title())
        service.handle_config_updated(device)
        service.robot_data().schedule_update_live(device)
        immediate = _interrupt_and_launch(
            service, device, module_id, 'default',
            {
                'chat': "I'm listening. What would you like to talk about?",
                'homework': 'Homework mode is ready. Tell me the problem or subject.',
                'trivia': 'Trivia time! Get your thinking cap ready.',
                'jokes': "Joke time! I've got some good ones ready.",
            }[target],
        )
        label = {'wake': 'Wake and Chat', 'stop': 'Stop and Chat', 'interrupt': 'Stop and Chat'}.get(action, action.title())
        message = label + (' launched immediately.' if immediate else ' queued for the next connection.')
    elif action == 'sleep':
        if online:
            sent = service.queue_remote_action_to_bot(device.device_id, 'sleep', text='Okay. Good night!')
            service.send_telehealth_interrupt(device.device_id)
            # Wake is also used as a router nudge. If Moxie is already awake it is
            # harmless; if she is between activities it causes the request that
            # consumes the queued sleep action instead of launching a schedule.
            service.send_wakeup_to_bot(device.device_id)
            service.send_remote_action_to_bot(device.device_id, 'sleep', text='Okay. Good night!')
        else:
            sent = False
        message = 'Sleep requested. Waiting for Moxie to report sleep; voice fallback: “Go to sleep, please.”' if sent else 'Moxie is offline; no sleep command was sent.'
    else:
        return HttpResponseBadRequest('Unknown robot action.')
    command_status = 'sent' if online else 'failed'
    RobotCommandEvent.objects.create(
        device=device, action=action, label={
            'wake': 'Wake & Chat', 'chat': 'Start chat', 'homework': 'Start homework',
            'trivia': 'Start trivia', 'jokes': 'Start joke time', 'stop': 'Stop & Chat', 'interrupt': 'Stop activity',
            'sleep': 'Go to sleep',
        }.get(action, action.title()), status=command_status,
        detail=message,
    )
    if request.POST.get('ajax') == '1':
        return JsonResponse({'ok': True, 'message': message})
    return redirect('hive:dashboard_alert', alert_message=message)

# MOXIE - Edit Moxie Face Customizations
class MoxieFaceView(generic.DetailView):
    template_name = "hive/face.html"
    model = MoxieDevice

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['assets'] = get_moxie_customization_groups()
        context['face_options'] = get_instance().robot_data().get_config_for_device(self.object).get('child_pii', {}).get('face_options', [])
        return context

# FACE-POST - Save changes to a Moxie Face
@require_http_methods(["POST"])
def face_edit(request, pk):
    try:
        device = MoxieDevice.objects.get(pk=pk)
        new_face = []
        for key in request.POST.keys():
            if key.startswith('asset_'):
                val = request.POST[key]
                if val != '--':
                    new_face.append(val)

        if "child_pii" in device.robot_config:
            device.robot_config["child_pii"]["face_options"] = new_face
        else:
            device.robot_config["child_pii"] = { "face_options": new_face }

        # Moxie-Unity keeps a cached record of face textture keyed by the 'id' field.  This
        # Sets a new unique id to invalidate any old/corrupt cached record
        suffix = ''
        if request.POST.get('child_recover'):
            device.robot_config["child_pii"]["id"] = str(uuid.uuid4())
            suffix = " - Created new child ID"

        device.save()
        get_instance().handle_config_updated(device)
        return redirect('hive:dashboard_alert', alert_message=f'Updated face for {device}{suffix}')
    except MoxieDevice.DoesNotExist as e:
        logger.warning("Moxie update for unfound pk {pk}")
        return redirect('hive:dashboard_alert', alert_message='No such Moxie')

# MOXIE - Puppeteer Moxie
class MoxiePuppetView(generic.DetailView):
    template_name = "hive/puppet.html"
    model = MoxieDevice

# PUPPET API - Handle AJAX calls from puppet view
@csrf_exempt
def puppet_api(request, pk):
    try:
        device = MoxieDevice.objects.get(pk=pk)
        if request.method == 'GET':
            # Handle GET request
            result = { 
                "online": get_instance().robot_data().device_online(device.device_id),
                "puppet_state": get_instance().robot_data().get_puppet_state(device.device_id),
                "puppet_enabled": device.robot_config.get("moxie_mode") == "TELEHEALTH" if device.robot_config else False
            }
            return JsonResponse(result)
        elif request.method == 'POST':
            # Handle COMMANDS request
            if not device.robot_config:
                device.robot_config = {}
            cmd = request.POST['command']
            if cmd == "enable":
                device.robot_config["moxie_mode"] = "TELEHEALTH"
                device.save()
                get_instance().handle_config_updated(device)
            elif cmd == "disable":
                device.robot_config.pop("moxie_mode", None)
                device.save()
                get_instance().handle_config_updated(device)
            elif cmd == "interrupt":
                get_instance().send_telehealth_interrupt(device.device_id)
            elif cmd == "speak":
                get_instance().send_telehealth_speech(device.device_id, request.POST['speech'], 
                                                      request.POST['mood'], float(request.POST['intensity']))
        return JsonResponse({'result': True})
    except MoxieDevice.DoesNotExist as e:
        logger.warning("Moxie puppet speak for unfound pk {pk}")
        return HttpResponseBadRequest()
    
# MOXIE - View Moxie Mission Sets to Complete
class MoxieMissionsView(generic.DetailView):
    template_name = "hive/missions.html"
    model = MoxieDevice

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # list of tupes (key,prettykey)
        context['mission_sets'] = [ (key, key.replace("_", " ")) for key in DM_MISSION_CONTENT_IDS.keys() ]
        return context

# MOXIE-POST - Save changes to a Moxie record
@require_http_methods(["POST"])
def mission_edit(request, pk):
    try:
        device = MoxieDevice.objects.get(pk=pk)

        mission_action = request.POST["mission_action"]
        if mission_action == "reset":
            # Delete all MBH to start fresh
            MentorBehavior.objects.filter(device=device).delete()
            msg = f'Reset ALL progress for {device}'
        else:
            # Handle mission set actions... get all the CIDs for the selected sets
            mission_sets = request.POST.getlist("mission_sets")
            dm_cid_list = [cid for ms in mission_sets for cid in DM_MISSION_CONTENT_IDS.get(ms, [])]
            if mission_action == "forget":
                # Delete any records with these module/content ID (completed, quit)
                MentorBehavior.objects.filter(device=device, module_id='DM', content_id__in=dm_cid_list).delete()
                msg = f'Forgot {len(mission_sets)} Daily Mission Sets ({len(dm_cid_list)} missions) for {device}'
            else: # == "complete"
                # Create new completions for all these mission content IDs
                get_instance().robot_data().add_mbh_completion_bulk(device.device_id, module_id="DM", content_id_list=dm_cid_list)
                msg = f'Completed {len(mission_sets)} Daily Mission Sets ({len(dm_cid_list)} missions) for {device}'

        return redirect('hive:dashboard_alert', alert_message=msg)
    except MoxieDevice.DoesNotExist as e:
        logger.warning("Moxie update for unfound pk {pk}")
        return redirect('hive:dashboard_alert', alert_message='No such Moxie')

# Enable wake-button support and wake a connected Moxie.
@require_http_methods(["POST"])
def moxie_wake(request, pk):
    try:
        device = MoxieDevice.objects.get(pk=pk)
        if device.robot_config is None:
            device.robot_config = {}
        device.robot_config['wake_button_enabled'] = True
        device.save(update_fields=['robot_config'])
        get_instance().handle_config_updated(device)
        logger.info(f'Waking up {device}')
        alert_msg = "Wake message sent. Watch the live Mode value for confirmation." if get_instance().send_wakeup_to_bot(device.device_id) else 'Moxie was offline.'
        return redirect('hive:dashboard_alert', alert_message=alert_msg)
    except MoxieDevice.DoesNotExist as e:
        logger.warning("Moxie wake for unfound pk {pk}")
        return redirect('hive:dashboard_alert', alert_message='No such Moxie')

# Wake directly into the OpenMoxie chat module. The derived schedule can be
# changed back from the normal Moxie edit screen.
@require_http_methods(["POST"])
def moxie_wake_chat(request, pk):
    try:
        device = MoxieDevice.objects.get(pk=pk)
        if not device.schedule:
            return redirect('hive:dashboard_alert', alert_message='Moxie has no schedule to use for chat.')

        schedule_data = deepcopy(device.schedule.schedule)
        schedule_data['wake_module'] = {
            'module_id': 'OPENMOXIE_CHAT',
            'content_id': 'default',
        }
        schedule_name = f'Wake to Chat - {device.device_id}'
        chat_schedule, _ = MoxieSchedule.objects.update_or_create(
            name=schedule_name,
            defaults={'schedule': schedule_data, 'source_version': 1},
        )
        device.schedule = chat_schedule
        if device.robot_config is None:
            device.robot_config = {}
        device.robot_config['wake_button_enabled'] = True
        device.save(update_fields=['schedule', 'robot_config'])
        get_instance().handle_config_updated(device)
        get_instance().robot_data().schedule_update_live(device)
        logger.info('Waking %s directly into OpenMoxie chat', device)
        sent = get_instance().send_wakeup_to_bot(device.device_id)
        message = 'Wake & Chat sent. Moxie should open with a chat prompt.' if sent else 'Moxie was offline.'
        return redirect('hive:dashboard_alert', alert_message=message)
    except MoxieDevice.DoesNotExist:
        return redirect('hive:dashboard_alert', alert_message='No such Moxie')

# MOXIE - Export Moxie Content Data - Selection View
class ExportDataView(generic.TemplateView):
    template_name = "hive/export.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['conversations'] = SinglePromptChat.objects.all()
        context['schedules'] = MoxieSchedule.objects.all()
        context['globals'] = GlobalResponse.objects.all()
        return context
    
# MOXIE - Export Moxie Content Data - Save Action
@require_http_methods(["POST"])
def export_data(request):
    content_name = request.POST['content_name']
    content_details = request.POST['content_details']
    globals = request.POST.getlist("globals")
    schedules = request.POST.getlist("schedules")
    conversations = request.POST.getlist("conversations")
    if not content_name:
        content_name = 'moxie_content'
    output = { "name": content_name, "details": content_details }
    for pk in globals:
        r = GlobalResponse.objects.get(pk=pk)
        rec = model_to_dict(r, exclude=['id'])
        output["globals"] = output.get("globals", []) + [rec]
    for pk in schedules:
        r = MoxieSchedule.objects.get(pk=pk)
        rec = model_to_dict(r, exclude=['id'])
        output["schedules"] = output.get("schedules", []) + [rec]
    for pk in conversations:
        r = SinglePromptChat.objects.get(pk=pk)
        rec = model_to_dict(r, exclude=['id'])
        output["conversations"] = output.get("conversations", []) + [rec]
    # Save output as JSON file
    response = JsonResponse(output, json_dumps_params={'indent': 4})
    response['Content-Disposition'] = f'attachment; filename="{content_name}.json"'
    return response

# MOXIE - Import Moxie Content Data
@require_http_methods(['POST'])
def upload_import_data(request):
    json_file = request.FILES.get('json_file')
    if not json_file:
        return JsonResponse({'error': 'No file uploaded'}, status=400)

    try:
        json_data = json.loads(json_file.read().decode('utf-8'))
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON file'}, status=400)

    # Preprocess the JSON data to build the context for the template
    update_import_status(json_data)
    context = {
        'json_data': json_data,
        'json_data_str': json.dumps(json_data)
        # Add other context variables as needed
    }
    return render(request, 'hive/import.html', context)

@require_http_methods(['POST'])
def import_data(request):
    # these hold indexes into the source JSON arrays that we want to import
    g_list = request.POST.getlist("globals")
    s_list = request.POST.getlist("schedules")
    c_list = request.POST.getlist("conversations")
    # the original JSON upload, passed back to us
    jstring = request.POST.get("json_data")
    logger.info(f'IMPORTING {jstring}')
    json_data = json.loads(jstring)
    # finally import the data
    message = import_content(json_data, g_list, s_list, c_list)
    # and refresh all things
    get_instance().update_from_database()
    return redirect('hive:dashboard_alert', alert_message=message)

# MOXIE - View Moxie Data
class MoxieDataView(generic.DetailView):
    template_name = "hive/moxie_data.html"
    model = MoxieDevice

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['active_config'] = json.dumps(get_instance().robot_data().get_config_for_device(self.object))
        context['persist_data'] = json.dumps(get_instance().robot_data().get_persist_for_device(self.object))
        return context
