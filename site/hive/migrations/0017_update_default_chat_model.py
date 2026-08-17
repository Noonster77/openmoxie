from django.db import migrations, models


def update_legacy_chat_models(apps, schema_editor):
    SinglePromptChat = apps.get_model('hive', 'SinglePromptChat')
    SinglePromptChat.objects.filter(model='gpt-3.5-turbo').update(model='gpt-4o-mini')


class Migration(migrations.Migration):
    dependencies = [
        ('hive', '0016_globalresponse_source_version'),
    ]

    operations = [
        migrations.AlterField(
            model_name='singlepromptchat',
            name='model',
            field=models.CharField(default='gpt-4o-mini', max_length=200),
        ),
        migrations.RunPython(update_legacy_chat_models, migrations.RunPython.noop),
    ]
