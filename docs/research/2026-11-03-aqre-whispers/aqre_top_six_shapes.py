"""SCRATCH: every free 9-cell shape whose shading tops out at 6, judged on the shape alone. One process.

usage: aqre_top_six_shapes.py DIR

Shapes are free: rotations and reflections count once. Holed shapes are left out, since a hole under 9 cells cannot be
filled by whole regions. A shape "holds v" when v of its cells can be shaded with no circle fixed: shaded cells are
low on one checkerboard colour and high on the other, at most 4 of each, no shaded 5, whispers on adjacent shaded pairs,
and no 4 in a line of one colour inside the shape. Shading elsewhere and other regions are ignored.

Also counted, per shape and circle cell: the same test with that cell holding the count's digit, as in the runs.

Controls: 1,285 free shapes with 37 holed, the known counts. Every 8 shape in shape-screen.json must hold 8. A solver
check (`region_holds`) must agree on every shape's 7 and 8. Writes top-six-shapes.json.
"""

import json
import sys
import time
from collections import Counter
from pathlib import Path

from aqre_r5_eight_sheet import has_hole
from aqre_r5_fixed_regions import region_holds
from aqre_r5_region_max import embed, lines_of
from itertools import combinations
from jigsaw_r5_diversity import shape_key


def normal(cells):
    top, left = min(r for r, _ in cells), min(c for _, c in cells)
    return frozenset((r - top, c - left) for r, c in cells)


def images(cells):
    out = []
    now = list(cells)
    for _ in range(4):
        now = [(c, -r) for r, c in now]
        out.append(normal(now))
        out.append(normal([(r, -c) for r, c in now]))
    return out


def canonical(cells):
    return min(tuple(sorted(x)) for x in images(cells))


def free_shapes():
    level = {canonical([(0, 0)])}
    for _ in range(8):
        grown = set()
        for shape in level:
            cells = set(shape)
            for r, c in shape:
                for x in ((r + 1, c), (r - 1, c), (r, c + 1), (r, c - 1)):
                    if x not in cells:
                        grown.add(canonical([*shape, x]))
        level = grown
    return sorted(level)


def holds(cells, count, lines, root=None):
    fixed = {root: count} if root else {}
    for chosen in combinations(sorted(cells), count):
        shaded = set(chosen)
        if any(len({x in shaded for x in line}) == 1 for line in lines):
            continue
        evens = [x for x in chosen if sum(x) % 2 == 0]
        odds = [x for x in chosen if sum(x) % 2 == 1]
        if len(evens) > 4 or len(odds) > 4:
            continue
        for lows, highs in ((evens, odds), (odds, evens)):
            if root and root in shaded and root in lows:
                continue
            if embed(lows, highs, fixed, shaded):
                return True
    return False


def main(out):
    begun = time.time()
    shapes = free_shapes()
    holed = [s for s in shapes if has_hole(s)]
    print(f"free shapes {len(shapes)}, holed {len(holed)}", flush=True)
    if (len(shapes), len(holed)) != (1285, 37):
        raise SystemExit("SHAPE COUNT FAILED")
    open_shapes = [s for s in shapes if not has_hole(s)]
    screen = json.loads((out / "shape-screen.json").read_text())
    eights = {canonical([tuple(c) for c in x["cells"]]) for x in screen}
    tops = {}
    with_circle = Counter()
    pairs_top_six = 0
    disagree = 0
    for i, shape in enumerate(open_shapes):
        lines = lines_of(set(shape))
        can_8 = holds(shape, 8, lines)
        can_7 = holds(shape, 7, lines)
        if can_8 != region_holds(sorted(shape), 8, {}) or can_7 != region_holds(sorted(shape), 7, {}):
            disagree += 1
        tops[shape] = 8 if can_8 else 7 if can_7 else 6
        if tops[shape] < 8 and shape in eights:
            raise SystemExit(f"CONTROL FAILED: {shape} is in the screen but cannot hold 8")
        for root in shape:
            top = 8 if holds(shape, 8, lines, root) else 7 if holds(shape, 7, lines, root) else 6
            with_circle[top] += 1
            pairs_top_six += top == 6
        if i % 200 == 199:
            print(f"{i + 1} of {len(open_shapes)}, {time.time() - begun:.0f}s, {sorted(Counter(tops.values()).items())}", flush=True)
    tally = Counter(tops.values())
    keys = {shape_key(list(s)) for s in tops}
    print(f"{len(open_shapes)} open shapes in {time.time() - begun:.0f}s, shape_key groups {len(keys)}", flush=True)
    print(f"highest count on the shape alone: {sorted(tally.items())}", flush=True)
    print(f"shape and circle cell pairs, before the shape's own symmetry: {sorted(with_circle.items())}", flush=True)
    print(f"solver disagreements: {disagree}; screen shapes {len(eights)}, of them holding 8: {sum(tops.get(s) == 8 for s in eights)}", flush=True)
    six = [s for s, top in tops.items() if top == 6]
    (out / "top-six-shapes.json").write_text(json.dumps(six))
    print(f"TOP OUT AT 6: {len(six)}", flush=True)


if __name__ == "__main__":
    main(Path(sys.argv[1]))
