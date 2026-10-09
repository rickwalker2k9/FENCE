"""Faith's fence takeoff engine.

Turns a job description (runs, gates, height, style, terrain) into a bill of
materials. Faith never does this math herself: she calls this through the
`fence_estimate` tool and reads back the `spoken` line, the same way Claire
in Vantage only quotes numbers a tool returned.

Supported today: 6 ft-style wood privacy (side-by-side or board-on-board) and
galvanized chain-link. Every rule lives in the constants below so the
Master-Halco team can tune them without touching the logic.
"""

from __future__ import annotations

import json
import math
import os
from dataclasses import dataclass, field
from pathlib import Path

# ---------------------------------------------------------------- rules

MAX_SPACING_FT = {"wood_privacy": 8.0, "chain_link": 10.0}

# Pickets per linear foot for a nominal 6 in (actual 5.5 in) picket.
PICKETS_PER_FT = {
    "side_by_side": 12 / 5.5,  # 2.18, often quoted as 2.17
    "board_on_board": 2.7,  # front and back layers with about 1 in overlap
}

# Horizontal 2x4 rails per bay, by fence height.
RAILS_PER_BAY = {4: 2, 5: 2, 6: 3, 7: 3, 8: 4}

# Setting depth in inches.
WOOD_DEPTH_IN = {"line": 24, "end": 24, "corner": 24, "gate": 36}
CHAIN_LINK_DEPTH_IN = {"line": 24, "end": 36, "corner": 36, "gate": 36}

HOLE_DIAMETER_IN = 10.0
BAG_LB = 60
BAG_YIELD_CU_FT = 0.45  # one 60 lb bag of post-hole concrete

WOOD_POST_STOCK_FT = (8, 10, 12, 14, 16)
CHAIN_LINK_LINE_OD_IN = 1.875
CHAIN_LINK_TERMINAL_OD_IN = 2.375
FABRIC_ROLL_FT = 50
TOP_RAIL_STICK_FT = 21

DEFAULT_WASTE_PCT = 10.0
SLOPE_WASTE_PCT = 15.0
DOUBLE_GATE_OVER_FT = 6.0  # wider openings get a double drive gate

FENCE_TYPES = ("wood_privacy", "chain_link")
STYLES = tuple(PICKETS_PER_FT)
TERRAINS = ("flat", "racked", "stepped")


class EstimateError(ValueError):
    """A job Faith can't price as described. The message is safe to say aloud."""


# ---------------------------------------------------------------- input

@dataclass
class Gate:
    width_ft: float
    run: int = 0  # index into runs
    at_ft: float | None = None  # distance from the start of the run to the gate's near edge


