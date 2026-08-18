from django.db import migrations, models


DEFAULT_PROFILE = (
    "You are Moxie, a warm, playful, age-appropriate robot friend. Keep replies short and "
    "conversational, ask at most one question at a time, and encourage the child to talk to "
    "a trusted adult about safety, health, or anything that worries them."
)


class Migration(migrations.Migration):
    dependencies = [('hive', '0017_update_default_chat_model')]

    operations = [
        migrations.AddField(model_name='hiveconfiguration', name='chat_provider', field=models.CharField(default='openai', max_length=20)),
        migrations.AddField(model_name='hiveconfiguration', name='chat_base_url', field=models.CharField(blank=True, default='http://host.docker.internal:1234/v1', max_length=500)),
        migrations.AddField(model_name='hiveconfiguration', name='chat_model', field=models.CharField(default='gpt-4o-mini', max_length=255)),
        migrations.AddField(model_name='hiveconfiguration', name='stt_provider', field=models.CharField(default='openai', max_length=20)),
        migrations.AddField(model_name='hiveconfiguration', name='local_stt_model', field=models.CharField(default='small.en', max_length=100)),
        migrations.AddField(model_name='moxiedevice', name='conversation_profile', field=models.TextField(default=DEFAULT_PROFILE)),
        migrations.AddField(model_name='moxiedevice', name='conversation_memory_enabled', field=models.BooleanField(default=True)),
    ]
