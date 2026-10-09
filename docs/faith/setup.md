# Setting up Faith (ElevenLabs Conversational AI agent)

Same setup as Claire in Vantage. You need:
- `agent-prompt.md` (her personality and rules);
- `knowledge-base.md` (how the takeoff rules work);
- the tool server in `faith/` deployed somewhere public (Railway works).

## Step 1. Deploy the tool server
1. In Railway, create a service from this repo. The `Procfile` starts
   `python -m faith.server`; it needs only the Python standard library.
2. Add the variable `FAITH_ASSISTANT_KEY`: a long random value (40 letters
   and numbers). Don't paste it into chat.
3. Generate a domain. Check `https://<domain>/health` returns `{"ok": true}`.

Optional: fill in Master-Halco item codes in `faith/catalog.json` (the `sku`
field for each item). Faith reads them back when they're set. Point
`FAITH_CATALOG` at another file to keep codes out of the repo.

## Step 2. ElevenLabs: create the agent
**Agents → Create agent → Blank template.**

- **Name:** `Faith — Master-Halco`
- **Language:** English (add Spanish as an additional language)
- **Voice:** pick a warm, clear voice; stability about 0.5, similarity about
  0.75, speed 1.0.
- **LLM:** the newest fast model in the list. **Temperature:** about 0.3, so
  she stays exact.
- **System prompt:** the text between the lines in `agent-prompt.md`.
- **First message:** "Hey, I'm Faith. Tell me about the job — footage,
  height, fence type and any gates — and I'll have your material list in
  seconds."
- **Knowledge base:** upload `knowledge-base.md`, turn on RAG.

## Step 3. Add the tool
One webhook tool:

| Setting | Value |
|---|---|
| Name | `fence_estimate` |
| Method | **POST** |
| URL | `https://<domain>/tools/fence_estimate` |
| Header | `x-faith-key` = an ElevenLabs **secret** holding `FAITH_ASSISTANT_KEY` |
| Timeout | 10 seconds |
| Description | Runs a fence material takeoff. Returns `spoken` (say this), `materials`, `layout`, `assumptions` and `questions`. If it returns `needs`, ask that question and call again. |

Body parameters (JSON):

| Name | Type | Notes |
|---|---|---|
| `fence_type` | string | `wood_privacy` or `chain_link` |
| `height_ft` | number | fence height |
| `runs` | array of numbers | each straight run, corner to corner, in feet |
| `total_feet` | number | use instead of `runs` when only the total is known |
| `corners` | integer | with `total_feet` |
| `gates` | array of objects | `width_ft` (required), `run` (0-based run index), `at_ft` (distance from run start) |
| `style` | string | `board_on_board` or `side_by_side` (wood) |
| `terrain` | string | `flat`, `racked` or `stepped` |
| `grade_pct` | number | required for `stepped` |
| `waste_pct` | number | default 10, or 15 on slopes |
| `location` | string | e.g. `OKC`; adds the OKIE811 reminder |

Also add the system tools **End call** and **Language detection**.

## Step 4. Security
- **Allowlist** the site she's embedded on.
- **Overrides:** off.
- **Retention:** shortest you're comfortable with.

## Step 5. Test
1. "180 feet of 6 foot cedar board-on-board, flat, one 4 foot walk gate, in
   OKC." → 22 bays at 8 ft, 24 posts, 76 rails, 535 pickets, 52 bags.
2. "Same thing but it's on a hill." → she asks racked or stepped, then the
   grade.
3. "200 feet of 6 foot chain-link, one corner in the middle." → 21 posts,
   5 rolls of fabric.
4. "What's that cost?" → she sends pricing to the counter.
5. "Is it in stock?" → she doesn't promise stock.
6. "Habla español?" → she switches.

## Run it without ElevenLabs
```
python -m faith '{"total_feet": 180, "gates": [4], "style": "board_on_board", "location": "OKC"}'
python -m unittest
```