@dataclass
class Job:
    fence_type: str = "wood_privacy"
    height_ft: float = 6
    runs: list[float] = field(default_factory=list)
    gates: list[Gate] = field(default_factory=list)
    style: str = "board_on_board"
    terrain: str = "flat"
    grade_pct: float | None = None
    waste_pct: float | None = None
    max_spacing_ft: float | None = None
    location: str | None = None
    assumptions: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, d: dict) -> "Job":
        d = dict(d or {})
        assumptions: list[str] = []
        fence_type = _norm(d.get("fence_type") or "wood_privacy")
        aliases = {"wood": "wood_privacy", "privacy": "wood_privacy", "cedar": "wood_privacy", "chainlink": "chain_link", "chain": "chain_link"}
        fence_type = aliases.get(fence_type, fence_type)
        if fence_type not in FENCE_TYPES:
            raise EstimateError("I can run takeoffs for wood privacy and chain-link right now. Which of those is closest?")

        runs = d.get("runs")
        if runs:
            runs = [_pos(r, "Each run length") for r in runs]
        else:
            total = d.get("total_feet")
            if total is None:
                raise EstimateError("How many total feet of fence are we running?")
            total = _pos(total, "Total footage")
            corners = int(d.get("corners") or 0)
            if corners < 0:
                raise EstimateError("Corners can't be negative.")
            runs = [total / (corners + 1)] * (corners + 1)
            if corners:
                assumptions.append(f"Split {_ft(total)} into {corners + 1} equal runs; give me each run's length for an exact layout.")

        gates = []
        for g in d.get("gates") or []:
            if isinstance(g, (int, float, str)):
                g = {"width_ft": g}
            run = int(g.get("run") or 0)
            if not 0 <= run < len(runs):
                raise EstimateError(f"There's no run {run + 1} on this job.")
            at = g.get("at_ft")
            gates.append(Gate(width_ft=_pos(g.get("width_ft"), "Gate width"), run=run, at_ft=None if at is None else float(at)))

        style = _norm(d.get("style") or "board_on_board")
        style = {"shadowbox": "board_on_board", "bob": "board_on_board", "flat": "side_by_side", "stockade": "side_by_side"}.get(style, style)
        if fence_type == "wood_privacy" and style not in STYLES:
            raise EstimateError("Is that side-by-side pickets or board-on-board?")

        terrain = _norm(d.get("terrain") or "flat")
        if terrain not in TERRAINS:
            raise EstimateError("Is the ground flat, a mild slope we can rack, or steep enough to step?")
        grade = d.get("grade_pct")
        if terrain == "stepped" and grade is None:
            raise EstimateError("For a stepped fence I need the grade. Roughly how many inches does it drop per 10 feet?")

        height = float(d.get("height_ft") or 6)
        if fence_type == "wood_privacy" and int(round(height)) not in RAILS_PER_BAY:
            raise EstimateError("I can do wood privacy from 4 to 8 feet tall. What height are we building?")
        if fence_type == "chain_link" and not 3 <= height <= 12:
            raise EstimateError("I can do chain-link from 3 to 12 feet tall. What height are we building?")

        return cls(
            fence_type=fence_type,
            height_ft=height,
            runs=runs,
            gates=gates,
            style=style,
            terrain=terrain,
            grade_pct=None if grade is None else float(grade),
            waste_pct=None if d.get("waste_pct") is None else float(d["waste_pct"]),
            max_spacing_ft=None if d.get("max_spacing_ft") is None else _pos(d["max_spacing_ft"], "Post spacing"),
            location=d.get("location"),
            assumptions=assumptions,
        )


def _norm(s) -> str:
    return str(s).strip().lower().replace("-", "_").replace(" ", "_")


def _pos(v, what: str) -> float:
    try:
        f = float(v)
    except (TypeError, ValueError):
        raise EstimateError(f"{what} needs to be a number of feet.") from None
    if not f > 0:
        raise EstimateError(f"{what} has to be more than 0.")
    return f


def _ft(x: float) -> str:
    return f"{x:g} ft" if abs(x - round(x, 2)) < 1e-9 else f"{x:.2f} ft"


# ---------------------------------------------------------------- layout

@dataclass
class Segment:
    run: int
    length_ft: float
    bays: int
    on_center_ft: float


def _layout(job: Job, max_spacing: float):
    """Split runs at gates into fenced segments and classify every post.

    Returns (segments, post_counts, gate_widths). Posts are unique points:
    adjacent runs share a corner post, and a gate set flush against a run's
    end shares that post.
    """
    segments: list[Segment] = []
    kinds = {"line": 0, "end": 0, "corner": 0, "gate": 0}
    nruns = len(job.runs)

    # The kind of post at each run boundary, before gates touch them.
    boundary = ["end"] + ["corner"] * (nruns - 1) + ["end"]

    for i, length in enumerate(job.runs):
        gates = [g for g in job.gates if g.run == i]
        open_ft = sum(g.width_ft for g in gates)
        if open_ft >= length:
            raise EstimateError(f"The gates on run {i + 1} are as wide as the run itself.")

        if all(g.at_ft is None for g in gates):
            # Center the gates so every fenced segment comes out the same.
            n = len(gates) + 1
            seg = (length - open_ft) / n
            spans, pos = [], 0.0
            for g in gates:
                spans.append((pos + seg, pos + seg + g.width_ft))
                pos += seg + g.width_ft
            if gates:
                job.assumptions.append(f"Placed the gate{'s' if len(gates) > 1 else ''} on run {i + 1} so the fence on each side is even; tell me if it sits elsewhere.")
        elif any(g.at_ft is None for g in gates):
            raise EstimateError(f"Give me where every gate on run {i + 1} sits, or none of them and I'll center them.")
        else:
            spans = sorted((g.at_ft, g.at_ft + g.width_ft) for g in gates)
            if spans[0][0] < 0 or spans[-1][1] > length + 1e-9 or any(a[1] > b[0] + 1e-9 for a, b in zip(spans, spans[1:])):
                raise EstimateError(f"The gates on run {i + 1} overlap or fall outside the run.")

        # Fenced pieces between gate openings.
        edges = [0.0] + [x for s in spans for x in s] + [length]
        pieces = [(edges[k], edges[k + 1]) for k in range(0, len(edges), 2)]
        for a, b in pieces:
            seg_len = b - a
            if seg_len < 1e-9:
                continue
            bays = max(1, math.ceil(seg_len / max_spacing - 1e-9))
            segments.append(Segment(run=i + 1, length_ft=round(seg_len, 4), bays=bays, on_center_ft=seg_len / bays))
            kinds["line"] += bays - 1

        # Posts at the gate edges and run ends.
        start_is_gate = bool(spans) and spans[0][0] < 1e-9
        end_is_gate = bool(spans) and spans[-1][1] > length - 1e-9
        interior_gate_posts = 2 * len(spans) - start_is_gate - end_is_gate
        kinds["gate"] += interior_gate_posts
        if start_is_gate:
            boundary[i] = "gate"
        if end_is_gate:
            boundary[i + 1] = "gate"

    for b in boundary:
        kinds[b] += 1
    return segments, kinds


