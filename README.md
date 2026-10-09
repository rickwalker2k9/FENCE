# Faith — fencing estimator for Master-Halco contractors

Faith is a voice and text assistant that turns a job description into a
symmetrical post layout and a full bill of materials. She's built like Claire
in Vantage: a clear personality, and every job number comes from a tool, never
from the model's head.

- `faith/estimator.py` — the takeoff engine (wood privacy, chain-link, slopes, gates, concrete).
- `faith/server.py` — the `fence_estimate` webhook tool for the ElevenLabs agent.
- `faith/catalog.json` and `faith/gate_hardware.json` — item codes and gate hardware packages.
- `scripts/create_elevenlabs_agent.py` — creates the ElevenLabs agent in one command.
- `docs/faith/agent-prompt.md` — Faith's system prompt and first message.
- `docs/faith/knowledge-base.md` — the rules behind the math.
- `docs/faith/setup.md` — ElevenLabs and Railway setup, step by step.
- `docs/faith/demo-script.md` — the three-text Master-Halco demo.

```
python -m faith '{"total_feet": 180, "gates": [4], "style": "board_on_board", "location": "OKC"}'
python -m unittest
```

Python 3.10+, standard library only.
