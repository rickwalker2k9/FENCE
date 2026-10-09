# Master-Halco demo: Faith on a phone

Three texts, under a minute. Every number below is the real tool output
(`python -m faith '{"total_feet":180,"height_ft":6,"style":"board_on_board","gates":[4],"location":"OKC"}'`).

## 1. The prompt
> Hey Faith, I'm at a job site in OKC. Putting up 180 feet of 6ft cedar
> board-on-board privacy fence, mostly flat, but we have one 4-foot wide
> walk gate.

## 2. Faith's answer
> Got it. 180 feet of 6 foot board-on-board with a 4 foot walk gate:
> 22 bays at exactly 8 feet on center, 24 posts, 76 rails, 535 pickets with
> 10% waste, and 48 bags of concrete. I centered the gate; tell me if it's
> by the house.
>
> - 22 × 4x4x8 posts (line and end, 24 in deep)
> - 2 × 4x4x10 gate posts (36 in deep)
> - 76 × 2x4x8 rails (66 + 10% waste, + 3 for the gate frame)
> - 535 × 6 ft cedar pickets (board-on-board, 10% waste)
> - Gate hardware: 2 T-hinges, 1 gravity latch, 1 D-handle, 1 gate spring
> - 48 × 60 lb post-hole concrete (2 per hole)

## 3. The closer
> Have you called OKIE811 yet? It's free and required before you dig.
> Want me to send this list to the OKC counter so they can confirm stock,
> price it and pre-stage it?

## Why these numbers differ from the first draft
The first draft of this script said 23 bays at 7.82 ft, 24 line posts plus
2 gate posts, 69 rails and 486 pickets. Faith corrects three things, and
they're worth pointing out in the meeting because they show she's exact:
- **The gate opening isn't fence.** Take the 4 ft gate out and there are
  176 ft of fence, two 88 ft sides, 22 bays at an even 8.0 ft.
- **Gate posts are part of the 24.** 20 line + 2 end + 2 gate = 24, not 26.
- **The waste was missing.** 180 ft × 2.7 = 486 pickets before waste;
  with 10% it's 535.

## What to keep out of the demo (until it's wired up)
- "This matches inventory at the OKC warehouse." Faith can't see inventory
  yet, and the prompt forbids promising stock. Connecting her to
  Master-Halco's ERP is the pilot's phase 2; pitch it as that.
- Prices. Same reason.

## Pilot phases to pitch
1. **Takeoff assistant (ready now):** wood privacy and chain-link, voice or
   text, English and Spanish.
2. **Catalog codes:** fill in `faith/catalog.json` with Master-Halco item
   codes so every list is ready to key in.
3. **Counter hand-off:** send the list to the OKC counter for pre-staging.
4. **ERP connection:** live stock, pricing, order status, pickup lanes and
   gate hours for the new facility.
