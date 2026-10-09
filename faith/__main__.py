"""Run a takeoff from the command line.

    python -m faith '{"total_feet": 180, "style": "board_on_board", "gates": [4], "location": "OKC"}'
    python -m faith --json job.json
"""

from __future__ import annotations

import json
import sys

from faith.estimator import EstimateError, estimate


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 2
    raw = open(argv[1]).read() if argv[0] == "--json" else argv[0]
    try:
        r = estimate(json.loads(raw))
    except EstimateError as e:
        print(f"Faith: {e}")
        return 1
    print(f"Faith: {r['spoken']}\n")
    lay = r["layout"]
    print(f"Layout: {lay['fence_ft']:g} ft of fence, {lay['bays']} bays, posts {lay['posts']}")
    for s in lay["segments"]:
        print(f"  run {s['run']}: {s['length_ft']:g} ft, {s['bays']} bays at {s['on_center_ft']:g} ft OC")
    print("\nMaterials:")
    for m in r["materials"]:
        sku = f" [{m['sku']}]" if m["sku"] else ""
        print(f"  {m['qty']:>5}  {m['item']}{sku}" + (f"  ({m['note']})" if m["note"] else ""))
    for a in r["assumptions"]:
        print(f"\nAssumed: {a}")
    for q in r["questions"]:
        print(f"Ask: {q}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
