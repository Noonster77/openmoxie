# OpenMoxie setup guide for Windows

This guide starts from a blank Windows PC. You do not need Git or any programming experience.

By the end, OpenMoxie will be running on your computer and Moxie will be connected to it over your home network.

## Before you start

You will need:

- A Windows 10 or 11 computer that can stay on while Moxie is in use.
- Moxie and the computer connected to the same private home network.
- At least 8 GB of RAM for Docker. For local AI, 16 GB of RAM and a graphics card with 4 GB of dedicated memory are recommended.
- About 10 GB of free disk space. Allow more if you plan to try several AI models.
- An Internet connection for the initial downloads.

Do not forward ports `8001` or `8883` through your router. OpenMoxie is meant to stay on your home network.

## 1. Download the OpenMoxie files

1. [Download OpenMoxie as a ZIP file](https://github.com/Noonster77/openmoxie/archive/refs/heads/main.zip).
2. Open your **Downloads** folder and right-click `openmoxie-main.zip`.
3. Select **Extract All** and then **Extract**.
4. Move the extracted `openmoxie-main` folder somewhere you will keep it, such as **Documents**.

Do not run OpenMoxie from inside the ZIP file. The folder must be extracted first.

## 2. Install Docker Desktop

Docker runs the two services OpenMoxie needs. You do not need to know Docker to use them.

1. Open the [official Docker Desktop for Windows installation page](https://docs.docker.com/desktop/setup/install/windows-install/).
2. Download the Windows installer that matches your computer. Most Windows PCs use **x86_64**.
3. Run `Docker Desktop Installer.exe` and follow the prompts. Keep **Use WSL 2** selected if the installer offers it.
4. Restart Windows if asked.
5. Open **Docker Desktop** from the Start menu and accept its terms.
6. Wait until Docker Desktop says the engine is running.

You do not need a paid Docker account for personal use. If Docker reports a WSL or virtualization problem, follow the troubleshooting link shown in Docker Desktop before continuing.

## 3. Start OpenMoxie

1. Open the extracted `openmoxie-main` folder.
2. Double-click [`start-openmoxie.bat`](../start-openmoxie.bat).
3. If Windows SmartScreen appears, select **More info**, check that the file is the one from this repository, and select **Run anyway**.
4. Leave the black command window open while Docker builds OpenMoxie for the first time.

The first start takes the longest because Docker has to download and build everything. When it is ready, your browser should open the OpenMoxie Setup page. If it does not, open [http://localhost:8001/hive](http://localhost:8001/hive) yourself.

OpenMoxie runs two containers named `openmoxie-server` and `openmoxie-mqtt`. Your settings, database, logs, and transcripts are kept in [`local/work`](../local/work/), outside those containers.

## 4. Install LM Studio and a local AI model

OpenMoxie needs an AI provider for open-ended conversations. LM Studio is the easiest way to run one locally without an API bill.

If this computer has less than 16 GB of RAM, the recommended local model may be too large. You can try a smaller model in LM Studio or use one of the cloud options later in this guide.

### Recommended automatic setup

1. [Download and install LM Studio](https://lmstudio.ai/download).
2. Open LM Studio once and finish its first-run setup. This is required before its command-line helper will work.
3. Once the main LM Studio window opens, return to the `openmoxie-main` folder. LM Studio can stay open.
4. Return to the `openmoxie-main` folder and double-click [`setup-lm-studio-model.bat`](../setup-lm-studio-model.bat).
5. If Windows Firewall asks for permission, allow access on **Private networks** only.

The helper downloads the recommended [Qwen3.5 9B Q4_K_S model](https://huggingface.co/Manojb/Qwen3.5-9B-Q4_K_S.gguf), which is about 6.5 GB. It then loads the model, starts LM Studio's local server on port `1234`, and opens OpenMoxie Setup.

When it finishes, the command window should show these values:

| OpenMoxie setting | Value |
|---|---|
| Chat provider | `LM Studio (local)` |
| Model identifier | `qwen_qwen3.5-9b.gguf` |
| API base URL | `http://host.docker.internal:1234/v1` |
| Speech provider | `Local faster-whisper` |

Keep LM Studio running while you use Moxie's AI conversations.

### Manual LM Studio setup

Use this route if the helper does not work or if you want a different model.

1. In LM Studio, search for and download a GGUF chat model that fits your computer.
2. Load the model. Copy its exact model identifier.
3. Open **Developer** in LM Studio and start the local server on port `1234`.
4. Turn on local-network serving if LM Studio asks. Allow **Private networks** in Windows Firewall.
5. Enter the copied identifier in OpenMoxie Setup. Use `http://host.docker.internal:1234/v1` as the API base URL.

LM Studio's [system requirements](https://lmstudio.ai/docs/app/system-requirements) and [local server guide](https://lmstudio.ai/docs/developer/core/server) have more detail if a model will not load or the server will not start.

## 5. Complete OpenMoxie Setup

Open [http://localhost:8001/hive/setup](http://localhost:8001/hive/setup) if the Setup page is not already visible.

### Conversation AI

For the recommended local setup, enter the four LM Studio values from the table above. No API key is needed.

### Speech recognition

Select **Local faster-whisper** and keep `small.en` as the model. The first transcription will be slower because OpenMoxie downloads this speech model once.

### Home network

In **Hostname or LAN IP**, enter the Windows computer's local IPv4 address:

1. Open the Start menu, type `cmd`, and open **Command Prompt**.
2. Run `ipconfig`.
3. Find the active Wi-Fi or Ethernet section.
4. Copy its **IPv4 Address**, which will usually look like `192.168.1.25` or `10.0.0.25`.

Do not enter `localhost` or `127.0.0.1`; those addresses point Moxie back to itself. If your router can reserve an IP address for this computer, doing so will keep the Migration QR valid after a restart.

### Administrator account

On a fresh install, create the administrator username and password shown at the bottom of the page. These are for OpenMoxie's **Advanced** settings. Save the password somewhere private; there is no shared default password.

Select **Save configuration**, then use **Test saved AI**. A successful test should say that LM Studio is reachable and show the configured model identifier.

## 6. Connect Moxie

1. Return to the OpenMoxie Control Center.
2. Open **Migration QR**.
3. Use Moxie's supported migration flow and show the QR code to the robot.
4. Wait for the robot card in the Control Center to say **Online**.

A Wi-Fi check mark only confirms that Moxie joined Wi-Fi. The **MQTT** and **Online** indicators in OpenMoxie confirm that the robot reached this computer.

## 7. Try it

Start with a few quick checks:

1. Select **Wake & Chat** and ask a short question.
2. Select **Homework** and try a simple calculation.
3. Open **Trivia** or **Jokes**. These use built-in content and are useful for checking the robot connection even if the AI model is not working.
4. Open **Live monitor** to watch commands and conversation events.

Reasoning mode may take a few minutes with a local model. Moxie will use facts or jokes while the answer is being prepared.

## Cloud AI options

You can use a cloud provider instead of LM Studio. Cloud services require an Internet connection and may charge for usage.

### OpenAI API

Select **OpenAI API**, enter an OpenAI API model identifier, and paste your API key. Choose either OpenAI Whisper or local faster-whisper for speech recognition. A ChatGPT subscription does not include OpenAI API credit.

### OpenRouter

Select **OpenRouter**, paste an OpenRouter API key, enter the exact model identifier listed by OpenRouter, and use this API base URL:

```text
https://openrouter.ai/api/v1
```

## Everyday start and stop

- To start OpenMoxie, open Docker Desktop and double-click [`start-openmoxie.bat`](../start-openmoxie.bat).
- To open the Control Center, visit [http://localhost:8001/hive](http://localhost:8001/hive).
- To stop OpenMoxie, open PowerShell in the `openmoxie-main` folder and run `docker compose down`.
- To check it, run `docker compose ps`. Both containers should show as running.
- To view recent server errors, run `docker compose logs --tail 100 server`.

## Back up or update a ZIP installation

Everything personal is stored in [`local/work`](../local/work/). It may contain family conversations, device information, and service keys. Never upload or share this folder.

To make a backup:

1. Run `docker compose down` from the current OpenMoxie folder.
2. Copy the entire `local/work` folder to private storage.

To update when you originally installed from a ZIP:

1. Make the backup above.
2. [Download the latest OpenMoxie ZIP](https://github.com/Noonster77/openmoxie/archive/refs/heads/main.zip) and extract it into a new folder.
3. Copy your old `local/work` folder into the new OpenMoxie folder, replacing the new empty `local/work` folder.
4. Double-click the new [`start-openmoxie.bat`](../start-openmoxie.bat).
5. Keep the old OpenMoxie folder until you have confirmed that the update works and your Moxie data is present.

## Troubleshooting

### `Docker was not found` or `Docker Desktop is not ready`

Open Docker Desktop and wait until its engine is running, then double-click `start-openmoxie.bat` again.

### The Control Center will not open

Run `docker compose ps` in the OpenMoxie folder. Both `openmoxie-server` and `openmoxie-mqtt` should be running. Then run `docker compose logs --tail 100 server` and look for the first error.

### Trivia works, but chat does not

Open **Setup** and select **Test saved AI**. Check that the model identifier exactly matches the loaded model in LM Studio.

### OpenMoxie cannot reach LM Studio

Confirm that the model is loaded, the LM Studio server is running on port `1234`, and Windows Firewall allows it on Private networks. The OpenMoxie API base URL must be `http://host.docker.internal:1234/v1`, not `localhost`.

### Moxie stays offline

Confirm that Moxie and the computer are on the same home network. Recheck the IPv4 address saved in Setup, create a new Migration QR, and repeat the migration step.

### You forgot the administrator password

Open PowerShell in the OpenMoxie folder and run the following command. Replace `admin` if you chose a different username.

```powershell
docker compose exec server python3 site/manage.py changepassword admin
```

For a bug report, include the OpenMoxie version, Windows version, Moxie firmware, the steps that failed, and a short redacted error message. Remove API keys, passwords, names, device IDs, logs, and transcripts before posting anything publicly.

For more technical information, see the [full installation guide](Installation.md) and the project [README](../README.md).
