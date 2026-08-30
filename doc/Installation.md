# OpenMoxie installation

## Before you begin

You need a computer that can stay on while Moxie is in use, Docker Desktop or Docker Engine with Compose, and a trusted home network. Do not expose ports 8001 or 8883 to the public Internet. Moxie and the OpenMoxie computer should be on the same LAN.

For conversation AI, choose OpenAI, OpenRouter, LM Studio, or another OpenAI-compatible service. Speech recognition can use OpenAI Whisper or local faster-whisper. Moxie's spoken output still uses the speech engine installed in the robot. First-time users should begin with the [Newbie guide](NewbieGuide.md).

## Install with Docker

1. Clone or download this repository.
2. Open a terminal in the repository directory.
3. On Windows, double-click `start-openmoxie.bat`. On other systems, run `docker compose up --build -d --remove-orphans`.
4. Open `http://localhost:8001/hive`.
5. Complete Setup. Use your computer's stable LAN IP if Moxie cannot resolve its hostname.
6. Open Migration QR in the Control Center and show it to Moxie.
7. Wait for the robot card to report Online before sending an activity.

Persistent state is stored in `local/work`, including the SQLite database, logs, downloaded local speech models, and transcript text files. Back up this directory before upgrading.

After the first setup, the two OpenMoxie containers restart automatically whenever Docker Desktop starts. They are the only required containers: `openmoxie-mqtt` and `openmoxie-server`.

## Local AI

1. Install LM Studio and load a chat GGUF.
2. Start its local server on port 1234 and allow LAN access when prompted.
3. In OpenMoxie Setup, choose LM Studio and enter the exact model identifier.
4. Use `http://host.docker.internal:1234/v1` from Docker Desktop.
5. Choose local faster-whisper. `small.en` is the recommended balance.
6. Save and use Test selected AI.

Any model LM Studio can expose through its chat API is supported. Copy its exact identifier; OpenMoxie does not maintain a model allowlist. If the model does not implement reasoning controls, choose **Off / compatibility** for reasoning effort.

## OpenRouter and other compatible providers

For OpenRouter, select it directly, enter an OpenRouter key and exact model ID, and use `https://openrouter.ai/api/v1`. For Ollama, vLLM, LocalAI, or another compatible server, select **Other OpenAI-compatible server** and enter that server's reachable `/v1` base URL. A service running on the Docker host usually needs `host.docker.internal` instead of `localhost`.

Conversation and homework token budgets are editable in **Advanced → Single prompt chats**. Reasoning model, effort, output tokens, and waiting content are editable per robot under **Family & voice**.

## Upgrade

1. Back up `local/work`.
2. Pull the new code or images.
3. Run `docker compose up --build -d` for a source checkout, or `docker compose pull` followed by `docker compose up -d` for published images.
4. Django applies database migrations at server startup.
5. Open the Alpha Guide and repeat the short test checklist.

## Troubleshooting

- “Command sent” means MQTT accepted the publish. “Robot confirmed” means a later robot state matched the command.
- If Moxie remains asleep while connected, inspect the live technical details for Wi-Fi app restarts or disconnects, then cold-start the robot.
- If chat fails but trivia works, test the selected AI provider. Trivia and family jokes do not require an AI API.
- If local speech is slow on the first request, allow the faster-whisper model download to finish.
- Download logs only after removing keys, device identifiers, and family conversation text.
