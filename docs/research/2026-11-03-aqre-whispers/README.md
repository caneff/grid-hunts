# Aqre shading with 5-whispers: feasibility, 2026-11-03

Chris's idea: a 9x9 sudoku with Aqre shading (shaded cells one orthogonally
connected group, no 4 in a line of one colour in a row or column) and 5-whispers
(orthogonally adjacent cells differ by at least 5). A circle's digit is the
number of shaded cells in its 3x3 box, the standard Aqre count. The scripts here
are scratch models, not finders: the repo has no Aqre model. Each solve ran on
one CP-SAT worker.

## Results

No solve timed out.

| Whispers on | Digits | Box counts | Result | Time |
|---|---|---|---|---|
| unshaded pairs | 1-9 | free | found, `grid-1.json` | 0.2 s |
| shaded pairs | 1-9 | free | found, `grid-2.json` | 72.1 s |
| shaded pairs | 0-8 | free (the control) | found; no rule broken | 20.4 s |
| none, no digits | none | all different, 0-8 | found (shape only) | 14.0 s |
| shaded pairs | 0-8 | all different, 0-8 | **proven infeasible**, first model | 187.8 s |
| shaded pairs | 0-8 | all different, 0-8 | **proven infeasible**, second model | 167.0 s |

So nine circles with nine different values, one per box, cannot exist under
those rules with 0-8 digits. The shading rules alone allow counts 0 to 8, so the
digits and shaded whispers are what rule it out. No hand proof is written yet.

The two infeasible models share no encoding: `aqre_disjoint_feasible.py` uses
integer digits, an orientation variable, flow connectivity and a redundant total
of 36; `aqre_disjoint_recheck.py` uses one-hot digits, whispers as clauses,
level-based connectivity and one-hot box counts. Both run on CP-SAT, so a CP-SAT
bug would reach both.

With unshaded whispers the first grid has only 5 adjacent unshaded pairs, so
that rule barely constrains it. That is one grid, not a bound.

## What the shaded-whisper rules force

By hand, and `grid-2.json` agrees:

- The shaded group alternates: one checkerboard colour of shaded cells is all
  low and the other all high.
- The middle digit (5 in 1-9, 4 in 0-8) is never shaded.
- A house holds at most 8 shaded cells.
- A digit on the wrong checkerboard colour for the orientation must be unshaded.
- Swapping `d` for its mirror digit flips the orientation only without circles:
  the swap changes a circled digit but not its box count.

## Rulings

- Circles count shaded cells in their box, and Chris wants "9 circles with
  different values", placed anywhere (2026-11-03). Regions are the 3x3 boxes.
- 0-8 was Chris's ask for this variant; whether digits stay 0-8 is open.
- Not tested: uniqueness, or any variant in the table's open cases.

## Rebuild

From the repo root, each with the folder holding these scripts on the path:

    PYTHONPATH=.:finders/counting_shaded:docs/research/2026-11-03-aqre-whispers \
      uv run python docs/research/2026-11-03-aqre-whispers/aqre_disjoint_recheck.py

`aqre_whispers_feasible.py DIR` and `aqre_shaded_whispers_feasible.py DIR` wrote
`grid-1` and `grid-2`; `aqre_disjoint_feasible.py DIR` is the first infeasible
solve.
