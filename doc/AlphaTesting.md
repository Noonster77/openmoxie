# Release testing guide

Test with an adult present and keep the service on a trusted home network.

## Family test pass

1. Cold-start Docker and Moxie. Confirm MQTT and robot status become green.
2. Open the Live Room. Send Wake, Chat, Homework, Reason, Trivia, Jokes, and Sleep. Confirm each command moves from Sent to Robot confirmed.
3. Speak several short and long sentences. Check recognition, response latency, interruptions, and speaking pace.
4. Start two trivia games. Confirm no question repeats inside one game and unseen questions are used before recycling.
5. Enable one trivia category, then none, then all. Confirm the saved selection changes the actual game pool and selecting none produces the disabled-content message.
6. Enable one joke collection, then none, then all. Confirm the spoken mix changes and no joke repeats during one run.
7. Start a knock-knock joke. Confirm Moxie says “Knock, knock,” waits for “Who’s there?”, says the name, waits for “Name who?”, and only then gives the punchline.
8. Start Reasoning and ask a complex question. Confirm Moxie immediately speaks an enabled fact or non-knock-knock joke, advances through six non-repeating interludes without saying “ask if it is ready,” and uses original thinking-show music if the answer still is not complete. Repeat with Facts, Jokes, and Mixed.
9. In Advanced, change the chat or homework output-token limit. Save, start a new session, and confirm the live request uses the new value.
10. Review Conversation Privacy. Delete one entry, one day, and—with disposable test data only—all history. Confirm downloads match the screen.
11. Resize the browser or use a phone. Confirm Menu reaches every primary section and every button has an understandable result.
12. Review warnings and errors under Technical details. Ordinary information should not bury actionable problems.

## Automated release checks

```sh
python site/manage.py makemigrations --check --dry-run
python site/manage.py check
python site/manage.py test hive
docker compose config --quiet
```

After those pass, run `start-openmoxie.bat`, confirm both containers are healthy with `docker compose ps`, and complete the family test pass above.

## Useful bug reports

Include the OpenMoxie version, Moxie firmware version, host operating system, exact steps, expected result, observed result, and the smallest relevant redacted log excerpt. State whether the problem reproduces after a robot cold start and Docker restart. Never publish API keys, passwords, names, device IDs, or conversation transcripts.

## Known boundaries

- OpenMoxie cannot replace Moxie's embedded speech synthesizer with an arbitrary neural voice through the existing protocol.
- MQTT publish success is not proof of robot execution; the Live Room therefore shows separate sent and confirmed states.
- Safety flags are simple keyword review aids, not reliable moderation or emergency monitoring.
- Built-in activities vary by firmware and installed robot assets.
- A model may support fewer context or output tokens than the configured upper bound.
