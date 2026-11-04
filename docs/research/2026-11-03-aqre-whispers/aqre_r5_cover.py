"""SCRATCH: strict r5 layouts as an exact cover over region catalogues. One worker.

Rules for a layout, each region judged alone: `n` is r5's uncircled column, holding the 9.
Each other r5 column roots one region, which holds no other r5 cell except possibly the 9.
- one region can be the circled 8 (its circle in r5c1-5, by mirror);
- one region can be a valid 7, cannot be a valid 8, and its shape forces the circled 7;
- six regions top out at 6, and can take the counts 1-6 between them;
- the ninth region is whatever is left, connected, with no rule on its shape.
No straight regions in the first eight.

`catalogue DIR` classifies every region and saves the lists. `estimate DIR SECONDS` runs
Knuth's random probes of the search tree: each probe follows one random path and multiplies
its branch sizes, so the mean estimates the number of layouts without listing them. An
estimate from a heavy-tailed sample can be well off, so it is reported with its spread. Each
completed probe is also a sampled layout, saved for the fixed-region solve.
"""

import json
import pickle
import random
import statistics
import sys
import time
from pathlib import Path

from aqre_jigsaw_feasible import neighbours
from aqre_r5_eight_regions import grow, holds_eight, straight
from aqre_r5_fixed_regions import can_match
from aqre_r5_region_max import holds, lines_of
from aqre_r5_seven_unshaded import seven_ways

ROW = 4
CELLS = [(r, c) for r in range(9) for c in range(9)]
FULL = (1 << 81) - 1
ROW_MASK = sum(1 << (ROW * 9 + c) for c in range(9))


def bit(cell):
    return 1 << (cell[0] * 9 + cell[1])


def mask_of(cells):
    return sum(bit(x) for x in cells)


def mirror(mask):
    return sum(1 << (r * 9 + 8 - c) for r, c in CELLS if mask >> (r * 9 + c) & 1)


def catalogue(out):
    start = time.time()
    table = {c: {"eight": [], "seven": [], "either": [], "low": []} for c in range(9)}
    for c in range(5):
        root = (ROW, c)
        for cells in grow(root):
            if straight(cells):
                continue
            lines = lines_of(cells)
            mask = mask_of(cells)
            if holds_eight(cells, root):
                table[c]["eight"].append(mask)
                continue
            shaded_way, unshaded_way = seven_ways(cells, root, lines)
            if shaded_way != unshaded_way:
                table[c]["seven"].append(mask)
            elif shaded_way:
                table[c]["either"].append(mask)
            else:
                counts = tuple(v for v in range(1, 7) if holds(cells, root, v, lines))
                table[c]["low"].append((mask, counts))
        print(f"r5c{c + 1}: 8 {len(table[c]['eight'])}, 7 {len(table[c]['seven'])}, low {len(table[c]['low'])}, {time.time() - start:.0f}s", flush=True)
    for c in range(5, 9):
        source = table[8 - c]
        table[c]["eight"] = [mirror(m) for m in source["eight"]]
        table[c]["seven"] = [mirror(m) for m in source["seven"]]
        table[c]["either"] = [mirror(m) for m in source["either"]]
        table[c]["low"] = [(mirror(m), v) for m, v in source["low"]]
    with (out / "cover-catalogue.tmp").open("wb") as f:
        pickle.dump(table, f)
    (out / "cover-catalogue.tmp").replace(out / "cover-catalogue.pickle")
    lows = [v for _, v in table[4]["low"]]
    print("r5c5 low regions by counts held, top 6 kinds:", sorted(
        ((lows.count(k), k) for k in set(lows)), reverse=True)[:6], flush=True)


def flip(mask):
    return sum(1 << ((8 - r) * 9 + c) for r, c in CELLS if mask >> (r * 9 + c) & 1)


def load(out):
    """Catalogues with only one 8 region kept from each symmetry group.

    The left-right mirror, top-bottom flip and 180 rotation keep r5 and the checkerboard.
    The 8 region's column is limited to r5c1-5, which settles the mirror except in r5c5.
    So r5c1-4 keep one of each flip pair and r5c5 keeps one of each group of 4. A layout whose
    8 region maps to itself under one of these still appears in more than one version.
    The 90 degree turns and diagonal reflections map r5 to c5, the same problem turned.
    """
    with (out / "cover-catalogue.pickle").open("rb") as f:
        table = pickle.load(f)
    for c in range(4):
        table[c]["eight"] = [m for m in table[c]["eight"] if m <= flip(m)]
    table[4]["eight"] = [
        m for m in table[4]["eight"]
        if m == min(m, flip(m), mirror(m), flip(mirror(m)))
    ]
    print("8 regions kept, one per symmetry group, r5c1-5:",
          [len(table[c]["eight"]) for c in range(5)], flush=True)
    return table


