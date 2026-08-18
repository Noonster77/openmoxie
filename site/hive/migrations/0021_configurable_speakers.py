from django.db import migrations, models


def configure_existing_profiles(apps, schema_editor):
    MoxieDevice = apps.get_model('hive', 'MoxieDevice')
    GlobalResponse = apps.get_model('hive', 'GlobalResponse')
    for device in MoxieDevice.objects.all():
        if 'Jack' in (device.conversation_profile or ''):
            device.speaker_names = ['Jack', 'Daddy', 'Josh']
        else:
            nickname = (device.robot_config or {}).get('child_pii', {}).get('nickname')
            device.speaker_names = [nickname] if nickname else ['Friend']
        device.save(update_fields=['speaker_names'])
    GlobalResponse.objects.update_or_create(
        name='Identify Speaker',
        defaults={
            'pattern': r"^(?:(?:moxie|moxy)[, ]+)?(?:i am|i'm|this is|it is) ([a-z][a-z -]{0,30})[.!]?$",
            'entity_groups': '1', 'action': 4, 'response_text': 'Hello!',
            'code': "def handle_volley(volley):\n    claimed = volley.entities[0].strip()\n    allowed = {name.lower(): name for name in volley.speaker_names}\n    display = allowed.get(claimed.lower())\n    if display:\n        volley.persist_data['active_speaker'] = display\n        volley.set_output(f'Hi {display}! I will remember who is talking.', None)\n    else:\n        volley.set_output(f'I do not have {claimed} in my speaker list yet. A grown-up can add that name in my OpenMoxie settings.', None)",
            'sort_key': 100, 'source_version': 2,
        },
    )


class Migration(migrations.Migration):
    dependencies = [('hive', '0020_alter_globalresponse_action')]
    operations = [
        migrations.AddField(model_name='moxiedevice', name='speaker_names', field=models.JSONField(blank=True, default=list)),
        migrations.RunPython(configure_existing_profiles, migrations.RunPython.noop),
    ]
