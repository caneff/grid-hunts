"""SCRATCH: every region that can be the circled 8 in r5, under digits and whispers.

A region here is a connected 9-cell set holding the circled cell (r5, column c), c in
1-5 by mirror, plus at most one other r5 cell, which would be the uncircled 9. No
straight region. Exhaustive over those sets, looking at the region alone.

By hand: a count of 8 leaves one unshaded cell, which must be the region's 5 since a 5 is
never shaded. So the circled 8 is shaded and high, which sets each colour's sign, and a
second r5 cell (the 9) is shaded too. The shaded cells hold 1-4 on one colour and 6-9 on
the other, so exactly 4 of each. Adjacent shaded cells differ by at least 5, and no 4 in
a line of one colour within the region.
"""

import json
import sys
from collections import Counter
from itertools import permutations
from pathlib import Path

from aqre_jigsaw_feasible import neighbours
from aqre_r5_fixed_regions import region_holds
from jigsaw_r5_diversity import shape_key

ROW = 4


def grow(root):
    """All connected 9-cell sets containing root with at most 2 r5 cells."""
    level = {frozenset([root])}
    for _ in range(8):
        following = set()
        for cells in level:
            for cell in cells:
                for other in neighbours(cell):
                    if other in cells:
                        continue
                    new = cells | {other}
                    if sum(r == ROW for r, _ in new) <= 2:
                        following.add(new)
        level = following
    return level


def runs_ok(cells, shaded):
    for r, c in cells:
        for line in ([(r, c + i) for i in range(4)], [(r + i, c) for i in range(4)]):
            if all(x in cells for x in line):
                values = {x in shaded for x in line}
                if len(values) == 1:
                    return False
    return True


def holds_eight(cells, root):
    """Ways to shade 8 cells and place digits: returns the first, or None."""
    high_colour = sum(root) % 2
    nine = next((x for x in cells if x[0] == ROW and x != root), None)
    for hole in cells:
        if hole == root or hole == nine:
            continue
        shaded = cells - {hole}
        highs = [x for x in shaded if sum(x) % 2 == high_colour]
        lows = [x for x in shaded if sum(x) % 2 != high_colour]
        if len(highs) != 4 or len(lows) != 4 or not runs_ok(cells, shaded):
            continue
        edges = [(a, b) for a in lows for b in neighbours(a) if b in shaded]
        for low_digits in permutations((1, 2, 3, 4)):
            place = dict(zip(lows, low_digits))
            others = [x for x in highs if x != root]
            for high_digits in permutations((6, 7, 9)):
                place.update(zip(others, high_digits))
                place[root] = 8
                if nine and place[nine] != 9:
                    continue
                if all(place[b] - place[a] >= 5 for a, b in edges):
                    return hole, place
    return None


def straight(cells):
    return len({c for _, c in cells}) == 1 or len({r for r, _ in cells}) == 1


def main(out):
    catalogue = []
    disagree = checked = 0
    for c in range(5):
        root = (ROW, c)
        all_sets = grow(root)
        kept = [x for x in all_sets if not straight(x)]
        held = []
        for i, cells in enumerate(kept):
            got = holds_eight(cells, root)
            if i % 2000 == 0:
                nine = next((x for x in cells if x[0] == ROW and x != root), None)
                fixed = {root: 8, **({nine: 9} if nine else {})}
                checked += 1
                if bool(got) != region_holds(sorted(cells), 8, fixed):
                    disagree += 1
            if got:
                held.append((cells, got))
        print(f"r5c{c + 1}: {len(all_sets)} sets, {len(kept)} not straight, {len(held)} can be the circled 8", flush=True)
        for cells, (hole, place) in held:
            catalogue.append({
                "column": c,
                "cells": sorted(cells),
                "hole": hole,
                "digits": [[*cell, digit] for cell, digit in sorted(place.items())],
            })
    print(f"solver cross-check: {checked} sets, {disagree} disagree", flush=True)
    shapes = Counter(shape_key(sorted(tuple(x) for x in e["cells"])) for e in catalogue)
    print(f"total {len(catalogue)}, {len(shapes)} distinct free shapes", flush=True)
    print("with a second r5 cell:", sum(sum(r == ROW for r, _ in e["cells"]) == 2 for e in catalogue), flush=True)
    (out / "eight-regions-r5.json").write_text(json.dumps(catalogue))


if __name__ == "__main__":
    main(Path(sys.argv[1]))
