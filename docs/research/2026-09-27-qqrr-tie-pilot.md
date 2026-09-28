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
