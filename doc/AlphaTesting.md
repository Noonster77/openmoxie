# Alpha testing guide

Thank you for helping turn OpenMoxie into a dependable community project. Test with an adult present and keep the service on a trusted home network.

## Family test pass

1. Cold-start Docker and Moxie. Confirm MQTT and robot status become green.
2. Open the Live Room. Send Wake, Chat, Stop, Trivia, Jokes, and Sleep. Note whether each moves from Sent to Robot confirmed.
3. Speak several short and long sentences. Check recognition, response latency, interruptions, and the selected speaking pace.
4. Start two trivia games. Confirm a question never repeats inside one game and that the deck uses unseen questions before recycling.
5. Choose one joke collection, test it, then choose all collections. Confirm the spoken mix changes and no joke repeats during one run.
6. Review Conversation Privacy. Delete one entry, one day, and—only with disposable test data—all history. Confirm downloads match the screen.
7. Resize the browser or use a phone. Confirm every visible button has an understandable result.
8. Review warnings and errors under Technical details. Ordinary information should not bury actionable problems.

## Useful bug reports

Include the OpenMoxie version, Moxie firmware version, host operating system, exact steps, expected result, observed result, and the smallest relevant redacted log excerpt. State whether the problem reproduces after a robot cold start and a Docker restart. Never publish API keys, passwords, child names, device IDs, or conversation transcripts.

## Known boundaries

- OpenMoxie cannot replace Moxie's embedded speech synthesizer with an arbitrary neural voice through the existing protocol.
- MQTT publish success is not proof of robot execution, which is why the Live Room shows separate sent and confirmed states.
- Safety flags are simple keyword review aids, not reliable moderation or emergency monitoring.
- Built-in activities vary by firmware and installed robot assets.
