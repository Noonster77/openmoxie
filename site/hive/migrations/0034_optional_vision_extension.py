from django.db import migrations, models


def seed_vision(apps, schema_editor):
    Chat = apps.get_model('hive', 'SinglePromptChat')
    Response = apps.get_model('hive', 'GlobalResponse')
    for module_id, name, opener in (
        ('OPENMOXIE_VISION', 'Local Object Vision', 'My local camera mode is ready.'),
        ('OPENMOXIE_ISPY', 'I Spy With My Little Eye', 'I spy with my little eye something in this room.'),
    ):
        Chat.objects.update_or_create(
            module_id=module_id, content_id='default',
            defaults={
                'name': name, 'source_version': 1, 'model': '', 'max_history': 4,
                'max_volleys': 9999, 'max_tokens': 80, 'temperature': .2,
                'question_probability': 0, 'prompt': 'Handled by the local vision session.',
                'opener': opener,
            },
        )
    code = (
        "def handle_volley(volley):\n"
        "    from hive.models import HiveConfiguration, MoxieDevice\n"
        "    from hive.mqtt.moxie_server import get_instance\n"
        "    from hive.vision import service_status, set_device_vision\n"
        "    cfg = HiveConfiguration.objects.filter(name='default').first()\n"
        "    device = MoxieDevice.objects.filter(device_id=volley.device_id).first()\n"
        "    if not cfg or not cfg.vision_extension_enabled or not device:\n"
        "        volley.set_output('A grown-up needs to enable my optional local Vision extension first.', None)\n"
        "        return\n"
        "    if not service_status().get('reachable'):\n"
        "        volley.set_output('My local Vision service is not running. Please start it from Parent Corner.', None)\n"
        "        return\n"
        "    mode = 'ispy' if 'spy' in volley.request.get('speech', '').lower() else 'vision'\n"
        "    module = 'OPENMOXIE_ISPY' if mode == 'ispy' else 'OPENMOXIE_VISION'\n"
        "    set_device_vision(device, True, mode=mode, service=get_instance())\n"
        "    volley.set_output('Opening my local camera for I Spy!' if mode == 'ispy' else 'Opening my local camera. Ask me what I see!', None)\n"
        "    volley.add_response_action('launch', module_id=module, content_id='default', output_type='GLOBAL_COMMAND')"
    )
    Response.objects.update_or_create(
        name='Start Optional Vision',
        defaults={
            'pattern': r'^(?:(?:moxie|moxy|foxy|boxy|oxy)[, ]+)?(?:please )?(?:start|open|turn on|use|enter)? ?(?:vision|camera)(?: mode)?[.!]?$',
            'action': 4, 'response_text': '', 'code': code, 'sort_key': 120, 'source_version': 1,
        },
    )
    Response.objects.update_or_create(
        name='Start Optional I Spy',
        defaults={
            'pattern': r'^(?:(?:moxie|moxy|foxy|boxy|oxy)[, ]+)?(?:please )?(?:play|start|launch) i spy(?: with my little eye)?[.!]?$',
            'action': 4, 'response_text': '', 'code': code, 'sort_key': 121, 'source_version': 1,
        },
    )


def unseed_vision(apps, schema_editor):
    apps.get_model('hive', 'GlobalResponse').objects.filter(
        name__in=['Start Optional Vision', 'Start Optional I Spy']
    ).delete()
    apps.get_model('hive', 'SinglePromptChat').objects.filter(
        module_id__in=['OPENMOXIE_VISION', 'OPENMOXIE_ISPY']
    ).delete()


class Migration(migrations.Migration):
    dependencies = [('hive', '0033_conversationevent_safety_reviewed_at')]

    operations = [
        migrations.AddField(
            model_name='hiveconfiguration',
            name='vision_extension_enabled',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='moxiedevice',
            name='vision_active',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='moxiedevice',
            name='vision_mode',
            field=models.CharField(blank=True, default='', max_length=20),
        ),
        migrations.AddField(
            model_name='moxiedevice',
            name='vision_config_backup',
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.RunPython(seed_vision, unseed_vision),
    ]
