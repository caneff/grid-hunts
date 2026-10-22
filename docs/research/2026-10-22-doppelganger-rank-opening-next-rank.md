# Doppelganger rank opening: which rank each place can take next

Chris's opening (`finders/doppelganger_rank/fixtures/opening_9x9.json`: c1 top 34,
c9 top 6, r5 left 35, r5 right 4), spec #66. Question: for each of the 32
places without a clue, which ranks 1–36 can a fifth clue there take and keep
the board solvable?

Space covered: all 32 × 36 = 1152 (place, rank) pairs, every one decided.

- **855 possible, by witness:** seen in 400 distinct solutions sampled from the
  repo `RankModel` (random seeds, `symmetry_level=0`).
- **17 possible, by solver:** the 297 pairs the sample never showed were each
  solved as a fifth clue on the repo `RankModel` (one worker, 60 s limit;
  `spec-66` at 74e39d7, after #75's buckets). 17 came back FEASIBLE.
- **280 impossible:** INFEASIBLE in that same solve. None timed out (the
  slowest took 56 s before #75; after it, most took under 0.1 s).

The 17 solver-only pairs: rank 7 at r3/r4/r6/r7/r8/r9 from the right and at
c2–c8 from the top and c9 from the bottom; rank 8 at c9 from the bottom;
rank 31 at r7 from the left and at c1 from the bottom.

Most restricting places: r1 from the left (31, 32 or 33) and r1 from the
right (5, 7 or 8), three ranks each; next is c2 from the top at 24.

Known gap: one model only. The solves did not run on #70's second model
(`reprove.py`), so an encoding bug shared across every result would go
unseen. Sample shares are of 400 sampled solutions, not of all solutions
(the full count is capped: over 552 in 60 s).

Scripts were scratch (session scratchpad: `sample_opening.py`,
`feas_opening.py`, `build_artifact.py`); the explorer page is
https://claude.ai/artifact/ApkATFTZ9F7pXD66cfrhrB
