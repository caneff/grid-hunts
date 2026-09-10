"""The canonical key must hold up on every grid in the pool.

Three claims, all falsifiable against the pool and the independent checker:

1. Every dihedral image of a legal grid is itself legal -- if not, the group is
   wrong and the key would merge grids that are not the same puzzle.
2. All eight images of one grid share one key.
Duplicates across pools are reported, not failed. A pool records what one hunt
found, and two hunts finding the same puzzle is a fact worth keeping -- it is
the lineup, not the pools, that must show each puzzle once.

    uv run docs/research/renbanana/tools/test_canon.py
"""

import json
import sys
from itertools import combinations
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import canon
import renbanana_verify as rv

ok = True
seen = {}
paths = sorted(Path("docs/research/renbanana").glob("candidates*/cand_*.json"))
for path in paths:
    grid, is_choc, _ = rv.load(path)
    keys = set()
    for g, s in canon.images(grid, is_choc):
        bad = rv.check(g, s)
        if bad:
            ok = False
            print(f"{path}: an image is ILLEGAL — {bad[0]}")
        keys.add(canon.key(g, s))
    if len(keys) != 1:
        ok = False
        print(f"{path}: its images disagree on the key ({len(keys)} keys)")
    k = keys.pop()
    if k in seen:
        print(f"note: {path} is the same puzzle as {seen[k]}")
    else:
        seen[k] = path

print(f"{len(paths)} grids, {len(seen)} distinct puzzles")

# The geometry group, which is what lets a harvest solve one placement per
# orbit instead of all eight. Two things have to hold: a geometry and its
# images must agree on the key, or the reduction would split an orbit; and
# every grid already found must have its own geometry inside the reduced set,
# or the reduction is dropping questions that have answers.
WANTED = {(2, 2), (2, 3), (3, 2)}
feasible = [
    json.loads(line)["pair"]
    for line in Path("docs/research/renbanana/circled-pairs-all/pairs.jsonl")
    .read_text()
    .splitlines()
    if line.strip() and json.loads(line)["grid"] is not None
]
orbits = {canon.geometry_key([tuple(x) for x in pair]) for pair in feasible}
print(f"{len(feasible)} sudoku-feasible geometries, {len(orbits)} orbits")

for pair in feasible[:200]:
    pair = [tuple(x) for x in pair]
    per = [canon.place_images(x) for x in pair]
    if len({canon.geometry_key([im[i] for im in per]) for i in range(8)}) != 1:
        ok = False
        print(f"{pair}: its images disagree on the geometry key")

for path in paths:
    if path.parent.name != "candidates-two-circles":
        continue
    grid, is_choc, _ = rv.load(path)
    places = []
    for group in rv.components(is_choc, True):
        if not rv.is_rectangle(group):
            continue
        a, b, r0, c0 = canon._bbox(list(group))
        if (a, b) in WANTED and any(grid[q] == a * b for q in group):
            places.append((a, b, r0, c0))
    if not any(
        canon.geometry_key(list(combo)) in orbits
        for combo in combinations(sorted(places), 2)
    ):
        ok = False
        print(f"{path}: its geometry is not in the reduced set")

print("PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)
