"""SCRATCH: the highest count each r5 region can hold, judged on the region alone.

Regions are the same space as aqre_r5_eight_regions: connected 9 cells holding the circled
cell in r5c1-5, at most one other r5 cell (the uncircled 9), not straight. A region "can be
v" when v of its cells can be shaded with the circled cell's digit v, all nine digits
placed, signs and whispers on shaded cells, and no 4 in a line of one colour inside it.
Shading elsewhere and other regions are ignored, so "can be v" is necessary only.

`DIR K` runs a random K, cross-checked by solver; K 0 runs them all.
"""

import random
import sys
import time
from collections import Counter
from itertools import combinations
from pathlib import Path

from aqre_jigsaw_feasible import neighbours
from aqre_r5_eight_regions import grow, straight
from aqre_r5_fixed_regions import region_holds

ROW = 4


def lines_of(cells):
    lines = []
    for r, c in cells:
        for line in ([(r, c + i) for i in range(4)], [(r + i, c) for i in range(4)]):
            if all(x in cells for x in line):
                lines.append(line)
    return lines


def embed(lows, highs, fixed, shaded):
    """Distinct digits on shaded cells meeting every whisper, or False."""
    order = lows + highs
    low_set = set(lows)
    near = {x: [y for y in neighbours(x) if y in shaded] for x in order}
    placed = {}
    used = set()

    def place(i):
        if i == len(order):
            return True
        cell = order[i]
        if cell in low_set:
            choices = (1, 2, 3, 4)
        else:
            choices = (6, 7, 8, 9)
        if cell in fixed:
            choices = (fixed[cell],)
        for value in choices:
            if value in used or value in banned:
                continue
            if any(y in placed and abs(placed[y] - value) < 5 for y in near[cell]):
                continue
            placed[cell] = value
            used.add(value)
            if place(i + 1):
                return True
            del placed[cell]
            used.remove(value)
        return False

    banned = {d for x, d in fixed.items() if x not in shaded}
    return place(0)


def holds(cells, root, count, lines):
    nine = next((x for x in cells if x[0] == ROW and x != root), None)
    fixed = {root: count}
    if nine:
        fixed[nine] = 9
    pool = sorted(cells)
    for chosen in combinations(pool, count):
        shaded = set(chosen)
        if any(len({x in shaded for x in line}) == 1 for line in lines):
            continue
        evens = [x for x in chosen if sum(x) % 2 == 0]
        odds = [x for x in chosen if sum(x) % 2 == 1]
        if len(evens) > 4 or len(odds) > 4:
            continue
        for lows, highs in ((evens, odds), (odds, evens)):
            good = True
            for cell, digit in fixed.items():
                if cell in shaded:
                    if digit == 5 or (digit < 5) != (cell in lows):
                        good = False
            if good and embed(lows, highs, fixed, shaded):
                return True
    return False


def highest(cells, root):
    lines = lines_of(cells)
    for count in range(8, 0, -1):
        if holds(cells, root, count, lines):
            return count
    return 0


def main(out, k):
    regions = []
    for c in range(5):
        root = (ROW, c)
        regions += [(x, root) for x in grow(root) if not straight(x)]
    print(f"{len(regions)} regions", flush=True)
    rng = random.Random(3)
    picks = rng.sample(regions, k) if k else regions
    tally = Counter()
    begun = time.time()
    disagree = checked = 0
    for i, (cells, root) in enumerate(picks):
        top = highest(cells, root)
        tally[top] += 1
        if k and i % 25 == 0:
            for count in (top, top + 1):
                if 1 <= count <= 8:
                    nine = next((x for x in cells if x[0] == ROW and x != root), None)
                    fixed = {root: count, **({nine: 9} if nine else {})}
                    checked += 1
                    disagree += holds(cells, root, count, lines_of(cells)) != region_holds(sorted(cells), count, fixed)
        if i % 20000 == 19999:
            print(f"{i + 1} done, {time.time() - begun:.0f}s, {sorted(tally.items())}", flush=True)
    print(f"highest count: {sorted(tally.items())} of {len(picks)} in {time.time() - begun:.1f}s", flush=True)
    if k:
        print(f"solver cross-check: {checked} checks, {disagree} disagree", flush=True)


if __name__ == "__main__":
    main(Path(sys.argv[1]), int(sys.argv[2]))
