# Faith knowledge base

Upload this file to the agent's knowledge base. It explains the rules behind
Faith's takeoffs so she can explain them. She still never computes job
quantities herself: every number comes from the `fence_estimate` tool, which
uses exactly these rules (`faith/estimator.py`).

## What Faith is
Faith is the estimator and counter companion for Master-Halco contractor
accounts. A contractor describes a job by voice or text; Faith returns a
symmetrical post layout and a full bill of materials, then hands it to the
counter for stock and pricing. She doesn't see pricing, inventory or order
status yet.

## 1. Post spacing and symmetrical layout
- Maximum spacing: 8 ft on center for wood privacy, 10 ft for chain-link.
- Each straight run is split at its gates into fenced segments.
- For each segment: bays = segment length ÷ max spacing, rounded **up**.
  On-center spacing = segment length ÷ bays. Every bay comes out equal, so
  there's never a short leftover bay.
- Posts: each segment has bays + 1 posts. Adjacent runs share the corner
  post. Every gate adds 2 gate posts (1 if it sits flush against a run end
  that already has a post).
- If the gate's position isn't given, Faith centers it so both sides come
  out even, and says so.
- Example: 180 ft with no gate → 23 bays at 7.83 ft, 24 posts.
- Example: 180 ft with a 4 ft gate → 176 ft of fence, two 88 ft sides,
  22 bays at 8 ft, 24 posts (20 line, 2 end, 2 gate).

## 2. Wood privacy takeoff
- Pickets: nominal 6 in (actual 5.5 in).
  - Side-by-side: 2.17 per linear foot (12 ÷ 5.5 in).
  - Board-on-board / shadowbox: 2.7 per linear foot (two layers with about
    1 in overlap).
  - Gates are clad in the same pickets, so gate width counts toward pickets.
- Rails (2x4x8): 2 per bay at 4–5 ft, 3 per bay at 6–7 ft, 4 per bay at 8 ft.
- Gate frame: 3 extra 2x4x8 per walk gate, 6 per double gate.
- Gate hardware: see section 3b.
- Waste: 10% on pickets and rails (15% on slopes). Posts are exact.
- Posts: 4x4, set 24 in deep (36 in for gate posts). Length = fence height +
  depth (+ step drop on a stepped fence), rounded up to stock 8, 10, 12, 14
  or 16 ft. A 6 ft fence uses 8 ft line posts and 10 ft gate posts.
- Gates wider than 6 ft default to a double drive gate. For any gate over
  4 ft, suggest 4x6 or 6x6 gate posts.

## 3. Chain-link takeoff
- Line posts: 1-7/8 in OD, set 24 in deep.
- Terminal posts (end, corner, gate): 2-3/8 in OD, set 36 in deep. They carry
  the fabric tension, so they go deeper (30–36 in is the trade range).
- Per fabric end (1 at each end and gate post, 2 at each corner): 1 tension
  bar, 1 brace band, 1 rail end cup, and tension bands = height in feet − 1
  (5 bands on a 6 ft fence).
- Caps: dome cap on every terminal, loop cap on every line post.
- Fabric: 50 ft rolls, fence footage + waste.
- Top rail: 21 ft swaged sticks, counted per segment.
- Ties: one every 12 in on line posts and every 24 in on top rail.
- Bottom tension wire is optional and left off unless asked.

## 3b. Gate hardware packages
Every gate expands into a full package (`faith/gate_hardware.json`). Item
codes are placeholders until mapped to Master-Halco item numbers.
- **Wood single walk:** 2 × 8 in heavy-duty T-hinge, 1 self-locking gravity
  latch, 1 × 6 in D-handle, 1 × 11 in gate spring.
- **Wood double drive:** 4 × T-hinge, 1 gravity latch, 1 cane bolt / drop
  rod, 1 D-handle.
- **Chain-link single walk:** 2 × industrial female/male strap hinge, 1
  industrial drop-fork latch.
- **Chain-link double drive:** 4 × heavy-duty commercial box hinge, 1
  StrongArm double-gate latch, 1 × 36 in industrial drop rod, 1 ground
  center stop.
- For double drive gates Faith always asks: automated or manual? Do you
  want the drop rod, center stop and heavy-duty latch? Automated operators
  and access control are specced by the counter.

## 4. Concrete
- 10 in diameter holes, 2 bags (60 lb) per post hole.
- Deep 36 in terminal and gate holes can take closer to 3 bags; the counter
  can bump those if the crew wants a margin.

## 5. Slopes and terrain
Faith asks: "Is the ground flat, or are we dealing with a slope?"
- **Flat:** standard math.
- **Racked:** the fence follows the ground. Material counts stay the same;
  measure footage along the slope. Good for mild, even slopes.
- **Stepped:** each bay stays level and drops like a stair. Every post gets
  at least 2 ft longer; on very steep ground (drop per bay over 2 ft) it gets
  the full drop. Waste goes to 15%. Expect triangular gaps under the low end
  of each bay.
- Grade from a contractor: inches of drop per 10 ft ÷ 120 × 100 = grade %.
  (12 in drop over 10 ft = 10%.)

## 6. Before digging in Oklahoma
- Call OKIE811 (811) at least 48 hours before digging, excluding weekends
  and holidays. It's free.
- Check city fence-height rules and HOA covenants. Pool barriers have their
  own code.

## 7. What Faith doesn't do (yet)
- No pricing, stock levels, order status, delivery times or warehouse hours.
  Those come from the Master-Halco counter until Faith is connected to the
  ERP.
- No vinyl, ornamental or wire/farm takeoffs yet.
- No engineering or code sign-off.
