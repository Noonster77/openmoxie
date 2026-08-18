from django.db import migrations, models
import django.db.models.deletion


def add_voice_actions(apps, schema_editor):
    GlobalResponse = apps.get_model('hive', 'GlobalResponse')
    records = [
        dict(name='Play Trivia', pattern=r'^(?:(?:moxie|moxy|foxy|boxy|oxy)[, ]+)?(?:please )?(?:play|start|launch) trivia(?: game)?[.!]?$', action=2, response_text="Let's play trivia!", module_id='OPENMOXIE_TRIVIA', content_id='default', sort_key=100),
        dict(name='Go To Sleep', pattern=r'^(?:(?:moxie|moxy|foxy|boxy|oxy)[, ]+)?(?:please )?(?:go to sleep|go back to sleep|time for bed|sleep now)[.!]?$', action=5, response_text='Okay. Good night!', sort_key=100),
        dict(name='Talk About Something Else', pattern=r'^(?:(?:moxie|moxy|foxy|boxy|oxy)[, ]+)?(?:let us |let\'s )?(?:talk|chat) about something else[.!]?$', action=2, response_text='Sure, what would you like to talk about?', module_id='OPENMOXIE_CHAT', content_id='default', sort_key=100),
        dict(name='Stop Current Activity', pattern=r'^(?:(?:moxie|moxy|foxy|boxy|oxy)[, ]+)?(?:please )?(?:stop|stop this|stop this mission|stop the game|never mind|listen to me)[.!]?$', action=6, response_text='Okay, I stopped. What would you like to do next?', sort_key=90),
        dict(name='Identify Speaker', pattern=r"^(?:(?:moxie|moxy)[, ]+)?(?:i am|i'm|this is|it is) (jack|daddy|dad|josh)[.!]?$", entity_groups='1', action=4, response_text='Hello!', code="def handle_volley(volley):\n    name = volley.entities[0].lower()\n    display = 'Jack' if name == 'jack' else 'Daddy'\n    volley.persist_data['active_speaker'] = display\n    volley.set_output(f'Hi {display}! I will remember who is talking for this session.', None)", sort_key=100),
    ]
    for record in records:
        record['source_version'] = 1
        GlobalResponse.objects.update_or_create(name=record['name'], defaults=record)


class Migration(migrations.Migration):
    dependencies = [('hive', '0018_local_ai_profile_memory')]
    operations = [
        migrations.CreateModel(
            name='ConversationEvent',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('role', models.CharField(max_length=20)),
                ('text', models.TextField()),
                ('module_id', models.CharField(blank=True, default='', max_length=100)),
                ('content_id', models.CharField(blank=True, default='', max_length=100)),
                ('safety_flagged', models.BooleanField(db_index=True, default=False)),
                ('safety_categories', models.JSONField(blank=True, default=list)),
                ('device', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='conversation_events', to='hive.moxiedevice')),
            ],
            options={'ordering': ['created_at']},
        ),
        migrations.AddIndex(model_name='conversationevent', index=models.Index(fields=['device', 'created_at'], name='conversation_device_time')),
        migrations.RunPython(add_voice_actions, migrations.RunPython.noop),
    ]