# ---------------------------------------------------------------- takeoff

def _hole_cu_ft(depth_in: float, displacement_sq_in: float) -> float:
    hole = math.pi * (HOLE_DIAMETER_IN / 2) ** 2 * depth_in
    return (hole - displacement_sq_in * depth_in) / 1728


def _stock_length(need_ft: float) -> int | None:
    return next((s for s in WOOD_POST_STOCK_FT if s >= need_ft - 1e-9), None)


def _catalog() -> dict:
    path = Path(os.environ.get("FAITH_CATALOG") or Path(__file__).with_name("catalog.json"))
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return {}


def estimate(data: dict) -> dict:
    """Run a takeoff. Raises EstimateError with a speakable message on bad input."""
    job = Job.from_dict(data)
    max_spacing = job.max_spacing_ft or MAX_SPACING_FT[job.fence_type]
    segments, posts = _layout(job, max_spacing)

    total_ft = sum(job.runs)
    gate_ft = sum(g.width_ft for g in job.gates)
    fence_ft = total_ft - gate_ft
    bays = sum(s.bays for s in segments)
    sloped = job.terrain != "flat"
    waste = job.waste_pct if job.waste_pct is not None else (SLOPE_WASTE_PCT if sloped else DEFAULT_WASTE_PCT)
    waste_x = 1 + waste / 100

    # Stepped fences need taller posts: each post carries the uphill panel's top.
    step_ft = 0.0
    if job.terrain == "stepped":
        step_ft = max(s.on_center_ft for s in segments) * job.grade_pct / 100
        job.assumptions.append(f"Stepped at {job.grade_pct:g}% grade: about {step_ft * 12:.0f} in drop per bay, added to every post.")
    elif job.terrain == "racked":
        job.assumptions.append("Racked to follow the ground; footage should be measured along the slope.")

    items: list[dict] = []
    add = lambda key, qty, desc, note="": items.append({"key": key, "item": desc, "qty": qty, "note": note})
    questions: list[str] = []
    concrete_cu_ft = 0.0
    depth = WOOD_DEPTH_IN if job.fence_type == "wood_privacy" else CHAIN_LINK_DEPTH_IN

    if job.fence_type == "wood_privacy":
        h = int(round(job.height_ft))
        # Posts: one stock length for line/end/corner, one for gates.
        groups = {"post": posts["line"] + posts["end"] + posts["corner"], "gate_post": posts["gate"]}
        for key, qty in groups.items():
            if not qty:
                continue
            d_in = depth["gate" if key == "gate_post" else "line"]
            need = h + d_in / 12 + step_ft
            stock = _stock_length(need)
            if stock is None:
                raise EstimateError(f"Those posts would need to be about {need:.0f} feet long. That slope is beyond a standard stepped fence; let's get the counter involved.")
            use = "gate posts" if key == "gate_post" else "line, end and corner posts"
            add(f"wood_post_4x4x{stock}", qty, f"4x4x{stock} post", f"{use}, set {d_in} in deep")
            concrete_cu_ft += qty * _hole_cu_ft(d_in, 3.5 * 3.5)

        rails = bays * RAILS_PER_BAY[h]
        add("rail_2x4x8", math.ceil(rails * waste_x - 1e-9), "2x4x8 rail", f"{RAILS_PER_BAY[h]} per bay x {bays} bays, plus {waste:g}% waste")

        # Gates are clad in the same pickets as the fence.
        rate = PICKETS_PER_FT[job.style]
        picket_ft = fence_ft + gate_ft
        pickets = math.ceil(picket_ft * rate * waste_x - 1e-9)
        style = "board-on-board" if job.style == "board_on_board" else "side-by-side"
        add(f"picket_{h}ft", pickets, f"{h} ft x 5.5 in picket", f"{style}, {rate:.2f} per ft over {_ft(picket_ft)}, plus {waste:g}% waste")

        for g in job.gates:
            if g.width_ft > DOUBLE_GATE_OVER_FT:
                add("wood_double_gate_kit", 1, f"Double drive-gate hardware kit ({_ft(g.width_ft)})", "4 hinges, cane bolt, latch")
                add("rail_2x4x8", 6, "2x4x8 rail", f"6 for the gate frame, two {_ft(g.width_ft / 2)} leaves")
            else:
                add("wood_walk_gate_kit", 1, f"Walk-gate hardware kit ({_ft(g.width_ft)})", "2 hinges, latch")
                add("rail_2x4x8", 3, "2x4x8 rail", "3 for the gate frame and brace")
        if any(g.width_ft > 4 for g in job.gates):
            questions.append("That's a wide gate. Do you want 4x6 or 6x6 gate posts instead of 4x4?")
    else:
        h = job.height_ft
        terminals = posts["end"] + posts["corner"] + posts["gate"]
        line_len = h + depth["line"] / 12 + step_ft
        term_len = h + depth["end"] / 12 + step_ft
        if posts["line"]:
            add("cl_line_post", posts["line"], f'1-7/8" line post, {_half_up(line_len):g} ft', f"set {depth['line']} in deep")
            concrete_cu_ft += posts["line"] * _hole_cu_ft(depth["line"], math.pi * (CHAIN_LINK_LINE_OD_IN / 2) ** 2)
        add("cl_terminal_post", terminals, f'2-3/8" terminal post, {_half_up(term_len):g} ft', f"{posts['end']} end, {posts['corner']} corner, {posts['gate']} gate; set {depth['end']} in deep")
        concrete_cu_ft += terminals * _hole_cu_ft(depth["end"], math.pi * (CHAIN_LINK_TERMINAL_OD_IN / 2) ** 2)

        rolls = math.ceil(fence_ft * waste_x / FABRIC_ROLL_FT - 1e-9)
        add("cl_fabric_roll", rolls, f"{h:g} ft galvanized fabric, {FABRIC_ROLL_FT} ft roll", f"{_ft(fence_ft)} of fence plus {waste:g}%")
        sticks = sum(math.ceil(s.length_ft / TOP_RAIL_STICK_FT - 1e-9) for s in segments)
        add("cl_top_rail", sticks, f'1-3/8" top rail, {TOP_RAIL_STICK_FT} ft', "swaged, cut per segment")

        # A fabric end lands on each end and gate post, two on each corner.
        ends = posts["end"] + posts["gate"] + 2 * posts["corner"]
        bands = max(1, math.ceil(h) - 1)
        add("cl_tension_bar", ends, f"{h:g} ft tension bar", "1 per fabric end")
        add("cl_tension_band", ends * bands, "Tension band", f"{bands} per fabric end")
        add("cl_brace_band", ends, "Brace band", "1 per fabric end")
        add("cl_rail_end", ends, "Rail end cup", "1 per fabric end")
        add("cl_dome_cap", terminals, "Terminal dome cap", "")
        if posts["line"]:
            add("cl_loop_cap", posts["line"], "Line post loop cap", "")
        ties = posts["line"] * math.ceil(h) + math.ceil(fence_ft / 2)
        add("cl_tie_wire", ties, "Aluminum tie wire", "every 12 in on line posts, every 24 in on top rail")
        for g in job.gates:
            if g.width_ft > DOUBLE_GATE_OVER_FT:
                add("cl_double_gate", 1, f"{h:g} ft x {_ft(g.width_ft)} double drive gate", "")
                add("cl_gate_hinge", 4, "Gate hinge", "")
                add("cl_cane_bolt", 1, "Drop rod / cane bolt", "")
                add("cl_fork_latch", 1, "Fork latch", "")
            else:
                add("cl_walk_gate", 1, f"{h:g} ft x {_ft(g.width_ft)} walk gate", "")
                add("cl_gate_hinge", 2, "Gate hinge", "")
                add("cl_fork_latch", 1, "Fork latch", "")
        questions.append("Do you want a bottom tension wire? I left it off.")

    bags = math.ceil(concrete_cu_ft / BAG_YIELD_CU_FT - 1e-9)
    add("concrete_60lb", bags, f"{BAG_LB} lb post-hole concrete", f'{HOLE_DIAMETER_IN:g}" holes, {concrete_cu_ft:.1f} cu ft total')

    items = _merge(items)
    catalog = _catalog()
    for it in items:
        it["sku"] = (catalog.get(it["key"]) or {}).get("sku") or None

    total_posts = sum(posts.values())
    ocs = sorted({round(s.on_center_ft, 2) for s in segments})
    oc_text = f"{ocs[0]:g}" if len(ocs) == 1 else f"{ocs[0]:g} to {ocs[-1]:g}"

    loc = (job.location or "").lower()
    if "okc" in loc or "oklahoma" in loc:
        questions.append("Have you called OKIE811 to mark utilities? It's free and required before digging in Oklahoma.")
    elif job.location:
        questions.append("Have utilities been marked? Call 811 before digging.")

    return {
        "job": {
            "fence_type": job.fence_type,
            "height_ft": job.height_ft,
            "style": job.style if job.fence_type == "wood_privacy" else None,
            "terrain": job.terrain,
            "grade_pct": job.grade_pct,
            "location": job.location,
        },
        "layout": {
            "total_ft": round(total_ft, 2),
            "gate_opening_ft": round(gate_ft, 2),
            "fence_ft": round(fence_ft, 2),
            "max_spacing_ft": max_spacing,
            "bays": bays,
            "on_center_ft": ocs,
            "segments": [{"run": s.run, "length_ft": round(s.length_ft, 2), "bays": s.bays, "on_center_ft": round(s.on_center_ft, 2)} for s in segments],
            "posts": {**posts, "total": total_posts},
        },
        "materials": items,
        "concrete": {"bags": bags, "bag_lb": BAG_LB, "cu_ft": round(concrete_cu_ft, 1)},
        "waste_pct": waste,
        "assumptions": job.assumptions,
        "questions": questions,
        "basis": "Faith takeoff from standard fencing rules. Quantities only: stock and pricing come from the Master-Halco counter.",
        "spoken": _spoken(job, total_ft, bays, oc_text, total_posts, items, bags, waste),
    }


