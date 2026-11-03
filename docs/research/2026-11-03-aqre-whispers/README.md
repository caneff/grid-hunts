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
digits and shaded whispers are what rule it out.

## Why: no box holds 8 whisper cells

Chris's proof, 2026-11-03. Take 0-8 digits and a gap of 5. A count of 8 leaves
only the box's 4 unshaded, because 4 has no partner. The 3 pairs only with 8 and
the 5 only with 0, so each may have one shaded neighbour at most, and each is
shaded with at least 2 shaded neighbours in the box. The box's checkerboard
colours show why: its 4 corners and centre cannot all be shaded (four digits per
side), so the 4 is on that colour and every edge cell is shaded.

An enumeration of one box alone agrees: at a gap of 5, 0 of 9 layouts work with
8 whisper cells and 32 of 36 with 7. At a gap of 4, 9 of 9 work with 8 and none
with 9. That box check is necessary only; it does not show a whole grid exists.

Consequences at a gap of 5, the same in 1-9 digits by shifting:

- Whispers on shaded cells: a box count is at most 7, so at most 8 different
  values (0-7, needing 0-8 digits) and 7 with 1-9 digits.
- Whispers on unshaded cells: at most 7 unshaded per box, so a count is at
  least 2, and at most 8 different values (2-9).
- Nine different values therefore need a gap below 5.

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

## Four circles in a 2x2 where four boxes meet

Chris's ask, 2026-11-03: back to 1-9 digits with 5-whispers on shaded cells and
no "all different" rule; four circles fill a 2x2 across a box crossing, and every
box holds a valid circle because every box has a shaded cell. The four crossings
are one case under reflection.

Found, `grid-4.json`, in 8.6 s after a warm start from a solve of the four boxes
alone (`aqre_crossing_circles.py DIR`). The circles are r3c3=4, r3c4=6, r4c3=2 and
r4c4=4, and the separate reader found no rule broken. The first attempt, without
the warm start or the every-box rule, ended UNKNOWN at 300 s, which proves nothing.

Not tested: uniqueness.

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
