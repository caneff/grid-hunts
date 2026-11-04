"""SCRATCH: r5 exact cover with colour taken from the 8. One worker.

Chris, 2026-11-04: only one r5 region can be the 8 and only one can be the 7. The 8 is always
shaded, so its cell's checkerboard colour is high everywhere. A region is judged alone but
with that colour known: on the opposite colour its circled cell is low if shaded, so it can
never be the 8, and its 7 could only be unshaded.

For each region and each of the two colours for its circled cell:
- able 8, able 7 shaded, able 7 unshaded, and which of counts 1-6 it can hold.
A layout has one 8 region (same colour, one per symmetry group), one 7 region (not able 8, able
7), six low regions (not able 8, not able 7, able to take 1-6 between them) and a ninth with
no rule. `forced` also needs the 7 region's shape to force the circled 7 one way, given colour.

Each case is one place of r5's 9 and one parity for the 8's column. INFEASIBLE is a proof for
that case on these lists. A layout found goes to the fixed-region solve for digits and shading;
if that fails it is cut and the case continues until its cap. It stops at the first grid.
"""

import json
import pickle
import sys
import time
from itertools import combinations
from pathlib import Path

from aqre_jigsaw_feasible import connected
from aqre_jigsaw_r5_staged import finish
from aqre_r5_cover import FULL, allowed, components, flip, mask_of, mirror
from aqre_r5_eight_regions import grow, holds_eight, straight
from aqre_r5_fixed_regions import attempt, can_match
from aqre_r5_region_max import embed, holds, lines_of
from ortools.sat.python import cp_model

ROW = 4
CASE_LIMIT = 900.0
CELLS = [(r, c) for r in range(9) for c in range(9)]


def holds_coloured(cells, root, count, lines, root_high, root_shaded=None):
    """Can it hold `count` with the root's colour high or low? Optionally force the root."""
    nine = next((x for x in cells if x[0] == ROW and x != root), None)
    fixed = {root: count, **({nine: 9} if nine else {})}
    high_parity = sum(root) % 2 if root_high else (sum(root) + 1) % 2
    for chosen in combinations(sorted(cells), count):
        picked = set(chosen)
        if root_shaded is not None and (root in picked) != root_shaded:
            continue
        if any(len({x in picked for x in line}) == 1 for line in lines):
            continue
        highs = [x for x in chosen if sum(x) % 2 == high_parity]
        lows = [x for x in chosen if sum(x) % 2 != high_parity]
        if len(highs) > 4 or len(lows) > 4:
            continue
        good = True
        for cell, digit in fixed.items():
            if cell in picked and (digit == 5 or (digit < 5) != (cell in lows)):
                good = False
        if good and embed(lows, highs, fixed, picked):
            return True
    return False


def build_catalogue(out):
    begun = time.time()
    table = {c: [] for c in range(9)}
    disagree = checked = 0
    for c in range(5):
        root = (ROW, c)
        for i, cells in enumerate(grow(root)):
            if straight(cells):
                continue
            lines = lines_of(cells)
            entry = {"mask": mask_of(cells)}
            for root_high in (True, False):
                eight = holds_coloured(cells, root, 8, lines, root_high)
                shaded_7 = holds_coloured(cells, root, 7, lines, root_high, True)
                unshaded_7 = holds_coloured(cells, root, 7, lines, root_high, False)
                counts = ()
                if not (eight or shaded_7 or unshaded_7):
                    counts = tuple(v for v in range(1, 7) if holds_coloured(cells, root, v, lines, root_high))
                entry[root_high] = (eight, shaded_7, unshaded_7, counts)
            if i % 500 == 0:
                checked += 1
                any_8 = entry[True][0] or entry[False][0]
                any_7 = any(entry[o][1] or entry[o][2] for o in (True, False))
                disagree += any_8 != holds_eight(cells, root) or any_7 != holds(cells, root, 7, lines)
                if entry[False][0]:
                    disagree += 1
            table[c].append(entry)
        print(f"r5c{c + 1}: {len(table[c])} regions, {time.time() - begun:.0f}s, check {checked}, disagree {disagree}", flush=True)
    for c in range(5, 9):
        table[c] = [{**e, "mask": mirror(e["mask"])} for e in table[8 - c]]
    with (out / "oriented.tmp").open("wb") as f:
        pickle.dump(table, f)
    (out / "oriented.tmp").replace(out / "oriented.pickle")
    for root_high in (True, False):
        for c in (4, 3):
            rows = [e[root_high] for e in table[c]]
            print(
                f"r5c{c + 1}, circled cell {'high' if root_high else 'low'} colour:",
                f"able 8 {sum(e[0] for e in rows)},",
                f"7 not 8 {sum(not e[0] and (e[1] or e[2]) for e in rows)},",
                f"forced 7 {sum(not e[0] and e[1] != e[2] for e in rows)},",
                f"low {sum(not e[0] and not e[1] and not e[2] for e in rows)}",
                flush=True,
            )
    return disagree == 0


