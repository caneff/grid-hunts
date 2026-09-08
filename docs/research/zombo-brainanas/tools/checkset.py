"""Is one found fill the unique solution under a given clue set (circles + white dots)?
usage: checkset.py <found name> <clue> ... where clue = r6c8 (circle) or r3c2-r3c3 (white dot). Prints UNIQUE or the second solution."""

import json
import os
import sys
import time

sys.path.insert(
    0, "/home/caneff/orca/workspaces/sudokumaker-custom-constraints/tang/docs/research"
)
import zombo_brainanas_cpsat as zb

F = "/home/caneff/orca/workspaces/sudokumaker-custom-constraints/tang/docs/research/zombo-brainanas/found/"
name = sys.argv[1]
clues = sys.argv[2:]
limit = int(os.environ.get("LIMIT", 600))
zb.WORKERS = int(os.environ.get("ZB_WORKERS", zb.WORKERS))
zb.BIG_POCKET_CELLS = None
d = json.load(open(F + name + ".json"))
sol = {(r, c): int(d["grid"][r][c]) for r in range(9) for c in range(9)}
shade = {(r, c): int(d["infected"][r][c] == "*") for r in range(9) for c in range(9)}
cell = lambda s: (int(s[1]) - 1, int(s[3]) - 1)
circles = {cell(s): None for s in clues if "-" not in s}
whites = [tuple(cell(t) for t in s.split("-")) for s in clues if "-" in s]
for p in circles:
    assert p in zb.circle_candidates(sol, shade), (
        f"{p} is not a valid circle on this fill"
    )
for p, q in whites:
    assert not shade[p] and not shade[q] and abs(sol[p] - sol[q]) == 1, (
        f"bad white dot {p}-{q}"
    )
_build = zb.build


def build(*a, **k):
    m, x, inf = _build(*a, **k)
    for p, q in whites:
        m.Add(inf[p] == 0)
        m.Add(inf[q] == 0)
        e = m.NewBoolVar("")
        m.Add(x[p] - x[q] == 1).OnlyEnforceIf(e)
        m.Add(x[q] - x[p] == 1).OnlyEnforceIf(e.Not())
    return m, x, inf


zb.build = build
t = time.time()
try:
    other = zb.solve_valid(circles=circles, cuts=[], exclude=[sol], limit=limit)
except TimeoutError:
    print(f"TIMEOUT after {limit}s")
    sys.exit(2)
print(f"{'UNIQUE' if other is None else 'SECOND SOLUTION'} ({time.time() - t:.0f}s)")
if other is not None:
    g, inf = other
    for r in range(9):
        print(
            "".join(str(g[(r, c)]) for c in range(9)),
            "".join("*" if inf[(r, c)] else "." for c in range(9)),
        )
