"""Create the Faith agent in ElevenLabs from the files in docs/faith/.

    export ELEVENLABS_API_KEY=...        # ElevenLabs → Profile → API keys
    export FAITH_TOOL_URL=https://<your-railway-domain>/tools/fence_estimate
    export FAITH_ASSISTANT_KEY=...       # same value as on the tool server
    python scripts/create_elevenlabs_agent.py            # creates it
    python scripts/create_elevenlabs_agent.py --dry-run  # shows what it would send

Optional: FAITH_VOICE_ID (defaults to the stock "Rachel" voice), FAITH_LLM
(default gemini-2.0-flash).

Steps: store the tool key as an ElevenLabs secret, create the
`fence_estimate` webhook tool, upload the knowledge base, create the agent.
If a step is rejected (ElevenLabs changes its API from time to time), the
script says which one and what to do by hand in the dashboard, following
docs/faith/setup.md.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

API = "https://api.elevenlabs.io"
ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs" / "faith"
DEFAULT_VOICE = "21m00Tcm4TlvDq8ikWAM"  # Rachel, an ElevenLabs stock voice

TOOL_DESCRIPTION = (
    "Runs a fence material takeoff. Returns `spoken` (say this), `materials`, `layout`, "
    "`assumptions` and `questions`. If it returns `needs`, ask that question and call again."
)

BODY_SCHEMA = {
    "type": "object",
    "description": "The job as the contractor described it.",
    "properties": {
        "fence_type": {"type": "string", "description": "wood_privacy or chain_link"},
        "height_ft": {"type": "number", "description": "Fence height in feet"},
        "runs": {"type": "array", "description": "Each straight run, corner to corner, in feet", "items": {"type": "number", "description": "Run length in feet"}},
        "total_feet": {"type": "number", "description": "Total footage, when run lengths aren't known"},
        "corners": {"type": "integer", "description": "Number of corners, with total_feet"},
        "gates": {
            "type": "array",
            "description": "One entry per gate",
            "items": {
                "type": "object",
                "description": "A gate",
                "properties": {
                    "width_ft": {"type": "number", "description": "Gate opening width in feet"},
                    "style": {"type": "string", "description": "single_walk or double_drive"},
                    "automated": {"type": "boolean", "description": "Only if the contractor said whether it's automated"},
                    "run": {"type": "integer", "description": "0-based index of the run the gate is on"},
                    "at_ft": {"type": "number", "description": "Distance from the start of the run to the gate"},
                },
                "required": ["width_ft"],
            },
        },
        "style": {"type": "string", "description": "board_on_board or side_by_side (wood only)"},
        "terrain": {"type": "string", "description": "flat, racked or stepped"},
        "grade_pct": {"type": "number", "description": "Slope in percent, if known"},
        "waste_pct": {"type": "number", "description": "Override the waste percentage"},
        "location": {"type": "string", "description": "City or branch, e.g. OKC"},
    },
    "required": [],
}


def prompt_and_first_message() -> tuple[str, str]:
    text = (DOCS / "agent-prompt.md").read_text()
    parts = text.split("\n---\n")
    if len(parts) < 3:
        raise SystemExit("Couldn't find the prompt between the --- lines in agent-prompt.md.")
    prompt = parts[1].strip()
    first = prompt.split("## First message", 1)[1].strip().strip('"').replace("\n", " ")
    return prompt.split("## First message", 1)[0].strip(), first


def call(method: str, path: str, key: str, body: dict) -> dict:
    req = urllib.request.Request(API + path, json.dumps(body).encode(), {"xi-api-key": key, "content-type": "application/json"}, method=method)
    with urllib.request.urlopen(req, timeout=60) as res:
        return json.loads(res.read() or b"{}")


def step(name: str, fn):
    try:
        out = fn()
        print(f"  ok   {name}")
        return out
    except urllib.error.HTTPError as e:
        print(f"  FAIL {name}: HTTP {e.code} {e.read().decode(errors='replace')[:400]}")
    except urllib.error.URLError as e:
        print(f"  FAIL {name}: {e.reason}")
    return None


def main(argv: list[str]) -> int:
    dry = "--dry-run" in argv
    key = os.environ.get("ELEVENLABS_API_KEY", "")
    tool_url = os.environ.get("FAITH_TOOL_URL", "https://YOUR-DOMAIN/tools/fence_estimate")
    tool_key = os.environ.get("FAITH_ASSISTANT_KEY", "")
    if not dry and not (key and tool_key and "YOUR-DOMAIN" not in tool_url):
        raise SystemExit("Set ELEVENLABS_API_KEY, FAITH_TOOL_URL and FAITH_ASSISTANT_KEY first (or use --dry-run).")

    prompt, first = prompt_and_first_message()

    def tool_config(header_value) -> dict:
        return {
            "type": "webhook",
            "name": "fence_estimate",
            "description": TOOL_DESCRIPTION,
            "response_timeout_secs": 10,
            "api_schema": {
                "url": tool_url,
                "method": "POST",
                "request_headers": {"x-faith-key": header_value},
                "request_body_schema": BODY_SCHEMA,
            },
        }

    agent = {
        "name": "Faith — Master-Halco",
        "conversation_config": {
            "agent": {
                "first_message": first,
                "language": "en",
                "prompt": {"prompt": prompt, "llm": os.environ.get("FAITH_LLM", "gemini-2.0-flash"), "temperature": 0.3},
            },
            "tts": {"voice_id": os.environ.get("FAITH_VOICE_ID", DEFAULT_VOICE)},
        },
    }

    if dry:
        print(json.dumps({"tool": tool_config("<secret>"), "agent": agent}, indent=2)[:4000])
        return 0

    print("Creating Faith in ElevenLabs:")
    secret = step("store tool key as a secret", lambda: call("POST", "/v1/convai/secrets", key, {"type": "new", "name": "faith_assistant_key", "value": tool_key}))
    header = {"secret_id": secret["secret_id"]} if secret and secret.get("secret_id") else tool_key
    if not secret:
        print("       using the key as a plain header instead; swap it for a secret in the dashboard later")

    tool = step("create fence_estimate tool", lambda: call("POST", "/v1/convai/tools", key, {"tool_config": tool_config(header)}))
    if tool and tool.get("id"):
        agent["conversation_config"]["agent"]["prompt"]["tool_ids"] = [tool["id"]]
    else:
        print("       attaching the tool inline instead")
        agent["conversation_config"]["agent"]["prompt"]["tools"] = [tool_config(header)]

    kb = step("upload knowledge base", lambda: call("POST", "/v1/convai/knowledge-base/text", key, {"name": "Faith knowledge base", "text": (DOCS / "knowledge-base.md").read_text()}))
    if kb and kb.get("id"):
        agent["conversation_config"]["agent"]["prompt"]["knowledge_base"] = [{"type": "text", "id": kb["id"], "name": "Faith knowledge base"}]
    else:
        print("       upload docs/faith/knowledge-base.md in the dashboard (Knowledge base → Add)")

    made = step("create agent", lambda: call("POST", "/v1/convai/agents/create", key, agent))
    if not made:
        print("\nThe agent wasn't created. Follow docs/faith/setup.md step 2 in the dashboard instead.")
        return 1
    print(f"\nDone. Agent ID: {made.get('agent_id')}")
    print("Next in the dashboard: add Spanish as a language, add the End call and Language detection system tools, set the allowlist.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
