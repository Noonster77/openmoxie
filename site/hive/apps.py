from django.apps import AppConfig
from django.db.backends.signals import connection_created


def configure_sqlite_connection(sender, connection, **kwargs):
    """Favor concurrent readers and bounded writer waits for MQTT workloads."""
    if connection.vendor != 'sqlite':
        return
    with connection.cursor() as cursor:
        cursor.execute('PRAGMA journal_mode=WAL')
        cursor.execute('PRAGMA synchronous=NORMAL')
        cursor.execute('PRAGMA busy_timeout=10000')

class HiveConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'hive'

    def ready(self):
        connection_created.connect(
            configure_sqlite_connection,
            dispatch_uid='hive.configure_sqlite_connection',
        )
