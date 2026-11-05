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
- **At least 10 targets.** Eight lines of one direction hold at least 1 each and
  the middle one at least 2 (below). The fewest found is 11, in a 90 s run that
  timed out, so the minimum is 10 or 11.
- **Exactly 4 clues reach each row and each column, so each holds at most 4
  targets.** A row gets its own left and right clues, one top clue (the top row
  holds the row's position digit once) and one bottom clue. Columns are the same
  by symmetry. A count of 36 targets therefore means exactly 4 in every line.
- **The fewest in a line is 1, except r5 and c5, which hold at least 2**
  (`nr_unit_minimums.py`, all proven optimal, rows 1 to 5 covering all 18 lines by
  symmetry). r5's top clue sits in the column where r1 = 5 and its bottom clue in
  the column where r9 = 5. A column holds one 5, so they hit different cells.
- **A box can hold 0 targets** (same script, proven for the corner, edge and centre
  box, each grid re-read by the reader, so all nine boxes by symmetry).
- **Marks use up a line's 4 targets (Chris, 2026-11-04).** A marked window has
  exactly one target in each of its two rows and two columns. So k disjoint marks
  on a line leave at most 4 - k targets in its other cells, and 4 disjoint marks
  mean the ninth cell is not a target. On 5,000 random grids, 162 lines had 4
  disjoint marks and no ninth cell was a target. A full run of 8 overlapping marks
  across a row pair is impossible: the two rows are complements, so together they
  hold 9 targets and one has 5 (`nr_force_shapes.py`, infeasible). This corrects an
  earlier claim here that such a run forces positions 2, 4, 6 and 8. A run of 7 is
  feasible.
- **A box can hold 9 targets.** `nr_box_bounds.py` found a grid for the corner,
  edge and centre box, each re-read by the reader, so all nine boxes reach it by
  symmetry.
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

Two more necessary conditions, by hand (2026-11-05). The mark set can have no
left-right, up-down or rotation symmetry: the moved grid would have the same marks, and
no sudoku grid equals its own such image, since r1 or r5 or c5 would repeat a digit.
Diagonal symmetry is not excluded this way, because a grid can equal its own transpose.
And 64 windows give at most 2^64, about 1.8e19, mark sets against about
6.67e21 sudoku grids, so at most about 0.3% of grids could be unique from marks alone.
Neither rules out one such grid.

## A grid with 36 targets

`nr_full_targets.py`, read back by the reader: 4 targets in every row and column, 13
marks at r1c1, r1c7, r2c1, r2c3, r3c5, r4c1, r4c2, r5c4, r5c5, r6c6, r7c2, r8c3, r8c8.
Grid 621483759/359721684/487596321/168942537/593617248/274835916/915378462/846259173/
732164895. Picture `full-targets-1.png`.

Those 13 marks alone, negative rule on, have exactly 7,669,122 solutions, spread over
32 borders with 34,849 to 617,449 fillings each. `nr_full_targets_edges.py` enumerated
the borders to OPTIMAL, `count_fills.c` counted each exactly. `nr_full_targets_check.py`
confirmed on the repo model that forbidding all 32 borders is infeasible, and that each
border's first 30 fillings exist and re-read to exactly these marks. The fill counts
above 30 rest on `count_fills.c` alone, a solver-free count.

Forced across all those solutions (`nr_full_targets_forced.py`, read from the
per-cell digits `count_fills.c` records): no digit in any cell and no outside digit.
Target status is fixed for 36 cells. 12 are always targets: r1c1, r2c2, r2c3, r3c1,
r3c4, r4c1, r4c3, r4c4, r5c2, r7c2, r8c3, r9c4. 24 are never targets. The other 45 are
open. Tightest options: r4c1 is 1 or 4, r9c2 is 3 or 8, outside B9 is 1, 2 or 8.

A 36-target grid whose marks alone fix every target (`nr_t36_climb.py`, seed 1, at least
18 marks, `t36-hits.jsonl`, picture `full-targets-2.png`): 27 marks at r1c2 r1c6 r2c2 r3c2
r3c7 r3c8 r4c8 r5c1 r5c5 r5c8 r6c3 r6c4 r6c5 r6c8 r7c2 r7c3 r7c4 r7c5 r7c6 r7c7 r7c8 r8c3
r8c4 r8c5 r8c6 r8c7 r8c8, negative rule on, no givens. Grid 918732456/465819327/273456819/
346578291/187294563/529361748/851927634/792643185/634185972. On the repo's full model,
forbidding its target set is infeasible, so every solution has these 36 targets. The marks
allow 2 borders on the border-only model. Hits came within 4 evaluations, so this is not
rare at this density. It says nothing about the fewest marks that can do it, and there is
no hand path yet. Not unique as a puzzle.

Link, no givens (`build_link_t36.py`):

https://sudokumaker.app/p/hWHLr9dQzw

Chris's solve state on that board (2026-11-05, all correct against the grid) was traced by
`nr_t36_next.py`, which applies simple rules and tries each open fact one step ahead.
Short steps: r4 holds r4c7, r4c9 and one of r4c2/r4c3, so at most one of r4c1 and r4c4 is
a target. r1c1 = 2 fails in 6 steps through unmarked window r1c1 and mark r1c2. A line with
4 known targets takes each clue on a different cell, so r5 to r8 have first digit + last
digit != 10, and so do c2, c3, c6, c7 and c8 between r1 and r9. Beyond those, the next
forced facts, r1c1 not a target (68 steps) and r4c1 a target (78 steps), were long chains,
and the tracer stalled with 18 cells open. This is evidence that the board is hard by hand
from there, not proof: the tracer knows only these rules.

**Correction (Chris, 2026-11-05): "just by Battenburg" means no digits at all.** The 27-mark
board's proof above used all the Numbered Rooms and sudoku rules. On marks, the negative
rule and 1 to 4 targets per line alone it allows 424 patterns with 21 cells open
(`nr_t36_pure.py check`). Under this meaning a 32-mark board has exactly one pattern, with
36 targets, by complete enumeration, and the grid behind it is confirmed by the reader
(`nr_t36_pure.py`, seed 5, `t36-pure.jsonl`): r1c1 r1c4 r1c5 r1c6 r2c2 r2c3 r2c4 r2c5 r2c6
r2c7 r2c8 r3c4 r4c1 r4c4 r4c6 r4c7 r5c1 r5c4 r5c8 r6c1 r6c2 r6c3 r6c4 r6c5 r7c5 r7c8 r8c1
r8c2 r8c3 r8c6 r8c7 r8c8. Grid 724615389/819243576/536789241/452391768/173864952/968527134/
381976425/695432817/247158693. Link, no givens (`build_link_t36.py`):

https://sudokumaker.app/p/7mdPh6wG98

Fewer marks under the same no-digit rules (`nr_t36_pure_fewer.py`, seed 7, 900 s,
`t36-pure-fewer.jsonl`, picture `full-targets-3.png`): 25 marks, exactly one pattern with
36 targets, rechecked by a separate enumeration: r1c1 r1c3 r1c4 r1c8 r2c6 r2c8 r3c2 r3c4 r3c5
r3c6 r3c8 r4c4 r4c5 r5c1 r5c2 r5c3 r5c7 r6c5 r6c8 r7c1 r7c2 r8c1 r8c4 r8c5 r8c7. Grid
286319547/751248396/349675821/512984673/634752918/897136254/128493765/975861432/463527189.
An upper bound from a search, not a minimum. Link, no givens:

https://sudokumaker.app/p/mbCgPDpBMW

Chris dropped a variant that assumes exactly 36 targets, so 4 in every line, as a rule the
solver may use (2026-11-05). At most 4 per line already caps the total at 36.

At most 4 patterns, same rules: seed 7 logged 21 marks with 4 patterns on the way, but its
grid was not saved. A dedicated run from a limit of 24 (`want=4`, seed 9, 900 s under load
about 18, 484 tries, `t36-want4.jsonl`) found no hit. Its nearest was 23 marks with 7
patterns. So 25 marks with 1 pattern is the best saved board.

Under the looser meaning, all the rules allowed, `nr_t36_fewer.py` (seed 3, 900 s,
`t36-fewer.jsonl`) got down to 14 marks fixing all 36 targets, proven on the full model:
grid 761394852/592178364/834562719/123487695/957216483/648935271/416753928/379821546/
285649137. An upper bound from a search, not a minimum, and not the board Chris asked for.

## Digits fixed by the border alone (2026-11-05)

No marks or clues, only the 32 border digits. `fill_climb.c` climbs on the exact number
of fillings. The first run (`fill-climb.log`, 9,846 evaluations) had a bug: most moves
left the border alone and forced a restart (7,244 restarts), so it was close to random
sampling. The fixed run (`fill-climb-2.log`, seed 2, 182,280 evaluations, 26 restarts, 900 s
of wall clock with a pause) reached:

- Fewest fillings 6,712, with r2c3 = 9 and r8c8 = 8 forced. Grid 213794856/579628431/
  468513729/145872693/932456178/786139542/827341965/351967284/694285317.
- Most forced inner cells 4, with 59,653 fillings: r2c7 = 9, r3c3 = 4, r7c2 = 1, r7c8 = 7.
  Grid 321945768/587263914/964781352/132678549/475392186/896514237/219856473/758439621/
  643127895.

`nr_fill_verify.py` confirms both counts and forced cells with `count_fills.c`. The climb
scored fillings, not forced cells, so 4 is what it passed on the way, not a target it
chased. Every forced cell found is in a corner box, where inner cells see the most border.
No grid fixed by its border turned up, and none is ruled out.

Each digit with no corner cell has 4 border cells and 5 inner cells, in the 5 rows and 5
columns its border cells leave free. Those 4 cells also clear up to 4 boxes for it, so
digits whose border cells sit in different boxes have the fewest places left.

## What forces digits (2026-11-05)

By hand, the four clue families are permutations: the digits of r1 place one top clue
target in each row and column, and likewise r9, c1 and c9. So the target set is a union
of 4 permutation matrices, and a border digit is forced when the marks leave its clue one
possible cell, directly or after the other digits of its line take their cells. A non-target at rXcY rules out r1cY = X, r9cY = 10 - X,
rXc1 = Y and rXc9 = 10 - Y. Two clues landing on one cell cost a line one of its 4
targets, which is what breaks a line with 4 disjoint marks.

Shapes with no givens (`nr_force_shapes.py`, negative rule off and on; "forced" is on
the border-only model, a superset of the real options, so it is sound):

- 16 disjoint marks leaving one row and one column empty force exactly 4 digits at the
  shared cell, with the negative rule off. Only one symmetry class is feasible, r1 c3
  and its images (r3 c9 was run too): r1c1 = 3, r1c3 = 1, r1c9 = 7, r9c3 = 9.
- With the gap at r5 or c5, 16 marks are infeasible, since r5 needs 2 targets. Gap r3 c3
  is infeasible, since r3c1 and r1c3 would both be 3 in box 1. Gap r1 c1 and gap r1 c9
  are infeasible, because two clues would land on one cell of a line with 4 marks.
- Negative rule on: every disjoint block with 12 or more marks was infeasible. 8 marks
  or fewer in these shapes forced nothing, with more than 5,000 borders (capped).

Sample (`nr_force_sample.py`, seed 11, 300 s, negative rule on): 387 random grids, of
which 300 hit the 3,000-border cap and make no claim. Of the other 87, 74 force no
border digit. Forcing rose with mark count: 16 marks reached 6 and 20 marks reached 32.

20 marks that pin the whole border, verified on the full model (`nr_force_verify.py`,
another border is infeasible): r1c2 r1c3 r2c6 r3c2 r3c3 r3c4 r3c6 r4c2 r4c6 r4c7 r4c8
r5c1 r5c2 r5c6 r6c2 r6c3 r6c6 r7c2 r7c3 r8c3. Grid 654792831/281635479/793184256/
547963182/928541763/316278594/162357948/835429617/479816325. That border has exactly
175,079 fillings (`count_fills.c`), with r3c2 = 9 and r3c7 = 2 forced inside. So marks
can fix a border outright, and step (c) now rests on whether a border can fix its middle.
Link, no givens, not unique (`build_link_20.py`):

https://sudokumaker.app/p/HwcDM7rcpp

Inner cells: r2c2 sees at most 7 border cells and r5c5 at most 4, so no inner cell is
forced by sight alone. Inner digits come only from hidden singles and deeper logic.

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

### Opening ideas

`nr_opening.py` gives what the marks force before any given is used. No human
solver has walked this path, so the puzzle's difficulty is untested.

- r3 and r4 each have 4 disjoint marks over c1-8. So r3c9 and r4c9 are not
  targets, and all 4 clues into each row land on different cells.
- Those two non-targets remove pointers: r3c1 and r4c1 are not 9, r3c9 and r4c9
  are not 1, r1c9 is not 3 or 4, and r9c9 is not 6 or 7.
- r1c4 is never a target on the marks alone. No short hand reason is known yet.
  It also removes r1c1 = 4, r1c9 = 6, r1c4 = 1 and r9c4 = 9.
- The solver's marks-alone candidates: r3c1 12367, r3c9 234578, r1c9 125789,
  r9c9 3589.
- Marks at r3c1, r3c3 and r3c5 make r3 and r4 opposites across c1-6. The three
  marks at r4c5-r4c7 make c5-8 alternate in r4 and in r5.
- The givens read as pointers from these rows: `L5=1`, `T4=6` and `B5=8` all have
  targets in r4 or r5 in the solution.

The `L8=9` idea (Chris, 2026-11-04), read as the c1-2 marks in r7-9 with the 9
clue, by solver on the marks plus `L8=9` alone:

- r8c1 is 2 to 8. r8c1 = 2, 3, 4 or 6 forces targets at r7c1, r8c2 and r9c1.
  r8c1 = 7 or 8 forces targets at r7c2, r8c1 and r9c2. r8c1 = 5 allows both.
- Adding one more given: `B5=8` leaves r8c1 as 4, 5 or 7, `R7=8` removes 8, `L5=1`
  removes 6, and `T4=6` removes nothing. All five leave only 5.
- No hand reason is known yet for any of these splits.

### Chris's opening board (2026-11-04)

`T1=7`, `L7=9`, `L9=3` and marks at r5c1, r6c1 and r7c1, read from his picture.
Only these three marks were applied, with no rule on unmarked windows. The board
is not yet unique.

- r7c1 cannot be a target, from the three givens alone (solver, and by hand).
  `L7=9` rules out r7c1 = 1 and r7c9 = 9. `T1=7` rules out r1c1 = 7, which would
  repeat the 7 in c1. `L9=3` rules out r9c1 = 3, which would repeat the 3 in r9.
- The marks then force targets at r5c2, r6c1, r7c2 and r8c1, and no targets at
  r5c1, r6c2, r7c1 and r8c2.
- r1c1 is 2, 3, 4, 6, 8 or 9, and r9c1 is 2, 4, 6, 7, 8 or 9.

### Chris's second board (2026-11-04)

`T1=6`, `L6=9`, `L9=4`, `R9=9`, with marks at r1c8, r3c1, r4c1, r6c1, r6c8, r7c1,
r8c1, r8c7 and r8c8, read from his picture. **Infeasible**, proven by CP-SAT, even
with unmarked windows free and his colours and digits left out (`nr_board2.py`).

- `nr_board2_core.py`: the minimal conflict is all four givens and the marks at
  r1c8, r3c1, r4c1, r6c1, r7c1, r8c1 and r8c8. Marks r6c8 and r8c7 are not part of
  it.
- Dropping any one item of that conflict makes it feasible. Dropping r1c8 or r8c8
  also keeps his blue digits r1c1=9, r9c1=6 and r9c6=4, with or without the rule on
  unmarked windows. All his colours together still fail after either drop.
- The left side's logic holds by hand: r6c1 has no route, so r9c1 is a target, which
  forces r1c1=9 and r9c1=6, and `L9=4` then gives r9c6=4.

The conflict by hand, which uses exactly the items of the minimal conflict:

1. r6c1 has no route, so the c1-2 chain makes r9c1 a target, forcing r1c1 = 9 and
   r9c1 = 6.
2. r9c1 = 6 sends the bottom clue of c1 to r4c1. The marks then make r3c2, r5c2,
   r6c2 and r8c2 targets, which fills c2, so r1c2 is not a target.
3. r1c1 = 9 sends the left clue of r1 to r1c9, so r1c8 cannot be a target (mark
   r1c8).
4. r9c9 has no route, so mark r8c8 makes r9c8 and r8c9 targets. r9c8 is then either
   9 with r9c9 = 2, or 1.
5. If r9c8 = 9, its bottom clue targets r1c8, against step 3.
6. If r9c8 = 1, r8c9 can only be reached with r1c9 = 8. The right clue of r1 then
   targets r1c2, against step 2.

With the box 3 mark, r1c8, deleted (Chris, 2026-11-04), `nr_board3.py`, all-marked
rule on the 8 marks left: feasible, not unique (200 grids found, capped, each re-read
by the reader). Forced digits: r1c1 = 9, r1c8 = 6, r1c9 = 7, r4c9 = 9, r7c1 = 1,
r9c1 = 6, r9c6 = 4, r9c8 = 9, r9c9 = 2. His colours all stay allowed except r1c8,
which must be a target; r2c8 and r2c9 are now open.

### Chris's third board (2026-11-04)

The same four givens, with marks at r1c3, r1c5, r3c1, r4c1, r6c1, r6c8, r7c1, r8c1,
r8c7 and r8c8, read from his picture. Chris asked about dropping the rule on unmarked
windows.

- Without that rule the marks are feasible. With it they are not
  (`nr_board4.py`). At least one unmarked window must be a checkerboard
  (`nr_board4_windows.py`).
- His colouring fails either way. r7c9 as a target needs r1c9 = 7, which makes r1c3
  a target, and he has r7c9 pink and r1c3 green.
- `nr_board4_colours.py`, unmarked windows free: the fewest colour changes is 4, and
  there are exactly two such sets. Flip the r6c8 window, or flip the r1c3 window.

With mark r6c8 and the colours of r6c8, r6c9, r7c8 and r7c9 deleted, unmarked
windows free (Chris, 2026-11-04): feasible, with every remaining colour and digit
held, and a grid re-read by the reader. r7c9 must not be a target, r1c9 is 5 or 6,
r7c1 = 1, r9c8 = 9 and r9c9 = 2. Uniqueness not tested.

Forced on that board with his colours (`nr_board5.py`, not unique: 200 grids,
capped): r1c1 = 9, r4c9 = 9, r7c1 = 1, r9c1 = 6, r9c6 = 4, r9c8 = 9, r9c9 = 2. r1c8
is a target. r1c7, r4c9 and r7c9 are not. r1c6 is 2 or 8, r1c9 is 5 or 6, r8c1 is 2
or 7, r9c2 is 5 or 7, r8c9 is 3, 4 or 8. By hand, r4c9 = 9 because a 9 in c9 at r2,
r3, r5 or r6 would make the green c1 cell in its row a target.

### Chris's fourth board (2026-11-04)

The same four givens, with marks at r1c3, r1c5, r3c1, r4c1, r6c1, r6c4, r6c8, r7c1,
r8c1, r8c7 and r8c8, read from his picture, unmarked windows free (`nr_board6.py`).
His colours as drawn fail: r7c9 pink needs r1c9 = 7, which makes r1c3 a target.
Flipping the r6c8 window (r6c8 green, r6c9 pink, r7c8 pink, r7c9 green) is the fewest
changes, and every other colour, digit and pencil mark then holds. That window is a
checkerboard in that phase even with its mark deleted. With the mark kept and the
window flipped: r1c2 = 6, r1c6 = 8, r1c9 = 5, r9c2 = 5, 1s at r1c4 and r9c5, and r8c9
is 3 or 8.

### Chris's fifth board (2026-11-04)

The fourth board without mark r6c8, with r6c8, r6c9 and r7c9 uncoloured and r7c8
read as green (it was selected in his picture). Unmarked windows free. **Fails**,
solver and by hand, because r7c8 must be a target:

1. r7c9 is not a target, since that needs r1c9 = 7, which targets the green r1c3.
2. With r7c8 green, r7 has only r7c1 and r7c4 pink. So the top clue reaching r7 needs
   r1c4 = 7, and the right clue of r7 needs r7c9 = 6, since r7c9 = 9 repeats r9c8.
3. r1's four pink cells take all four clues into r1. The left clue takes r1c9 and the
   bottom clue of c8 takes r1c8. So r1c4 and r1c5 take the right clue and the top
   clue of the 1, which targets itself. r1c4 = 7 makes r1c5 = 1, and the right clue
   needs r1c9 = 6, repeating the 6 of r7c9 in c9.

With r7c8 pink everything else he drew holds, pencil marks included: 200 grids
(capped), each re-read by the reader. r6c9 is then forced pink, r6c8 and r7c9 green.

### Chris's sixth board (2026-11-04)

The same four givens with 13 marks: r1c3, r1c5, r3c1, r4c1, r6c1, r6c4, r6c8, r7c1,
r7c7, r7c8, r8c1, r8c7, r8c8, read from his picture (`nr_board7.py`). Without the
negative rule, all his digits, colours and pencil marks hold, 50 grids or more
(capped). With it, the givens and marks alone are infeasible. No single unmarked
window is forced, but at least one extra checkerboard is needed, and r3c4 is the only
single extra mark that works: all his entries then hold under the negative rule, 50
grids or more (capped). A hand reason is not known.

With mark r3c4 added and the negative rule on (`nr_board8.py`, `board8-forced.json`,
picture `board8-forced-1.png`): every target cell is determined, and all of c1 and c9
are forced: c1 reads 9 8 4 7 3 5 1 2 6 and c9 reads 5 4 8 9 7 1 6 3 2. r1 reads
9 6 (2/3) 1 4 8 (2/3) 7 5, r9 reads 6 5 (7/8) 3 1 4 (7/8) 9 2, and r6c5 = 9. Not
unique: 200 grids (capped), each re-read by the reader.

More marks cannot make that board unique (`nr_board8_more_marks.py`), negative rule
on, his digits and colours not held. Of the 50 unmarked windows, 48 singles are
infeasible and 2 not unique. Of the 1,225 pairs, 1,222 are infeasible and 3 not
unique. None timed out. The board allows 2 edges, each with more than 2,000
completions (capped), and marks read nothing but the edge.

### Chris's seventh board (2026-11-05)

Outside T7=5 and 12 marks at r1, r3, r6, r8 by c1, c3, c5, read from his picture
(`nr_board9.py`, `nr_board9_negative.py`). r5c1-7 light green taken as not a target,
r5c8-9 pink as a target, orange/green and yellow/blue as two-way pairs.

Negative rule on: infeasible on the marks alone, with or without T7=5, so the layout
is the fault and not the digit. Removing one mark makes it feasible except for r3c3,
r3c5 and r6c3 with T7=5 (without T7=5, r3c5 also works). No single added mark helps,
with or without T7=5. A hand reason for the conflict is not known. All solves
finished.

Negative rule off: givens, marks, r5 colours and pairs hold, with orange = target
and yellow = target or not, or orange = not and yellow = not. Orange = not with
yellow = target is infeasible. r5c1-6 are forced non-targets by the 4 disjoint marks.
r5c7, r5c8 and r5c9 are each open on the givens and marks, so his r5 colours there
are a choice.

The pair pattern is what the negative rule asks of adjacent marks, by hand. Marks r1c1
and r3c1 give exactly one target in each of r2 and r3 within c1-2. Window r2c1 may not
be a checkerboard, so both are in one column, making r2c1 and r3c1 alike. The same
holds across and down the block.

Fewest marks to add so it holds under the negative rule, keeping T7=5 and the 12 marks
(`nr_board9_fix.py`, all proven optimal, grids re-read by the reader): 2. There are
exactly 5 such pairs, enumerated until infeasible: r2c8+r8c6, r1c8+r3c7, r1c8+r2c8,
r1c7+r3c8, r2c8+r3c8. With his colours held as well, the minimum is 3 for orange = target
and yellow = target (one set: r1c8, r3c8, r5c7), 3 for orange = not and yellow = not
(one set: r3c8, r5c7, r8c6), and 4 for orange = target and yellow = not (one set: r4c7,
r6c4, r8c4, r8c7). Those three sets are examples, not all of them.

Adding B7=5 (Chris, 2026-11-05) breaks the 12 marks with the negative rule off, so no
added mark can help (`nr_board10.py`, `nr_board10_check.py`; the two 5s with no marks
are feasible as a control). By hand: both clues read the 5 of c7, so if it sits in row
p then r1c7 = p and r9c7 = 10 - p. Row p is not 5, since r1c7 = 5 repeats the 5, and
not 1 or 9. Both of row p's vertical clues land on the same c7 cell, leaving only its
left and right clues for c1-6, but row p's three disjoint marks need 3 targets there.
Removing any one of the 12 marks is feasible with the negative rule off, and each
witness grid has p in the rows of the removed mark. The negative rule was not tested
on those removals.

### Chris's 11-mark board (2026-11-05)

No outside digits; r1c1 = 9, r1c9 = 1; marks r2c1 r2c3 r2c5 r2c7 r3c8 r4c2 r4c6 r6c2 r6c6
r8c2 r8c6 (`nr_board12.py`, `nr_board12_fix.py`). Broken as drawn both ways.

Negative off: marks and digits hold. His colours fail, and greens r1c4, r1c5 and r1c8
alone conflict with the marks. By hand: 4 disjoint marks make r1c2, r1c3, r1c6, r1c7
non-targets, so with those greens r1's only targets are in c1 and c9. The bottom clue that
reaches r1 is the 9 of r9, so r9c9 = 9. Then T9, B9, the left clue from r1c1 = 9 and the
right clue from r1c9 = 1 all land on r1c9, so c9 has one target, and mark r3c8 needs one in
r3c9 or r4c9. Flipping any one of those three to a target makes all his entries hold.

Negative on: the marks alone are infeasible, no hand reason known. With his two digits,
removing one of r2c3, r2c5, r2c7, r3c8, r4c2 or r4c6 or adding r2c4 or r2c6 makes the marks
feasible. His colours were not rechecked on those, and either addition contradicts his r2-3
colouring.

### Chris's 10-mark start (2026-11-05)

Ruling for his boards from here: no negative rule for now, since he adds marks as needed,
and hold every colour, mark and pencil mark he draws. Marks r2c1 r2c3 r2c5 r2c7 r4c2 r4c6
r6c2 r6c6 r8c2 r8c6, nothing else (`nr_board13.py`): feasible. Forced non-targets are
r1c2 r1c3 r1c6 r1c7 r2c9 r3c9, every other status is open. Border digits: r1c1 is 1, 4, 5, 8
or 9; r1c9 is 1, 5, 6 or 9; r9c9 is not 7 or 8; r1c2 r1c3 r1c6 r1c7 r2c1 r3c1 r2c9 r3c9 r9c2
r9c3 r9c6 r9c7 each lose one digit, the one pointing at a forced non-target.

`nr_check.py BOARD_JSON` is the one checker for his boards from here, under that ruling: it
reads a small JSON board and reports feasibility or a minimal conflict, status and digits.
`board14.json`, his 11 marks with r4c8 and his colours: holds, 200 grids (capped). r1c8 is
forced a target, r1c1 is 1, 8 or 9, r1c9 is 1 or 9, r9c9 is 4, 5 or 9. Status map and
digits come from one run of about 22 s.

`board15.json`, 16 marks with r1c9 = 5: the marks alone fail, with no negative rule. Marks
r1c6, r2c6, r4c6, r6c6 and r8c6 clash. By hand: r1c6, r4c6, r6c6 and r8c6 are 4 disjoint
marks on c6 and on c7, so r3c6 and r3c7 are non-targets, and r2c6 needs exactly one of them
a target. `board15b.json` removes r1c6 and makes r1c7 green: holds, 200 grids (capped), with
r9c9 = 1 forced and r9c9 a target.

`board16.json`, 13 marks with r1c9 = 8: r1c1 pink conflicts with that digit. By hand: r1c1
has three routes. r1c9 = 9 is out. r9c1 = 9 makes r9c9 a target, but r1c9 = 8 makes r8c9 one
and mark r8c8 makes those opposite. r1c1 = 1 puts two clues on r1c1, leaving 3 clues for the
4 targets r1c1, r1c2 (right clue), r1c4 (mark r1c3) and one of r1c5/r1c6 (mark r1c5).
`board16b.json` makes r1c1 green: holds, 200 grids (capped), r1c1 is 2, 4 or 5.

`board17.json`, 17 marks with r1c9 = 8, half-magenta taken as a target, each set of corner 9s
as "the 9 is in one of these": holds, 200 grids (capped). New: r3c9 = 5 and r9c9 = 3, r5c1
is a target, r9c1 is not and is 5 or 8. His r3c9 pencil read as 2, 4, 5 drives some of that:
2 and 4 point at green r3c8 and r3c6. `board17b.json` drops that pencil. Then r3c9 is 5 or 6,
r1c8 stays 2, 5, 6, 9, and r4c9 and r9c6 are no longer narrowed. Still forced: r9c9 = 3, r5c1 a
target, r9c1 not a target and 5 or 8, r3c1 not 5, r9c7 is 1, 4, 6 or 7. Hand reasons exist for
r9c1 and r9c7. r9c9 = 3, r5c1 and r3c1 not 5 are solver results: `nr_why.py` found no short
chain with its simple rules and one level of case split.

`board18.json`, 19 marks with r4c1 and r6c1 added and r3c9 pencilled 2, 5, 6: holds, 200 grids
(capped). Forced digits r1c1 = 5, r1c4 = 1, r9c1 = 8, r9c4 = 9, r9c6 = 2, r9c9 = 3, r1c8 is 2 or 6,
r3c9 is 5 or 6, r2c1 is 3 or 6. Non-targets r4c4 r5c4 r6c4 r7c4 and r9c1.

Same 19 marks with the negative rule on (`nr_check.py board18m.json negative`): the marks alone
are feasible, 200 grids (capped), and they fix all 81 target statuses and nearly the whole border:
r1 = 3 6 4 2 7 1 5 8 9, r9 = 6 8 5 1 2 7 9 3 4, c1 = 3 5 8 4 (2/9) (2/9) 1 7 6, c9 = 9 3 7 2 (1/8) (1/8) 6 5 4. His drawing fails:
r1c9 = 8 alone conflicts (it is 9), and so do green r7c1 (a target) and each set of corner 9s.
Link, no givens:

https://sudokumaker.app/p/7bjhMWWNRC

Why r1c9 = 8 fails there: no short reason known. By hand it makes r1c2 a target, and the marks
with the negative rule then force his colouring along r1-r3, r4-r7 in c1, c2, c7, c8, c9 and the
r8-r9 run. `nr_board18_why.py` finds a set of 15 unmarked windows that fail together, each one
needed: r3c3 r3c8 r4c2 r4c6 r5c1 r5c3 r5c4 r5c5 r5c6 r5c8 r7c2 r7c6 r7c8 r8c3 r8c7. Dropping any
one gives a grid. That is one minimal set, not necessarily the smallest.

Chris's solve on these 19 marks, negative on (ruling 2026-11-05: negative on, exactly these
marks), has a two-way magenta/purple colouring with r1c9 8 or 9. Next deduction, true both ways
(`nr_next_pair.py`, `nr_next_chain.py`, confirmed on the full model): r8c1 and r8c2 are not
targets. c1 and c2 hold 4 and 3 of the pair, one each way round. So the colour with 4 targets in
its column kills that column's r8 cell, and unmarked window r7c1 kills the other. Pencil marks
true both ways: r1c1 is 3, 5 or 7 and r9c9 is 2, 3 or 4. r9c2 is also never a target, which is direct
for magenta and a longer chain for purple.

