from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('hive', '0032_reasoning_and_content_overhaul')]

    operations = [
        migrations.AddField(
            model_name='conversationevent',
            name='safety_reviewed_at',
            field=models.DateTimeField(blank=True, db_index=True, null=True),
        ),
    ]
