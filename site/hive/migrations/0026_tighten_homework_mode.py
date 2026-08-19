from django.db import migrations


HOMEWORK_PROMPT = (
    "You are Moxie's rapid-answer homework calculator and reference helper. Return only the answer "
    "and, when essential, one very short explanation. Never ask any question. Never quiz, prompt, "
    "request confirmation, offer more help, or continue the conversation. Prioritize math and school "
    "problems. Keep every reply under two short sentences and under 45 spoken words. Calculate carefully. "
    "If unsure, say so briefly instead of inventing facts."
)


def tighten_homework_mode(apps, schema_editor):
    apps.get_model('hive', 'SinglePromptChat').objects.filter(
        module_id='OPENMOXIE_HOMEWORK', content_id='default'
    ).update(
        source_version=2,
        prompt=HOMEWORK_PROMPT,
        max_tokens=45,
        temperature=0.1,
        question_probability=0.0,
    )
    apps.get_model('hive', 'GlobalResponse').objects.filter(
        name='Start Homework Mode'
    ).update(
        pattern=r'^(?:(?:moxie|moxy|foxy|boxy|oxy)[, ]+)?(?:please )?(?:(?:start|open|launch|begin)(?: my)? )?homework(?: help| mode)?[.!]?$',
        source_version=2,
    )


class Migration(migrations.Migration):
    dependencies = [('hive', '0025_homework_mode')]
    operations = [migrations.RunPython(tighten_homework_mode, migrations.RunPython.noop)]
