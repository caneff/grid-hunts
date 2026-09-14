import json
import sys
import time
from collections import Counter
from pathlib import Path

sys.path.insert(0, "docs/research/2026-09-14-galaxy-copycat")
from copycat_rsl_solver import Collector, build, segments
from ortools.sat.python import cp_model

base = json.loads(
    Path(
        "docs/research/2026-09-14-galaxy-copycat/boards/board1-three-lines.json"
    ).read_text()
)
used = {
    (int(c[1]) - 1, int(c[3]) - 1) for cells in base["lines"].values() for c in cells
}
OK = {(2, 4), (4, 2), (3, 3), (1, 1, 4), (1, 4, 1), (4, 1, 1)}

paths = set()


def grow(path):
    if len(path) == 6:
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
    f"{len(paths)} paths, {len(cands)} with allowed structure",
    Counter(cands.values()),
    flush=True,
)
if "--count" in sys.argv:
    sys.exit()
LIMIT = 2
LOG = Path("docs/research/2026-09-14-galaxy-copycat/boards/board1-l4-search.log")
for i, (p, st) in enumerate(sorted(cands.items())):
    cells = [f"r{r + 1}c{c + 1}" for r, c in p]
    setup = {
        "lines": dict(base["lines"], L4=cells),
        "pairs": [["L2", "L3"], ["L1", "L4"]],
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