def allowed(mask, root, n):
    """No r5 cell but the root and possibly the 9."""
    others = mask & ROW_MASK & ~(1 << (ROW * 9 + root))
    return others == 0 or others == 1 << (ROW * 9 + n)


def components(free):
    left = free
    sizes = []
    while left:
        low = left & -left
        comp = low
        frontier = low
        while frontier:
            grown = 0
            f = frontier
            while f:
                b = f & -f
                f ^= b
                i = b.bit_length() - 1
                r, c = i // 9, i % 9
                for x, y in neighbours((r, c)):
                    grown |= 1 << (x * 9 + y)
            frontier = grown & left & ~comp
            comp |= frontier
        sizes.append(comp)
        left &= ~comp
    return sizes


def free_ok(free, roots):
    """Free cells split into whole regions, with room for each remaining root."""
    spare = 0
    for comp in components(free):
        size = bin(comp).count("1")
        if size % 9:
            return False
        held = sum(comp >> (ROW * 9 + c) & 1 for c in roots)
        if held > size // 9:
            return False
        spare += size // 9 - held
    return spare == 1


def probe(table, rng):
    """One random path: (weight, layout or None), and how deep it got."""
    c8 = rng.randrange(5)
    n = rng.choice([c for c in range(9) if c != c8])
    weight = 5 * 8
    free = FULL
    picked = {}
    depth = 0
    c7 = rng.choice([c for c in range(9) if c not in (c8, n)])
    weight *= 7
    plan = [(c8, "eight"), (c7, "seven")]
    for c, kind in plan:
        options = [m for m in table[c][kind] if allowed(m, c, n) and m & free == m]
        if not options:
            return 0, None, depth
        weight *= len(options)
        chosen = rng.choice(options)
        free &= ~chosen
        picked[c] = chosen
        roots = [x for x in range(9) if x not in picked and x != n]
        if not free_ok(free, roots):
            return 0, None, depth
        depth += 1
    counts = []
    while True:
        roots = [x for x in range(9) if x not in picked and x != n]
        if not roots:
            break
        best = None
        for c in roots:
            options = [(m, v) for m, v in table[c]["low"] if m & free == m and allowed(m, c, n)]
            if best is None or len(options) < len(best[1]):
                best = (c, options)
        c, options = best
        if not options:
            return 0, None, depth
        weight *= len(options)
        m, v = rng.choice(options)
        free &= ~m
        picked[c] = m
        counts.append(v)
        if not free_ok(free, [x for x in roots if x != c]):
            return 0, None, depth
        depth += 1
    if len(components(free)) != 1:
        return 0, None, depth
    if not can_match(counts):
        return 0, None, depth + 1
    return weight, {"n": n, "eight": c8, "seven": c7, "picked": picked, "ninth": free}, depth + 1


def estimate(out, seconds):
    table = load(out)
    rng = random.Random(61)
    begun = time.time()
    weights = []
    depths = {}
    found = []
    while time.time() - begun < seconds:
        weight, layout, depth = probe(table, rng)
        weights.append(weight)
        depths[depth] = depths.get(depth, 0) + 1
        if layout:
            found.append(layout)
    mean = statistics.fmean(weights)
    error = statistics.pstdev(weights) / len(weights) ** 0.5
    print(f"{len(weights)} probes in {time.time() - begun:.0f}s; deepest reached {sorted(depths.items())}", flush=True)
    print(f"estimated layouts: {mean:.3g}, standard error {error:.3g}; completed probes {len(found)}", flush=True)
    with (out / "cover-layouts.jsonl").open("a") as f:
        for layout in found:
            f.write(json.dumps({
                **{k: layout[k] for k in ("n", "eight", "seven")},
                "picked": {str(c): str(m) for c, m in layout["picked"].items()},
                "ninth": str(layout["ninth"]),
            }) + "\n")


if __name__ == "__main__":
    out_dir = Path(sys.argv[2])
    if sys.argv[1] == "catalogue":
        catalogue(out_dir)
    else:
        estimate(out_dir, float(sys.argv[3]))