Outside clue impact on these 19 marks, negative on, no givens (`nr_clue_impact.py`, `count_cells.c`,
exact): 2 borders of 184,900 fillings each, 369,800 solutions. The c1 and c9 swaps are linked. B9
= 1 or 8 picks the border. Fewest left by one clue: T3 = 3 leaves 14,904, R4 = 7 leaves 19,000, B6 =
9 leaves 26,368. Best expected whichever digit it holds: L4, 72,048 left on average. L1, L7, L9, R1,
R9, T1, T6, T9, B1, B4, B7 are forced (4, 1, 7, 3, 7, 8, 1, 4, 4, 1, 5) and add nothing.

B9 = 8 settles his magenta/purple pair at once: B9 reads a cell of c9, r1c9 is not a target, so it
cannot read r1c9, and if r1c9 = 8 no other c9 cell can hold 8. So r1c9 = 9 and purple are the
targets. It also picks the border. Spec for promoting these scripts: #100. T9 can only be 4: it also
rules out magenta on the solver, even with no negative constraint, but no short chain was found.

Chris took B9 = 8 (`board20.json`, `nr_check.py`, negative on): one border, 184,900 solutions, r5c1 = 2,
r6c1 = 9, r5c9 = 1, r6c9 = 8, and r6c6 = 2 is the first forced inner digit, a hidden single in box 5,
since r4c9, r5c1, r1c4 and r9c5 hold the other 2s reaching it. Only inner cells are open now, and all 81
target statuses are fixed.

## Step (a)

Under the all-marked ruling every sudoku grid is valid: it has exactly one set of
targets, outside digits and marks. Any grid above answers (a).
