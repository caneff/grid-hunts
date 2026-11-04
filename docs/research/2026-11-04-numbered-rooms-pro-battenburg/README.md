# Numbered Rooms with enterable outside digits, pro-Battenburg on targets

Decision log. The scripts here are scratch: the repo has no Numbered Rooms
model, and nothing imports or runs them.

## The rule

- Normal 9x9 sudoku.
- 36 enterable outside cells, one at each end of each row and column. Corners
  stay empty.
- Each outside digit is the digit in its **target**: the Nth cell from that
  edge, where N is the digit in the first cell. This is the standard Numbered
  Rooms rule ([Logic Masters](https://logic-masters.de/Raetselportal/Raetsel/zeigen.php?chlang=en&id=0003CH)).
- A cell is a target or it is not. A cell targeted twice counts once.
- A **window**, a 2x2 inside the 9x9, is marked exactly when its four cells are
  a checkerboard of target and not target. No window reaches outside the 9x9.

## Rulings (Chris, 2026-11-04)

- "Pro-Battenburg" means all marked: a window is marked exactly when it is a
  checkerboard, the published Battenburg convention ([Logic Masters](https://logic-masters.de/Raetselportal/Raetsel/zeigen.php?chlang=en&id=00027F)).
- Goals, in order: (a) any valid grid, (b) a unique puzzle with the fewest given
  outside digits, (c) a unique puzzle from the marks alone.

## Preflight

1. **Known bounds.** The 17-givens bound does not apply: marks and outside
   digits carry information it does not count.
2. **Corpus.** Random grids come from shuffled backtracking in `nr.py`, which is
   not uniform over sudoku grids. Counts below describe that sampler only.
3. **Orbit.** The D4 symmetries of the board keep the rule. Relabelling digits
   does not, because digits are positions.
4. **Lessons contradicted.** None known.
5. **Artefact control.** `nr_selfcheck.py` checks the model against the reader,
   and refuses a flipped mark and a wrong outside digit on 40 random grids.
6. **Oracle.** Each uniqueness answer is a CP-SAT solve, not a sample statistic.
7. **Necessary conditions.** See below.

## What the rules force

- **Every window a checkerboard is impossible.** The targets would be one whole
  parity colouring, 40 or 41 cells, and 36 clues reach at most 36 cells.
- **At most 36 targets.** `nr_target_bounds.py` found a grid with 36, so 36 is
  exact.
- **At least 9 targets.** The left clues alone reach 9 different rows. The
  fewest found is 11, in a 90 s run that timed out, so the minimum is 9, 10 or 11.
- **Exactly 4 clues reach each row and each column, so each holds 1 to 4
  targets.** A row gets its own left and right clues, one top clue (the top row
  holds the row's position digit once) and one bottom clue. Columns are the same
  by symmetry. A count of 36 targets therefore means exactly 4 in every line.
- **Marks use up a line's 4 targets (Chris, 2026-11-04).** A marked window has
  exactly one target in each of its two rows and two columns. So k disjoint marks
  on a line leave at most 4 - k targets in its other cells, and 4 disjoint marks
  mean the ninth cell is not a target. On 5,000 random grids, 162 lines had 4
  disjoint marks and no ninth cell was a target. A full run of 8 overlapping marks
  across a line forces targets onto positions 2, 4, 6 and 8, since the other
  alternation needs 5.
- **The marks read only the 32 edge cells.** Targets depend only on first-cell
  digits, so two grids with equal edges have equal targets and equal marks.
- **Goal (c) needs a grid fixed by its own edge.** A grid whose 32 edge cells
  allow a second completion has a second solution with the same marks.

## Runs

- **Reader on 2,000 random grids (seed 1):** targets 23 to 36, mean 30.2; marks 1
  to 27, mean 10.1.
- **Exact minimum, `min_outside_givens`:** too slow as a first pass. On seeds 0 to
  4 the first version stopped at its 400-round cap, or found no separation. The
  version with shrunken counterexamples finished no grid in 280 s.
- **Greedy upper bound, `nr_greedy.py`, seeds 0 to 7, one order:** 3 of 8 grids
  are separable, with 13, 9 and 10 givens. The other 5 have a second grid with
  the same marks and all 36 outside digits.

- **Greedy survey, seeds 0 to 399, 5 orders each, `greedy-survey.jsonl`:** 223
  separable, 177 not separable, no solve timed out. Smallest set per separable
  grid: 5 (1 grid), 6 (7), 7 (30), 8 (44), 9 (37), 10 (41), 11 (29), 12 (22), 13
  (10), 14 (1), 15 (1). These are upper bounds per grid, not minimums. Seed 328
  needs at most 5.
- **Climb, `nr_climb.py`, `climb.jsonl`:** the moves are digit, line and block
  swaps and row or column cycle swaps. It starts from the six smallest survey
  grids. 894 evaluations in 1,203 s found no greedy set below 5, and 17 records at
  5, which are 15 distinct grids. This is a sampled run, so 5 is no floor over
  all grids.
- **Exact check, `nr_exact.py`, `exact.jsonl`:** on all 15 grids every 4-subset of
  the 36 outside cells fails, so 5 is the proven minimum for each of those grids
  with their marks. None timed out. A new grid could still need fewer. Each grid
  has more than 200 grids with the same marks (count capped at 201).
- **Independent proof, `nr_verify_sat.py`:** PySAT, sharing no code with `nr.py`,
  confirms the grid below is unique with its 5 givens and finds a second grid
  when `B5` is dropped.
- **Edge completions, `nr_edge_rate.py`:** all 200 random grids (seed 3) have
  more than 50 completions of their edge (capped).

- **Edge climb, `nr_edge_climb.py`, `edge-climb.jsonl`:** 4,572 evaluations in six
  900 s-budget climbs, counts capped at 20,000. Five climbs ended at the cap, and
  the best grid has 19,105 completions. The capped score gives the climb no
  gradient, so this says little about what exists.
- **Edge search, `nr_edge_cegar.py`:** 2,470 rounds on PySAT, forbidding each
  minimal interior rearrangement, with its symmetric images and digit
  relabellings. It stopped at its 3,000,001-clause limit after about 203 s,
  neither finding a grid fixed by its edge nor proving none exists. This
  proves nothing. The patterns stayed at 6 to 30 cells.

## Step (c)

None found, and not proven impossible. No grid fixed by its own edge turned up,
and marks-alone uniqueness needs one. All 15 grids in `exact.jsonl` have more than
200 grids with the same marks. Stopped here on 2026-11-04.

## Best puzzle so far, step (b)

13 marks, 5 given outside digits, unique:

```text
863479125
924158367
715326894
192685473
647931582
358247619
239814756
586793241
471562938
```

Givens: `L5=1`, `L8=9`, `R7=8`, `T4=6`, `B5=8`. L and R count rows from the top;
T and B count columns from the left. Marks, as the top-left cell of each window,
row and column from 0: (1,6), (2,0), (2,2), (2,4), (3,4), (3,5), (3,6), (4,2),
(5,2), (6,0), (6,7), (7,0), (7,3).

### Link

https://sudokumaker.app/p/j8BWkCggcK

Built by `build_link.py` from `link_template.json`, with all 36 outside cells
outlined and no solution digit entered. The marks are cosmetic text, so the app's
solver does not read them and will not confirm uniqueness. The proof is
`nr_verify_sat.py`. The rendered page was checked by screenshot.

## Step (a)

Under the all-marked ruling every sudoku grid is valid: it has exactly one set of
targets, outside digits and marks. Any grid above answers (a).
