# Family use and release guide

This guide is for the person running Moxie at home. Keep OpenMoxie on a trusted private network and use it with an adult present.

## Starting a normal day

1. Start Docker Desktop and wait until its engine is ready.
2. Run `start-openmoxie.bat`. It starts the base services and the optional Vision service when that extension has been installed.
3. Open Control Center at `http://localhost:8001/hive/dashboard`.
4. Turn on Moxie. Wait for MQTT and the robot card to show green before starting an activity.
5. Press **Chat**, or say “Moxie, talk about something else.” Homework, Reasoning, Trivia, and Jokes are available from the same card.

The Live room shows the current robot mode, recent conversation, and whether a command was only sent or was actually confirmed by Moxie.

## Family setup

- **Family & voice:** add the names Moxie may use, select a nickname, and adjust voice, speaking pace, volume, and screen brightness.
- **Activity rotation:** choose which built-in activities Moxie may offer. Disabling an activity here does not delete its data.
- **Trivia and Jokes:** select the collections your family wants. OpenMoxie avoids repeats within a running game.
- **Conversation privacy:** review, download, or delete local conversation entries. Safety flags are fallible review aids, not emergency monitoring.
- **Setup:** choose the AI and speech providers, manage optional Vision, and maintain bundled database content.

## Useful voice requests

- “Moxie, start homework mode.”
- “Moxie, start reasoning mode.”
- “Moxie, play trivia.”
- “Moxie, tell me some jokes.”
- “Moxie, start vision mode.”
- “Moxie, play I Spy.”
- “Talk about something else.”
- “Go to sleep, please.”

## Optional Vision

Install Vision with `setup-vision.bat`, then add both DNS overrides printed by the installer to the router or DNS service used by Moxie. Setup contains separate controls for turning Vision features on or off and starting, restarting, or stopping the Docker service.

- **Vision** lets the family ask about common objects in the current view.
- **I Spy** asks Moxie to look around. Say “ready” after Moxie stops moving, then ask yes-or-no questions or guess the object.
- **Camera off**, Sleep, starting a non-Vision activity, or turning Vision features off restores the previous camera settings.
- Face recognition is optional biometric processing. Enroll only someone who consents, use several clear samples, and expect occasional “unknown” results or mistakes.

The camera feed is low-resolution and roughly one frame per second. Do not use it for security, safety decisions, or continuous tracking of a person.

## Common problems

### Moxie is offline

Confirm Docker is running and that Moxie and the OpenMoxie computer are on the same home network. If Moxie remains at the OpenMoxie QR screen, run `setup-openmoxie-network.bat` and approve its administrator prompt, then show the Wi-Fi QR followed by the Migration QR. Check the Live room for connection errors.

### LM Studio loaded a model but conversations do not answer

Run `setup-lm-studio-model.bat` again. It starts the LM Studio daemon, binds its API listener to port 1234, verifies `/v1/models`, and checks that the OpenMoxie Docker container can reach it.

### Speech recognition is inaccurate

Reduce background noise and speak one short sentence at a time. In Setup, select a larger faster-whisper model if the computer has enough memory and processing capacity.

### Vision says ready but has no picture

Keep Moxie awake and engaged, leave Puppet mode, verify both DNS overrides, and confirm the detector shows Ready in Setup. Do not redirect `client-service-api.embodied.com`.

### An activity appears stuck

Press **Chat** or **Stop**, wait several seconds, and check Live room. A successful MQTT send does not prove that the robot executed the command.

## Before reporting a problem

Restart Docker and cold-start Moxie once. Record the OpenMoxie version, Moxie firmware, exact steps, expected result, observed result, and the smallest useful redacted log excerpt. Never publish keys, passwords, names, device IDs, face samples, or transcripts.

## Maintainer release check

This shorter technical check is for maintainers preparing a build, not ordinary family use:

```sh
python site/manage.py makemigrations --check --dry-run
python site/manage.py check
python site/manage.py test hive
docker compose config --quiet
docker compose -f docker-compose.yml -f docker-compose.vision.yml config --quiet
```

Afterward, verify one Chat session, one game, Sleep, transcript deletion, and—when installed—Vision, I Spy, Camera off, and wake-from-sleep recovery on real hardware.