def _half_up(x: float) -> float:
    return math.ceil(x * 2 - 1e-9) / 2


def _merge(items: list[dict]) -> list[dict]:
    """Combine lines for the same item (e.g. fence rails and gate-frame rails)."""
    out: dict[str, dict] = {}
    for it in items:
        k = it["key"]
        if k in out:
            out[k]["qty"] += it["qty"]
            out[k]["note"] = "; ".join(n for n in (out[k]["note"], it["note"]) if n)
        else:
            out[k] = dict(it)
    return list(out.values())


def _spoken(job: Job, total_ft, bays, oc_text, total_posts, items, bags, waste) -> str:
    """30 to 60 words, digits only, the way Claire speaks."""
    qty = lambda prefix: sum(i["qty"] for i in items if i["key"].startswith(prefix))
    gates = len(job.gates)
    gate_txt = f" with {gates} gate{'s' if gates > 1 else ''}" if gates else ""
    head = f"For {total_ft:g} feet of {job.height_ft:g} foot"
    if job.fence_type == "wood_privacy":
        style = "board-on-board" if job.style == "board_on_board" else "side-by-side"
        return (
            f"{head} {style} privacy{gate_txt}: {bays} bays at {oc_text} feet on center, "
            f"{total_posts} posts, {qty('rail_')} rails, {qty('picket_')} pickets with {waste:g}% waste, "
            f"and {bags} bags of concrete."
        )
    return (
        f"{head} chain-link{gate_txt}: {bays} bays at {oc_text} feet on center, "
        f"{total_posts} posts, {qty('cl_fabric_roll')} rolls of fabric, {qty('cl_top_rail')} sticks of top rail, "
        f"and {bags} bags of concrete."
    )
