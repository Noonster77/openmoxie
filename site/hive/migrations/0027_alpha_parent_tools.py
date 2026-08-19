from django.db import migrations, models
import django.db.models.deletion


STARTER_JOKES = [
    ('Animal antics', 'What do you call a sleeping bull?', 'A bulldozer.'),
    ('Animal antics', 'What do cats eat for breakfast?', 'Mice crispies.'),
    ('School smiles', 'Why did the math book look sad?', 'It had too many problems.'),
    ('School smiles', 'Why did the student eat their homework?', 'The teacher said it was a piece of cake.'),
    ('Silly science', 'What is a robot’s favorite snack?', 'Computer chips.'),
    ('Silly science', 'Why can’t you trust an atom?', 'Because they make up everything.'),
]


def seed_jokes(apps, schema_editor):
    Joke = apps.get_model('hive', 'Joke')
    for collection, setup, punchline in STARTER_JOKES:
        Joke.objects.get_or_create(
            setup=setup,
            defaults={'collection': collection, 'punchline': punchline, 'enabled': True},
        )
    SinglePromptChat = apps.get_model('hive', 'SinglePromptChat')
    SinglePromptChat.objects.update_or_create(
        module_id='OPENMOXIE_JOKES', content_id='default',
        defaults={
            'name': 'OpenMoxie Family Jokes', 'opener': "Let's tell some jokes!",
            'prompt': 'Deterministic local joke player; no AI provider is used.',
            'model': 'gpt-4o-mini', 'max_volleys': 9999, 'source_version': 1,
        },
    )
    GlobalResponse = apps.get_model('hive', 'GlobalResponse')
    GlobalResponse.objects.update_or_create(
        name='Tell Jokes',
        defaults={
            'pattern': r'^(?:(?:moxie|moxy|foxy|boxy|oxy)[, ]+)?(?:please )?(?:tell|play|start) (?:me )?(?:some )?jokes?[.!]?$',
            'action': 2, 'response_text': "Let's tell some jokes!", 'module_id': 'OPENMOXIE_JOKES',
            'content_id': 'default', 'sort_key': 100, 'source_version': 1,
        },
    )


class Migration(migrations.Migration):
    dependencies = [('hive', '0026_tighten_homework_mode')]
    operations = [
        migrations.AddField(
            model_name='moxiedevice',
            name='trivia_seen_question_ids',
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.CreateModel(
            name='Joke',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('collection', models.CharField(db_index=True, default='Family favorites', max_length=60)),
                ('setup', models.TextField()),
                ('punchline', models.TextField()),
                ('enabled', models.BooleanField(db_index=True, default=True)),
            ],
            options={'ordering': ['collection', 'setup']},
        ),
        migrations.CreateModel(
            name='RobotCommandEvent',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('action', models.CharField(max_length=40)),
                ('label', models.CharField(blank=True, default='', max_length=100)),
                ('status', models.CharField(default='sent', max_length=20)),
                ('detail', models.CharField(blank=True, default='', max_length=255)),
                ('device', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='command_events', to='hive.moxiedevice')),
            ],
            options={'ordering': ['-created_at']},
        ),
        migrations.RunPython(seed_jokes, migrations.RunPython.noop),
    ]
