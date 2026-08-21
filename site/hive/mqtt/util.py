import logging
import threading
import time

from django.db import OperationalError, connections, transaction


logger = logging.getLogger(__name__)
_DB_WRITE_LOCK = threading.RLock()

def now_ms():
    return time.time_ns() // 1_000_000

# Execute a block of db interactions inside an atomic transaction
def run_db_atomic(functor, *args, **kwargs):
    """Run a short DB unit with ordered writes and retry transient SQLite locks."""
    alias = 'default'
    attempts = 4
    for attempt in range(attempts):
        try:
            # SQLite permits one writer. Ordering MQTT writes also preserves the
            # state sequence when several worker callbacks arrive together.
            with _DB_WRITE_LOCK:
                with transaction.atomic(using=alias):
                    return functor(*args, **kwargs)
        except OperationalError as exc:
            if 'locked' not in str(exc).lower() or attempt == attempts - 1:
                raise
            delay = 0.05 * (2 ** attempt)
            logger.warning(
                'SQLite busy during %s; retrying in %.2fs (%d/%d)',
                getattr(functor, '__name__', 'database operation'),
                delay, attempt + 1, attempts,
            )
            connections[alias].close()
            time.sleep(delay)
