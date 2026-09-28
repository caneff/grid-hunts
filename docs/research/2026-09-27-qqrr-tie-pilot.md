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

**Probe** (`2026-09-27-qqrr-tie-pilot/probe-model.py`, 1 CP-SAT worker, 120 s cap,
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
