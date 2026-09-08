# Chocolate in the upper left

Question (Chris): boxes 1-2 look like one banana clump; can we optimize for
chocolate there so both chocolate and banana deductions exist?

Why it is sparse. Infection flows only to smaller digits. Box 1's patient
zero is a 1 and infects nothing; box 2's 2 catches only an adjacent 1; box 4's
4 catches 1-3. Chocolate in the upper left arrives by chains from the
big-digit boxes, so the corner is banana by default.

Measured (tools/ceiling.py, model 6ec3f89, rows 1-5 x cols 1-5 = 25 cells):

- Pair r7c8 infected + r9c7 uninfected, maximize quadrant chocolate: 7/25,
  proven OPTIMAL in under 30 s, same grid for seeds 5, 8, 9.
- Same pair, maximize colour boundaries in the quadrant instead: 16/40 edges,
  the same grid. With chocolate that sparse, boundaries = chocolate perimeter,
  so both objectives agree.
- Across the 119 found grids the quadrant holds 3-9 infected cells, median 5;
  the 9 is bal36_300 (min-infected 36 arm). The unconstrained ceiling was not
  measured: the objective model without a fixed pair shading exceeds a 14 GB
  virtual cap (bad_alloc); the fixed-shading model runs at ~4 GB.

Conclusion. Under the map #342 rules the upper left cannot carry a "this
banana must grow" deduction: there is not enough chocolate to box a banana in.
The role swap (`rect=0`) is not a lever: #342 records it as infeasible under
gdc's rules (CP-SAT proves it in under a second; the one-patient-zero-per-row
rule is the killer). What remains:

1. Accept it: the upper left resolves by sudoku + Cocci dots, and the
   chocolate/banana interplay lives in the bottom and right thirds. Optimize
   grids for chocolate reach into boxes 2 and 4 (min_cross, bonus) rather than
   box 1.
2. A rules change, which is a wayfinder decision, not a generator setting:
   e.g. a different digit-to-box assignment so a big patient zero sits in the
   top band.

## Planting the 4 and 5 next to box 1 (tools/plant.py)

Question (Chris): bias the upper left differently — plant the box-4 and box-5
patient zeros where their chains reach into box 1.

Six plants as givens, each with the box-9 pair open and no pocket library
(min_pockets 0, so the objective model fits in memory), maximizing circles plus
50000 per infected box-1 cell; every run proved OPTIMAL in under 10 s:

| plant | box-1 infected | quadrant (5x5) |
|---|---|---|
| 5 r4c4, 4 r5c1 | 3/9 | 9/25 |
| 5 r4c4, 4 r5c2 | 3/9 | 8/25 |
| 5 r4c4, 4 r5c3 | 3/9 | 9/25 |
| 5 r5c4, 4 r4c3 | 3/9 | 7/25 |
| 5 r5c4, 4 r4c2 | 3/9 | 7/25 |
| 5 r5c4, 4 r4c1 | 3/9 | 5/25 |
| no plant | 3/9 | 6/25 |

Box 1 holds at most 3 infected cells whatever is planted: its own 1 plus two
more, and the digit-height bound (row r holds only infected digits <= r+2)
leaves no room for a third. Planting moves those cells, it does not add any:
the 5 r4c4 + 4 r5c1 grid runs a 5-4-3-2 staircase up column 3 into r2c3.
Grids are in `scratch-zombo/hunt/plant/grid_*_ceil.txt` (not synced to
`found/`: they are ceiling witnesses, 6-10 circles, no pocket circles).

Two gotchas from the run. The fixed pair r7c8 infected + r9c7 uninfected used
by `ceiling.py` is infeasible with every one of the six plants; the ablation
(`scratch-zombo/hunt/plant/ablate.py`, 18 solves in one process) pins it on
the 5: a 5 at r4c4 or r5c4 is infeasible with that pair, while a 4 in any of
the six cells is feasible with it, and every plant is feasible with the pair
open. A plant hunt needs its own pair kind. And repeated solves in one process
leaked until `release_heap()` landed in the model (see its docstring); the
18-solve ablation is the confirmation.

## Chocolate reaching boxes 2 and 4 (tools/pairopt.py b24)

Accepting the corner, the next hunt rewarded chocolate in boxes 2 and 4:
`pairopt.py shard 3 400 90 b24`, one run per box-9 pair kind (42, no r8c8),
circle weight 10000 plus 3333 per infected cell in boxes 2 and 4, stall 90 s.
39 of 42 kinds produced a grid (r7c7+r7c8 IU, r7c9+r9c9 IU, r7c9+r9c8 IU and
r9c8+r9c9 IU hit the 400 s limit); results are `found/pairb24_*`, arm
"pair boxes 2+4" on the lineup.

| | boxes 2+4 infected | circles |
|---|---|---|
| found/ before this arm (119 grids) | 2-7, median 4 | |
| b24 arm (39 grids) | 3-7, median 5 | 4-12, median 10 |

A one-cell median gain and no new maximum: with circles weighted three times
a chocolate cell the objective still spends its budget on circles. A heavier
chocolate weight (trade circles for reach) is the untested lever.