def canonical(mask, c):
    if c < 4:
        return mask <= flip(mask)
    return mask == min(mask, flip(mask), mirror(mask), flip(mirror(mask)))


def solve_case(table, n, parity, forced, out, tally):
    m = cp_model.CpModel()
    by_cell = {i: [] for i in range(81)}
    columns = {c: [] for c in range(9) if c != n}
    eights, sevens = [], []
    info = []

    def add(c, mask, kind, counts):
        v = m.new_bool_var("")
        info.append((v, c, mask, kind, counts))
        columns[c].append(v)
        rest = mask
        while rest:
            b = rest & -rest
            rest ^= b
            by_cell[b.bit_length() - 1].append(v)
        return v

    for c in columns:
        same = c % 2 == parity
        for e in table[c]:
            mask = e["mask"]
            if not allowed(mask, c, n):
                continue
            eight, shaded_7, unshaded_7, counts = e[same]
            if eight:
                if same and c <= 4 and canonical(mask, c):
                    eights.append(add(c, mask, "eight", ()))
                continue
            if shaded_7 or unshaded_7:
                if not forced or shaded_7 != unshaded_7:
                    sevens.append(add(c, mask, "seven", ()))
                continue
            add(c, mask, "low", counts)
    if not eights or not sevens or any(not x for x in columns.values()):
        return "INFEASIBLE, a list is empty", 0, len(info), 0.0, False
    for options in columns.values():
        m.add_exactly_one(options)
    for options in by_cell.values():
        if options:
            m.add_at_most_one(options)
    m.add_exactly_one(eights)
    m.add_exactly_one(sevens)
    start = time.time()
    layouts = 0
    while time.time() - start < CASE_LIMIT:
        s = cp_model.CpSolver()
        s.parameters.num_workers = 1
        s.parameters.max_time_in_seconds = max(1.0, CASE_LIMIT - (time.time() - start))
        status = s.solve(m)
        name = s.status_name(status)
        if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            return name, layouts, len(info), time.time() - start, False
        chosen = [e for e in info if s.value(e[0])]
        free = FULL
        for _, _, mask, _, _ in chosen:
            free &= ~mask
        counts = [e[4] for e in chosen if e[3] == "low"]
        if len(components(free)) == 1 and can_match(counts):
            layouts += 1
            region = {}
            for _, c, mask, _, _ in chosen:
                for r, q in CELLS:
                    if mask >> (r * 9 + q) & 1:
                        region[r, q] = c
            for r, q in CELLS:
                region.setdefault((r, q), n)
            with (out / "oriented-layouts.jsonl").open("a") as f:
                f.write(json.dumps({"n": n, "parity": parity, "forced": forced, "region": [[region[r, q] for q in range(9)] for r in range(9)]}) + "\n")
            outcome, digits, shade = attempt(region, ROW, n)
            tally[outcome] = tally.get(outcome, 0) + 1
            print(f"  layout {layouts}: {outcome}; tally {tally}", flush=True)
            if digits:
                finish(digits, shade, region, n, out)
                return name, layouts, len(info), time.time() - start, True
        m.add_bool_or([e[0].Not() for e in chosen])
    return "capped", layouts, len(info), time.time() - start, False


def run(out):
    with (out / "oriented.pickle").open("rb") as f:
        table = pickle.load(f)
    tally = {}
    for forced in (True, False):
        for parity in (0, 1):
            for n in range(9):
                name, layouts, size, spent, done = solve_case(table, n, parity, forced, out, tally)
                print(f"forced 7 {forced}, 8 on column parity {parity}, 9 in r5c{n + 1}: {name}, {layouts} layouts, {size} candidates, {spent:.1f}s", flush=True)
                if done:
                    return


if __name__ == "__main__":
    out_dir = Path(sys.argv[1])
    if build_catalogue(out_dir):
        run(out_dir)
    else:
        print("catalogue check FAILED; cover not run", flush=True)
