# Optional local vision extension

OpenMoxie Vision enables the camera pathway already present in Moxie firmware 24.10.803, redirects its small caption images to a local HTTPS service, detects objects locally, and adds two remote activities: **Vision** and **I Spy With My Little Eye**. It also includes an explicitly enrolled face-recognition beta.

Vision is off by default. A parent must install the overlay, enable the option in Setup, and start Vision or I Spy for a robot. Sleep, Camera off, starting any ordinary activity, disabling the extension, or stopping the Vision service restores the robot's previous camera-related settings.

## What the system can and cannot do

- Moxie sends approximately one 320x180 JPEG per second while awake, engaged, and in buddy mode.
- The local YOLO model can identify common objects, approximate count and position, and supply candidates for I Spy.
- Approximate object colors come from the detected crop and can be wrong under mixed lighting.
- The feed is not normal video. It is too slow and too small for smooth host-side face or object tracking, reading small text, security monitoring, or safety decisions.
- Moxie's native face-search behavior provides physical attention. The server can conservatively associate one clearly recognized enrolled face with an allowed speaker name, but it refuses ambiguous identity.
- Face recognition identifies a consenting enrolled person; it does not determine which of several people produced an audio signal. Moxie can turn toward the single recognized speaker during a Vision activity, but this is not continuous multi-person speaker tracking.
- Captioning does not operate in Puppet/teacher mode.
- Only one Moxie can own local Vision at a time. Starting it on a second robot automatically closes and restores the first robot's camera settings so frames cannot be attributed to the wrong device.

## Windows installation

1. Start Docker Desktop.
2. Double-click [`setup-vision.bat`](../setup-vision.bat). It launches the guided [`setup-vision-router-dns.bat`](../setup-vision-router-dns.bat) after the containers are ready.
3. Sign in to the router page opened by the helper. The helper detects and copies the current LAN IP and records, then verifies the router's answers after you save them.
4. In the router's Local DNS, DNS Rules, DNS Proxy, Host Mapping, or Address Records area, add:

   ```text
   production-ic-worker.embodied.com -> OPENMOXIE_PC_IP
   staging-ic-worker.embodied.com    -> OPENMOXIE_PC_IP
   ```

5. Do not add `client-service-api.embodied.com`; this extension does not implement that unrelated vendor API.
6. Restart Moxie's network connection if it cached the old DNS answer.
7. Open the Control Center. The Vision status should become Ready. Start **Vision** or **I Spy**.

A Windows hosts-file entry affects only Windows, not the robot. The Migration QR format has Wi-Fi credentials and OpenMoxie endpoint data but no DNS-server or hostname-override field. The override must therefore be supplied by Moxie's DNS resolver. Reserve the OpenMoxie computer's LAN address in the router so the redirect remains valid. If the router uses its own DNS proxy for local records, configure DHCP to give clients the router's LAN address as DNS and do not leave a public resolver as a bypassing DHCP fallback. Do not change WAN DNS.

On macOS or Linux, build the same overlay manually:

```sh
docker compose -f docker-compose.yml -f docker-compose.vision.yml up -d --build
docker compose -f docker-compose.yml -f docker-compose.vision.yml exec server \
  python site/manage.py shell -c "from hive.models import HiveConfiguration; c,_=HiveConfiguration.objects.get_or_create(name='default'); c.vision_extension_enabled=True; c.save()"
```

## Everyday controls

- **Start Vision / Restart / Stop service** controls the named `openmoxie-vision` Docker container.
- **Vision** opens the camera gate and starts object questions.
- **I Spy** opens the gate, runs Moxie's bundled 360-degree look-around behavior, then picks a detected non-person object after the user says “ready.” Ask yes/no questions or guess it.
- **Camera off** immediately restores the values that existed before Vision started.
- Voice starts are available after parent setup: “Moxie, start vision mode” and “Moxie, play I Spy.”

The optional compose overlay mounts Docker's Unix socket into the OpenMoxie server so the UI can start, stop, or restart only the named Vision container. Access to a Docker socket is security-sensitive even though the application restricts its own calls. Install this only on a trusted home computer and do not expose the Django UI to the Internet.

## Local data and face recognition

By default, every incoming image atomically replaces `local/work/vision/latest.jpg`; frames are not archived. The latest detections are in `latest.json`. Set `OPENMOXIE_VISION_ARCHIVE_FRAMES=1` only if you intentionally want an accumulating frame history.

Face recognition is a beta based on local OpenCV LBPH matching:

1. Add the consenting person's name under the robot's **Family & voice** speaker list.
2. Start Vision and place exactly that one face clearly in view.
3. In **Face recognition beta**, enter the same name and save a sample.
4. Repeat about five times, turning slightly between fresh frames.
5. Delete removes that person's samples immediately.

Samples live in `local/work/vision/faces`. They are biometric data: keep them private, include them in deletion requests, and never enroll someone without consent. A match is accepted only below a conservative LBPH distance threshold, only one known face may establish the active speaker, and its name must also be in that robot's configured speaker list.

## Privacy and network behavior

The firmware gate requires `data_sharing=full` and `gcp_upload_disable=0` while Vision is active. Those names come from the discontinued cloud firmware and may also wake dormant upload machinery. OpenMoxie restores all prior values afterward. Keep the robot and host on a private network, do not port-forward 443, 8001, or 8883, and use DNS/firewall policy to prevent unintended vendor egress.

The HTTPS receiver uses a local self-signed certificate because the robot's caption client does not verify the server certificate. Port 443 is exposed only so the robot can upload captions on the LAN. The latest frame, detections, enrolled names, and face-management API are available only on the internal Docker network and are proxied into the existing OpenMoxie UI. The base UI itself is designed for a trusted private network, not Internet exposure.

## Troubleshooting

- **Port 443 already used:** stop the other local HTTPS server, then rerun setup.
- **Ready but zero frames:** run `setup-vision-router-dns.bat`, check that both answers equal the OpenMoxie PC's LAN IP, confirm Moxie is awake and engaged, and leave Puppet mode.
- **Frames but no objects:** move a common object closer, improve lighting, and hold still. The first inference waits for the detector model to finish downloading.
- **Camera blind after sleep:** start Vision again. Wake events are re-armed, but Sleep intentionally closes the privacy gate.
- **Camera stalls while Moxie remains awake:** the server may attempt at most two recovery arms for that stall. The counter resets only after fresh frames actually resume; it never sends a periodic arm heartbeat.
- **Face enrollment says exactly one face:** wait for a fresh well-lit frame containing one front-facing person.
- **Wrong or unknown face:** delete weak samples and capture five closer, varied samples. Do not lower the confidence threshold for convenience.
- **UI cannot control Docker:** rerun `setup-vision.bat`; starting only the base compose file does not mount the opt-in Docker control socket.

Logs:

```powershell
docker compose -f docker-compose.yml -f docker-compose.vision.yml logs --tail 100 vision
```

## Technical provenance

The backend flags, MQTT/ZMQ gate messages, hardcoded caption hostname, multipart JPEG extraction advice, wake re-arm behavior, and flood-safety constraints are adapted from [AppleMelonOrange/sidecar-for-openmoxie](https://github.com/AppleMelonOrange/sidecar-for-openmoxie). The detector service, privacy backup/restore, Docker controls, conversations, I Spy game, local face enrollment, UI, and Windows automation are further work in the Noonster77 family fork. See [Third-party notices](ThirdPartyNotices.md).
