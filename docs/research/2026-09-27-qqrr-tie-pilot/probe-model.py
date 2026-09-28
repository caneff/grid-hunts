"""Probe (#491 pilot, burn-2026-09-27): do the known r1c5 / r7c7 / tr / q34
grids from the 2026-09-22 hunt satisfy the pilot's own model?

A: tie_finder.TieFinder.verify (oracle) on each known grid.
B: the pilot's model (flags tables, hint, criteria=q34) with every cell pinned
   to the grid -- feasible means the model admits it.
C: the same model with the grid as a hint only (a warm start), no pin.
1 CP-SAT worker, 120 s cap per solve.
"""
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "finders" / "qqrr" / "hunt"))
sys.path.insert(0, str(ROOT))

import tie_finder as tf  # noqa: E402

from examples._shared import cpsat  # noqa: E402

GRIDS = [
    "654781392/987234516/123956847/218679453/539842761/476513928/745168239/391427685/862395174",
    "654781392/987234516/123956847/218679453/539842761/746513928/475168239/391427685/862395174",
    "654781392/987263514/123459768/215697843/376814925/498532671/549178236/761325489/832946157",
]
N = tf.N
HUNT, TEN, CORNER = "r1c5", "r7c7", "tr"
CAP = 120


def model(hint=None):
    q, _, _ = tf.chan_big.build(HUNT, TEN, CORNER, {"tables", "hint", "criteria=q34"})
    if hint:
        q.m.ClearHints()
        for r, row in enumerate(hint.split("/")):
            for c, d in enumerate(row):
                q.m.AddHint(q.x[r][c], int(d))
    return q


def solve(q):
    s = cpsat.solver(CAP, reproducible=True, seed=0)
    s.parameters.num_workers = 1
    t = time.time()
    res = s.Solve(q.m)
    return s.StatusName(res), round(time.time() - t, 1), s, q


finder = tf.TieFinder(HUNT, TEN, CORNER, CAP, True)
for i, g in enumerate(GRIDS):
    flat = tuple(int(d) for d in g.replace("/", ""))
    print(f"grid {i}: A verify -> {finder.verify(tf.Candidate(flat, HUNT, TEN, CORNER, True))}", flush=True)
    q = model()
    for r, row in enumerate(g.split("/")):
        for c, d in enumerate(row):
            q.m.Add(q.x[r][c] == int(d))
    status, secs, _, _ = solve(q)
    print(f"grid {i}: B pinned -> {status} in {secs} s", flush=True)

status, secs, s, q = solve(model(hint=GRIDS[0]))
got = ""
if status in ("OPTIMAL", "FEASIBLE"):
    got = tf.grid_text(tuple(s.Value(q.x[r][c]) for r in range(N) for c in range(N)))
print(f"C hinted with grid 0 -> {status} in {secs} s {got}", flush=True)
