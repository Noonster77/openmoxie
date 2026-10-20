# Credits and third-party notices

OpenMoxie Family Edition stands on work from several community maintainers:

- **Justin Beghtol / jbeghtol** created the original [OpenMoxie](https://github.com/jbeghtol/openmoxie) server and its local MQTT, robot protocol, Django, schedule, content, and remote-module foundation. This repository remains a fork of that project.
- **AppleMelonOrange** published [SideCar for OpenMoxie](https://github.com/AppleMelonOrange/sidecar-for-openmoxie), including the vision-gate research, configuration fields, protobuf field mapping, caption endpoint findings, wake re-arm behavior, and flood-safety lessons adapted by this extension.
- **Noonster77** maintains this family-oriented fork and its additional setup automation, provider support, parent controls, local speech, reasoning/homework modes, family content, privacy tools, local object detector, Vision and I Spy activities, face-recognition beta, and Docker UI integration.

## SideCar for OpenMoxie license notice

MIT License

Copyright (c) 2026 AppleMelonOrange

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

The repository root [MIT License](../LICENSE), including Justin Beghtol's 2025 copyright notice, continues to govern OpenMoxie itself.

## Vision runtime dependencies

The optional image intentionally installs third-party packages and a detector model that retain their own terms:

- [Ultralytics](https://github.com/ultralytics/ultralytics) code and the default YOLO model are offered under AGPL-3.0 unless the installer has a separate Ultralytics enterprise license. Network use and redistribution can create source-availability obligations; review those terms before distributing or operating this extension outside personal experimentation.
- [OpenCV](https://github.com/opencv/opencv) is Apache-2.0, [Pillow](https://github.com/python-pillow/Pillow) uses the HPND license, and [cryptography](https://github.com/pyca/cryptography) is dual Apache-2.0/BSD licensed.

Pinned package versions are listed in [`vision_service/requirements.txt`](../vision_service/requirements.txt). Consult each installed distribution and model artifact for the controlling notice; this file is attribution, not legal advice.
