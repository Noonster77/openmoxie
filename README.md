# OpenMoxie Family Edition

<p align="center"><img src="./site/static/hive/openmoxie_logo.svg" width="160" height="160" alt="OpenMoxie logo"></p>

OpenMoxie is a local home server that reconnects an Embodied Moxie robot to useful conversation, activities, and family controls. It runs on a computer on the same trusted network as the robot and is managed through a browser—no replacement parent app is required.

This repository is a community fork of [Justin Beghtol’s original OpenMoxie project](https://github.com/jbeghtol/openmoxie). The upstream project established the local MQTT, robot protocol, Django, schedule, and remote-conversation foundation. This fork keeps that work and its MIT license while focusing on an easier family experience and broader AI support. It is not an official Embodied product.

## What changed in this fork

- A cohesive Control Center, mobile navigation, Parent Corner, Live Room, command acknowledgements, recovery controls, and clearer setup diagnostics.
- OpenAI, OpenRouter, LM Studio, local faster-whisper, and arbitrary OpenAI-compatible chat servers. LM Studio accepts the exact identifier of any model it can load.
- Configurable conversation models, prompts, history, temperature, and output-token budgets in **Advanced → Single prompt chats**.
- A button- and voice-activated reasoning mode for complex questions. Long inference runs in the background while Moxie rotates through at least six enabled facts or jokes, then adds playful original thinking-show music if more time is needed.
- Fast homework help, conversation memory and local transcripts, family speaker profiles, privacy deletion, and conservative parent-review flags.
- Editable, selectable joke and trivia collections. Knock-knock jokes now pause for “Who’s there?” and “Name who?” before delivering the punchline.
- More than 100 family jokes and an expanded no-repeat trivia library with 100 additional reviewed questions in each of six categories.

## Easiest install

You need:

- A Windows, macOS, or Linux computer that can remain on while Moxie is used.
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) or Docker Engine with Compose.
- Moxie and the computer on the same private home network.
- Either a cloud AI key, or LM Studio plus a local model. Fixed trivia and jokes need no AI API.

### Windows

1. Download this repository with **Code → Download ZIP**, then extract it. Git is optional.
2. Install and start Docker Desktop.
3. Double-click `start-openmoxie.bat`.
4. Wait for the browser to open `http://localhost:8001/hive`.
5. Complete Setup, save, and use **Test saved AI**.
6. Open **Migration QR** in the Control Center and show it to Moxie.

For the recommended local model, double-click `setup-lm-studio-model.bat` first. It downloads and loads Qwen3.5 9B Q4_K_S through LM Studio, starts port 1234, and prints the exact Setup values.

### macOS or Linux

```sh
git clone https://github.com/Noonster77/openmoxie.git
cd openmoxie
docker compose up --build -d --remove-orphans
```

Then visit `http://localhost:8001/hive`, complete Setup, and scan the Migration QR.

Your database, logs, local speech models, and transcripts live in `local/work`. Back up that directory before upgrades. Never publish it.

For screenshots-in-words, terminology, and first-day checks, follow the [Newbie guide](doc/NewbieGuide.md). The fuller [Installation guide](doc/Installation.md) covers providers, upgrades, and troubleshooting.

## AI providers

| Provider | Setup model value | API base | Notes |
|---|---|---|---|
| LM Studio | Exact loaded model identifier | `http://host.docker.internal:1234/v1` | Local; supports any model LM Studio can serve |
| OpenRouter | Exact model ID, for example `openai/gpt-5` | `https://openrouter.ai/api/v1` | Requires an OpenRouter key |
| OpenAI | OpenAI model ID | Managed automatically | Requires an OpenAI API key |
| Compatible | Server-specific model ID | Your server’s `/v1` URL | Works with compatible Ollama, vLLM, LocalAI, and similar servers |

### Model suggestions

- **Current/recommended default: Qwen3.5 9B Q4_K_S.** Your existing local configuration uses `qwen_qwen3.5-9b.gguf`. It is the best starting balance here: roughly a 6.5 GB download, responsive enough for ordinary chat, and capable enough for the optional reasoning mode. Start with a 32,768-token loaded context, 120 chat output tokens, 224 homework output tokens, and 1,200 reasoning output tokens.
- **Faster/lower-memory:** use a smaller Qwen3.5 quant/model when 9B is slow or does not fit. Keep reasoning effort off if that build does not expose reasoning controls.
- **More deliberate but heavier:** `openai/gpt-oss-20b` can be a separate reasoning override if the computer can load it comfortably. Use LM Studio’s resource estimate before switching; a larger model is usually slower and is not necessary for trivia or jokes.

The model runner’s context length and OpenMoxie’s output-token limit are different settings. A large context lets the model read more history; the output limit caps how much it may generate for one spoken reply.

Chat, homework, and reasoning can use different output budgets. Open **Advanced → Single prompt chats** to adjust conversation and homework limits. Open a robot’s **Family & voice** settings to choose the reasoning model override, 128–8192 token budget, effort, and waiting interludes.

### Administrator access and token controls

Open `http://localhost:8001/admin/`, or select **Advanced** in the navigation bar. Sign in with username `admin` and password `Trustno1`. In **Single prompt chats**, edit these rows:

- **OpenMoxie Chat - Long/Short** for ordinary conversation output and history limits.
- **OpenMoxie Homework Help** for homework output and history limits.
- **OpenMoxie Reasoning Mode** for the default reasoning output and history limits.

Save the row; the running conversation service reloads the saved backend values. A robot’s **Family & voice** page can override the reasoning model and output-token limit for that robot. Avoid editing `local/work/db.sqlite3` directly.

To reset an existing administrator named `admin`:

```powershell
docker compose exec server python3 site/manage.py changepassword admin
```

To create another administrator, choose your own username and email, then set its password:

```powershell
docker compose exec server python3 site/manage.py createsuperuser --username YOUR_NAME --email YOUR_EMAIL
```

## Everyday use

The Control Center can start Chat, Homework, Reasoning, Trivia, Jokes, and Sleep. Common voice requests include:

- “Moxie, start reasoning mode.”
- “Moxie, start homework mode.”
- “Moxie, play trivia.”
- “Moxie, tell me some jokes.”
- “Talk about something else.”
- “Go to sleep, please.”

Reasoning answers may take two or three minutes on a large local model. Moxie returns immediately with a fact or joke and advances to a fresh waiting interlude on each follow-up until the completed answer is available.

## Safety and privacy

Keep ports `8001` and `8883` private. Do not port-forward them or expose this development server to the Internet. MQTT intentionally accepts Moxie on the local network, stored service keys are not encrypted, and keyword safety flags can miss context or produce false alarms. This project does not replace adult supervision.

Before sharing a bug report, remove API keys, passwords, device IDs, names, logs, and transcripts. This is the only repository content intended to be public; runtime data in `local/work` must remain private.

## Test and develop

```sh
python -m pip install -r requirements.txt
python site/manage.py makemigrations --check --dry-run
python site/manage.py check
python site/manage.py test hive
```

See [Contributing](doc/Contributing.md), [Alpha testing](doc/AlphaTesting.md), [Moxie overview](doc/MoxieOverview.md), and the [remote module API](doc/RemoteModuleAPI.md).

## License

OpenMoxie is open source under the [MIT License](LICENSE). You may use, copy, modify, and share it under those terms. Upstream copyright and license notices are preserved.
