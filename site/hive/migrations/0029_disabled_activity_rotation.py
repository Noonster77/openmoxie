from django.db import migrations, models
import hive.models


class Migration(migrations.Migration):
    dependencies = [('hive', '0028_family_content_library')]
    operations = [
        migrations.AddField(
            model_name='moxiedevice',
            name='disabled_module_ids',
            field=models.JSONField(blank=True, default=hive.models.default_disabled_modules),
        ),
    ]
