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

## Step (a)

Under the all-marked ruling every sudoku grid is valid: it has exactly one set of
targets, outside digits and marks. Any grid above answers (a).
