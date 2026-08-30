from django.db import migrations


def restore_fast_homework_responses(apps, schema_editor):
    SinglePromptChat = apps.get_model('hive', 'SinglePromptChat')
    SinglePromptChat.objects.filter(
        module_id='OPENMOXIE_HOMEWORK', content_id='default'
    ).update(max_tokens=224, max_history=16, source_version=4)


class Migration(migrations.Migration):
    dependencies = [('hive', '0030_raise_conversation_token_budgets')]
    operations = [
        migrations.RunPython(
            restore_fast_homework_responses,
            migrations.RunPython.noop,
        ),
    ]
