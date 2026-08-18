from django.db import migrations


def update_speaker_command(apps, schema_editor):
    GlobalResponse = apps.get_model('hive', 'GlobalResponse')
    GlobalResponse.objects.filter(name='Identify Speaker').update(code=(
        "def handle_volley(volley):\n"
        "    claimed = volley.entities[0].strip()\n"
        "    allowed = {name.lower(): name for name in volley.speaker_names}\n"
        "    display = allowed.get(claimed.lower())\n"
        "    if display:\n"
        "        volley.persist_data['active_speaker'] = display\n"
        "        volley.set_output(f'Hi {display}! I will remember who is talking.', None)\n"
        "    else:\n"
        "        volley.set_output(f'I do not have {claimed} in my speaker list yet. "
        "A grown-up can add that name in my OpenMoxie settings.', None)"
    ))


class Migration(migrations.Migration):
    dependencies = [('hive', '0021_configurable_speakers')]
    operations = [migrations.RunPython(update_speaker_command, migrations.RunPython.noop)]
