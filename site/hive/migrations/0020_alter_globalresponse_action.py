from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('hive', '0019_conversationevent_voice_actions')]
    operations = [
        migrations.AlterField(
            model_name='globalresponse',
            name='action',
            field=models.IntegerField(
                choices=[(1, 'RESPONSE'), (2, 'LAUNCH'), (3, 'CONFIRM_LAUNCH'), (4, 'METHOD'), (5, 'SLEEP'), (6, 'EXIT')],
                default=1,
            ),
        ),
    ]
