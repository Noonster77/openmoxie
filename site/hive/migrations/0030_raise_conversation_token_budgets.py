from django.db import migrations


def raise_conversation_token_budgets(apps, schema_editor):
    SinglePromptChat = apps.get_model('hive', 'SinglePromptChat')
    SinglePromptChat.objects.filter(
        module_id='OPENMOXIE_CHAT', content_id__in=['default', 'short']
    ).update(max_tokens=120, source_version=4)
    SinglePromptChat.objects.filter(
        module_id='OPENMOXIE_HOMEWORK', content_id='default'
    ).update(max_tokens=512, source_version=3)


class Migration(migrations.Migration):
    dependencies = [('hive', '0029_disabled_activity_rotation')]
    operations = [
        migrations.RunPython(
            raise_conversation_token_budgets,
            migrations.RunPython.noop,
        ),
    ]
