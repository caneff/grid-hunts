"""Exhaustive fourth-line search: every orthogonal path of TARGET's length.

Usage: uv run find_l4_all.py board.json FIXED_A,FIXED_B TARGET log.txt [--count]
Pairs FIXED_A with FIXED_B, TARGET with each candidate L4, logs one line per candidate.
Candidates keep only segment structures the geometry-free segment model
(segment_openers.line_multisets) can pair with TARGET's structure.
"""

import json
import sys
import time
from collections import Counter
from itertools import permutations
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from copycat_rsl_solver import Collector, build, segments
from ortools.sat.python import cp_model
from segment_openers import line_multisets, partitions

BASE, FIXED, TARGET, LOGPATH = (
    sys.argv[1],
    sys.argv[2].split(","),
    sys.argv[3],
    sys.argv[4],
)
base = json.loads(Path(BASE).read_text())
used = {
    (int(c[1]) - 1, int(c[3]) - 1) for cells in base["lines"].values() for c in cells
}
target_cells = [(int(c[1]) - 1, int(c[3]) - 1) for c in base["lines"][TARGET]]
LENGTH = len(target_cells)
target_struct = tuple(len(s) for s in segments(target_cells))


def pairable(a: tuple[int, ...], b: tuple[int, ...]) -> bool:
    """Can structures a and b share a value multiset in the segment model?"""
    for s_a in range(3, 46):
        if (len(a) * s_a) % len(b):
            continue
        s_b = len(a) * s_a // len(b)
        if set(line_multisets(a, s_a)) & set(line_multisets(b, s_b)):
            return True
    return False


OK = {
    perm
    for part in partitions(LENGTH)
    if len(part) >= 2 and pairable(tuple(sorted(target_struct)), part)
    for perm in set(permutations(part))
}

paths = set()


def grow(path):
    if len(path) == LENGTH:
        key = min(tuple(path), tuple(reversed(path)))
        paths.add(key)
        return
    r, c = path[-1]
    for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        n = (r + dr, c + dc)
        if 0 <= n[0] < 9 and 0 <= n[1] < 9 and n not in used and n not in path:
            grow([*path, n])


for r in range(9):
    for c in range(9):
        if (r, c) not in used:
            grow([(r, c)])
cands = {p: tuple(len(s) for s in segments(list(p))) for p in paths}
cands = {p: st for p, st in cands.items() if st in OK}
print(
    f"target {TARGET} {target_struct} length {LENGTH}; partner structures {sorted(OK)}",
    flush=True,
)
print(
    f"{len(paths)} paths, {len(cands)} with allowed structure",
    Counter(cands.values()),
    flush=True,
)
if "--count" in sys.argv:
    sys.exit()
LIMIT = 2
LOG = Path(LOGPATH)
for i, (p, st) in enumerate(sorted(cands.items())):
    cells = [f"r{r + 1}c{c + 1}" for r, c in p]
    setup = {
        "lines": dict(base["lines"], L4=cells),
        "pairs": [FIXED, [TARGET, "L4"]],
    }
    m, digit, cc, lines = build(setup)
    solver = cp_model.CpSolver()
    solver.parameters.num_search_workers = 1
    solver.parameters.enumerate_all_solutions = True
    solver.parameters.max_time_in_seconds = 60
    col = Collector(digit, cc, LIMIT)
    t = time.time()
    s = solver.Solve(m, col)
    n = len(col.solutions)
    tag = (
        "UNKNOWN"
        if s == cp_model.UNKNOWN and n == 0
        else ("FEASIBLE" if n else "infeasible")
    )
    with LOG.open("a") as out:
        print(
            f"{i + 1}/{len(cands)} {tag} {time.time() - t:.1f}s {st} {'-'.join(cells)}",
            file=out,
        )
with LOG.open("a") as out:
    print("DONE", file=out)
