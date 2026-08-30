# OpenMoxie newbie guide

This guide assumes you have never used Git, Docker, a local AI model, or a network QR code.

## What you are installing

OpenMoxie runs two small services inside Docker:

- `openmoxie-server` provides the web Control Center and conversation logic.
- `openmoxie-mqtt` carries messages between that server and Moxie.

Docker keeps the software and its dependencies together. Your personal data stays outside the containers in the `local/work` folder, so rebuilding a container does not erase the database.

## First-time Windows setup

1. Install Docker Desktop and restart Windows if its installer requests it.
2. Start Docker Desktop. Wait until it reports that the engine is running.
3. Download this repository as a ZIP and extract the whole folder. Do not run files from inside the ZIP preview.
4. Double-click `start-openmoxie.bat`. Keep the window open if it reports an error.
5. The script starts both containers and opens the Control Center. If the browser does not open, visit `http://localhost:8001/hive` yourself.

The first build or pull is the slowest. Docker may download several large files.

## Choose your AI

### Simplest cloud setup: OpenAI

Choose **OpenAI API**, enter a supported model ID and API key, then choose OpenAI or local speech recognition. A ChatGPT subscription does not automatically include API credit.

### Broad cloud choice: OpenRouter

Choose **OpenRouter**, paste an OpenRouter API key, and copy an exact model ID from OpenRouter. Keep the supplied API base URL.

### Free local setup: LM Studio

1. Install LM Studio.
2. Download and load a model that fits your computer’s memory.
3. Open LM Studio’s Developer area and start its server on port `1234`.
4. Allow network access if prompted.
5. In OpenMoxie choose **LM Studio (local)**, paste the exact loaded model identifier, and keep `http://host.docker.internal:1234/v1`.
6. Choose **Local faster-whisper** for speech if you want conversations to stay local.

On Windows, `setup-lm-studio-model.bat` automates steps 2–4 for the recommended Qwen3.5 9B Q4_K_S model. It uses LM Studio’s own `lms` tool, assigns the stable API identifier `qwen_qwen3.5-9b.gguf`, loads a 32,768-token context, starts port 1234, and opens OpenMoxie Setup. Run LM Studio once before using the helper.

OpenMoxie does not restrict the LM Studio model family. If LM Studio can serve the model through its API, OpenMoxie can request it. Small models answer faster; reasoning models and large token limits can take minutes.

## Connect Moxie

1. In Setup, enter the computer’s stable local IP address or a hostname Moxie can resolve.
2. Save Setup.
3. Return Home and open **Migration QR**.
4. Show the QR code to Moxie using the robot’s supported migration flow.
5. Wait for the robot card to say **Online**.

A Wi-Fi check mark alone does not prove Moxie reached OpenMoxie. The Control Center’s MQTT and robot indicators are the useful checks.

## Try the main features

1. Select **Wake & Chat**, then ask a short question.
2. Select **Homework** and try a basic calculation.
3. Select **Reason** and ask a complex question. Moxie will rotate through at least six enabled facts or jokes while the answer runs in the background, without repeatedly asking you to check whether it is ready.
4. Open **Trivia** and **Jokes** settings to enable or disable whole categories.
5. Try a knock-knock joke. Wait for all three turns: “Knock knock,” “Who’s there?”, then “Name who?”
6. Open **Live monitor** to see commands and conversation events.

## Change token limits

Choose **Advanced** in the top navigation, or open `http://localhost:8001/admin/`. Sign in with username `admin` and password `Trustno1`.

Open **Single prompt chats**, select the relevant row, change **Max tokens** or **Max history**, and select **Save**:

- **OpenMoxie Chat - Long** and **OpenMoxie Chat - Short** control normal conversations.
- **OpenMoxie Homework Help** controls homework mode.
- **OpenMoxie Reasoning Mode** controls the reasoning default.

The saved values reload into the running backend. For one robot, open **Family & voice** to override its reasoning model, token budget, effort, and waiting interlude type. Use Django Admin rather than opening `local/work/db.sqlite3` in a database editor.

Higher limits allow longer answers but use more time, memory, and cloud credit. Start with the included defaults. A setting does not guarantee every model can use that entire context or output size.

### Create or reset an administrator

To reset the original `admin` account, open PowerShell in the OpenMoxie folder and run:

```powershell
docker compose exec server python3 site/manage.py changepassword admin
```

To create another administrator, substitute your own username and email. Django will ask for the password without displaying it:

```powershell
docker compose exec server python3 site/manage.py createsuperuser --username YOUR_NAME --email YOUR_EMAIL
```

After changing the administrator password, keep the replacement private.

## Stop, restart, back up, or upgrade

- Stop: `docker compose down`
- Start again: double-click `start-openmoxie.bat` or run `docker compose up -d`
- View status: `docker compose ps`
- View logs: `docker compose logs --tail 100 server`
- Back up: stop OpenMoxie, then copy `local/work` to private storage.
- Upgrade a source checkout: back up, pull changes, then run `docker compose up --build -d --remove-orphans`.

Never upload `local/work`; it may contain family conversations and service information.

## If something does not work

- Docker not found: install or start Docker Desktop, then rerun the BAT file.
- Page unavailable: run `docker compose ps`; both services should be running.
- Trivia works but chat does not: use **Test saved AI** and check the exact model ID.
- LM Studio unreachable: confirm its server is running, network access is allowed, and the Docker base URL uses `host.docker.internal`.
- Moxie is offline: confirm both devices are on the same LAN, then repeat the Wi-Fi/Migration QR steps.
- First local transcription is slow: faster-whisper is probably downloading its model once.

For a useful bug report, include the OpenMoxie version, operating system, Moxie firmware, exact steps, and a short redacted error. Never include keys, passwords, names, device IDs, or transcripts.
