# qqrr tie pilot on the shared hunt protocol (#491)

**Result: the pilot ran end to end and found no grid.** 3 seeds, all empty,
reason `timeout`.

**Run.** `finders/qqrr/hunt/tie_finder.py --out docs/research/2026-09-27-qqrr-tie-pilot
--seeds 0:3 --workers 3 --hunt r1c5 --ten r7c7 --corner tr --timeout 900 --q34`
under `job-run --name qqrr-tie-pilot-491`, 10:30–11:15 on 2026-09-27, at
`29bcbc0`. The review fixes after that sha change no solve path (a `--ten`
check, the infeasible reason's wording, a dropped class default).

**Output directory** (`2026-09-27-qqrr-tie-pilot/`, the driver's standard
layout; `.lock` not committed):

| file | content |
|---|---|
| `run.json` | argv, the finder's config (`hunt r1c5`, `ten r7c7`, `corner tr`, `timeout 900`, `q34`), git sha |
| `progress.jsonl` | seeds 0, 1, 2: `empty`, `empty_reason: timeout` |
| `summary.json` | 3 seeds, 0 examples, 3 empty |
| `examples.jsonl` | empty |
| `state.json` | no grid forbidden yet |

**What it does and does not say.** Every seed hit the 900 s cap, so this is
no proof: a timeout, not infeasibility. The same block (cage r1c5, QR 10 at
r7c7, top-right, 34–36 criterion) gave 5 grids in 29 minutes in the 34–36
hunt (`2026-09-22-qqrr-tie-r5c1.md`). That run had 6 workers, one solve of 30
minutes, and a warm start from an earlier qualifying grid. This one had 3
workers, 15-minute solves, and the hunt's seed grid as its only hint. The
example-writing path was not exercised by a real grid in this run; the
finder's `verify` and `record` are covered by `test_tie_finder.py` on a grid
the 34–36 hunt found.

More seeds need a new `--out`: `--seeds` is part of the resume key, so this
directory resumes only the range 0:3.

## Why no grid: the model is sound, the start was cold (2026-09-28)

**Probe** (the script below, run from `.scratch/` as `uv run .scratch/probe-491-model.py`; 1 CP-SAT worker, 120 s cap,
at `e703a1b`): the three known r1c5 / r7c7 / tr grids that pass the 34–36
criterion (`654781392/…`, from the 34–36 hunt in `2026-09-22-qqrr-tie-r5c1.md`),
run against `tie_finder.py`'s own code.

| check | grid 0 | grid 1 | grid 2 |
|---|---|---|---|
| `TieFinder.verify` (oracle) | ok | ok | ok |
| pilot model (`tables`, `hint`, `criteria=q34`), every cell pinned to the grid | OPTIMAL, 0.1 s | OPTIMAL, 0.1 s | OPTIMAL, 0.1 s |

The pilot's model admits every known answer, so the empty run is not a model
bug. The same model hinted with grid 0 instead of the hunt's seed grid solved
in **2.2 s on 1 worker** and returned grid 0. The pilot had 3 workers × 900 s
× 3 seeds from the seed-grid hint and found nothing.

What this does and does not say: the hint was the answer itself, so 2.2 s is
an upper bound on what a warm start buys. The 2026-09-22 hunt warm-started
from the *nearest earlier* hit of the same hunt, a different grid, and found
5 grids in 29 min with 6 workers. The missing piece in the pilot is
`chan_big.py`'s `warm` flag, which `tie_finder.py` did not port (#491 P1,
accepted by Chris "for now").

The probe script (kept here as text: a `.py` under `docs/research/` fails `check_layout.py`):

```python
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

ROOT = Path(__file__).resolve().parents[1]
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
    got = tf.hc.grid_text(tf.grid_rows(tuple(s.Value(q.x[r][c]) for r in range(N) for c in range(N))))
print(f"C hinted with grid 0 -> {status} in {secs} s {got}", flush=True)
```

## Warm-start demonstration (#643, 2026-10-03)

**Outcome, 3 seeds: 0 found, 3 timed out, 0 proven infeasible.** A capped
empty run is not a proof, and this one says nothing about whether a grid exists.
It shows that `--warm-from` runs end to end and that, at this cap, warming from
the r1c5 grids of other corners and windows (same hunt, not this block's own) did not
reproduce the 2026-09-22 find.

**Run.** `finders/qqrr/hunt/tie_finder.py --out docs/research/2026-10-03-qqrr-tie-warm-demo
--seeds 0:3 --workers 1 --hunt r1c5 --ten r7c7 --corner tr --timeout 300 --q34
--warm-from docs/research/2026-10-03-qqrr-tie-warm-source`, under
`job-run --name qqrr-tie-warm-643`, 1 worker, 3 × 300 s, started 14:20 UTC at
`604b4ea` (the commit before the README edit; no solve path differs).

**Warm source** (`2026-10-03-qqrr-tie-warm-source/examples.jsonl`): the 8 r1c5
grids of `2026-09-22-qqrr-tie-r5c1.md` § Big channelled finder, cage at r1c5,
*minus* the r7c7 / tr answers (the first tr grid and the 518 s one). It holds
no grid for the block being searched. The nearest grid is the r7c7 / br #2
grid (`645781329/…`: same window, other corner, and it passes the 34–36
criterion), recorded in the demo's `run.json` under `config.warm_from`.

**Against the pilot.** Same block, same criterion; the pilot had 3 workers ×
900 s with the seed-grid hint. This run had 1 worker × 300 s, so it is a third
of the pilot's time per seed on a third of the workers. It is a weaker budget
than either earlier run, not a like-for-like comparison. The 2026-09-22 hunt
that found 5 grids used 6 workers and 30-minute solves.

Not tried (each is a new launch, left for the owner to rule on): the pilot's
3 workers × 900 s with `--warm-from`; the hint from a grid of the block itself
(the 2.2 s probe above, an upper bound only).

Output: `2026-10-03-qqrr-tie-warm-demo/` (`.lock` not committed).
