from django.db import migrations


def update_sleep_pattern(apps, schema_editor):
    GlobalResponse = apps.get_model('hive', 'GlobalResponse')
    GlobalResponse.objects.filter(name='Go To Sleep').update(
        pattern=r'^(?:(?:moxie|moxy|foxy|boxy|oxy)[, ]+)?(?:please )?(?:go to sleep|go back to sleep|time for bed|sleep now)(?:,? please)?[.!]?$',
        source_version=2,
    )


class Migration(migrations.Migration):
    dependencies = [('hive', '0023_trivia_configuration')]
    operations = [migrations.RunPython(update_sleep_pattern, migrations.RunPython.noop)]
