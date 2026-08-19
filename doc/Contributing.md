# Contributing to OpenMoxie

## Project map

- `site/hive/models.py`: persistent application data.
- `site/hive/views.py` and `site/hive/urls.py`: web behavior and routes.
- `site/hive/templates` and `site/static/hive`: family interface.
- `site/hive/mqtt`: robot protocol, remote conversations, schedules, speech recognition, and logging.
- `site/data`: default content imported into the database.
- `content_modules`: optional portable content packages.
- `doc`: protocol and operating documentation.

## Development loop

1. Create a branch and preserve `local/work`; it contains user data.
2. Install `requirements.txt` or build the Docker services.
3. For model changes, create a numbered Django migration. Seed data through migrations or versioned import data.
4. Add focused tests in `site/hive/tests.py`.
5. Run `python site/manage.py makemigrations --check --dry-run`, `python site/manage.py check`, and `python site/manage.py test hive`.
6. Render and exercise changed pages at desktop and mobile widths.
7. Update the README or the relevant document when behavior or setup changes.

## Design principles

- Keep family data local by default and make deletion complete and understandable.
- Separate “message published” from “robot confirmed.”
- Prefer deterministic, API-free implementations for simple games.
- Never silently collect camera, face, or identity data.
- Make parent controls legible without exposing raw protocol concepts.
- Preserve advanced diagnostics, but redact secrets and place them behind a clear technical disclosure.
- Treat robot firmware as fallible: handle disconnects, duplicate notifications, stale state, and unsupported assets.

## Adding an activity

Define a remote conversation record, register a specialized `ChatSession` when deterministic behavior is needed, add a friendly launcher description, provide a global voice command only when it is unambiguous, and test prompt, reprompt, completion, and interrupted-session behavior. Avoid requiring an AI model for fixed-content activities.
