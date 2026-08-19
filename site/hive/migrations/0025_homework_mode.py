from django.db import migrations, models


HOMEWORK_PROMPT = (
    "You are Moxie's fast, answer-first homework helper. Prioritize schoolwork questions in math, "
    "science, history, geography, language arts, and related subjects. Give the direct answer first, "
    "followed by only the shortest explanation needed to understand it. For arithmetic and simple math, "
    "calculate carefully and state the result immediately. Never ask a question, quiz the person, request "
    "confirmation, or offer additional help. If a request is ambiguous, use the most likely interpretation "
    "and briefly state your assumption. If you are unsure, say so plainly instead of inventing facts. Keep "
    "every response concise, accurate, age-appropriate, and easy to understand when spoken aloud."
)


def add_homework_mode(apps, schema_editor):
    SinglePromptChat = apps.get_model('hive', 'SinglePromptChat')
    GlobalResponse = apps.get_model('hive', 'GlobalResponse')
    SinglePromptChat.objects.update_or_create(
        module_id='OPENMOXIE_HOMEWORK', content_id='default',
        defaults={
            'name': 'OpenMoxie Homework Help', 'source_version': 1, 'model': 'gpt-4o-mini',
            'prompt': HOMEWORK_PROMPT,
            'opener': 'Homework mode is ready. Tell me the problem or subject.',
            'max_history': 8, 'max_volleys': 9999, 'max_tokens': 100,
            'temperature': 0.1, 'question_probability': 0.0,
        },
    )
    GlobalResponse.objects.update_or_create(
        name='Start Homework Mode',
        defaults={
            'pattern': r'^(?:(?:moxie|moxy|foxy|boxy|oxy)[, ]+)?(?:please )?(?:start|open|launch|begin)(?: my)? homework(?: help| mode)?[.!]?$',
            'action': 2,
            'response_text': 'Homework mode is ready. Tell me the problem or subject.',
            'module_id': 'OPENMOXIE_HOMEWORK', 'content_id': 'default',
            'sort_key': 100, 'source_version': 1,
        },
    )


def remove_homework_mode(apps, schema_editor):
    apps.get_model('hive', 'GlobalResponse').objects.filter(name='Start Homework Mode').delete()
    apps.get_model('hive', 'SinglePromptChat').objects.filter(
        module_id='OPENMOXIE_HOMEWORK', content_id='default'
    ).delete()


class Migration(migrations.Migration):
    dependencies = [('hive', '0024_flexible_sleep_voice_command')]
    operations = [
        migrations.AddField(
            model_name='singlepromptchat', name='question_probability',
            field=models.FloatField(default=0.35),
        ),
        migrations.RunPython(add_homework_mode, remove_homework_mode),
    ]
