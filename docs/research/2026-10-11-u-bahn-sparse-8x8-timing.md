# U-Bahn: one sparse 8x8, rated 5 of 5, on four solvers

2026-10-11. Chris supplied a plain U-Bahn puzzle (no Choco-Banana) as a
picture, rated 5 stars of 5 for difficulty by its source. The source and
author are not known to this note. It is the first puzzle with **some outside
numbers missing** that any of our models has been run on: 26 of the 64
numbers are given.

## The puzzle, as read from the picture

8x8. Strips cross, branch, straight, turn from the outside in. The reading is
mine, from an image; a misread digit would change everything below.

| Row | cross | branch | straight | turn |
| --- | --- | --- | --- | --- |
| 1 | | 0 | | |
| 2 | | 0 | 0 | |
| 3 | 1 | 1 | 0 | 2 |
| 4 | | 1 | | |
| 5 | 0 | | | 4 |
| 6 | | 0 | 3 | |
| 7 | | | 2 | 4 |
| 8 | | | | 6 |

| Column | cross | branch | straight | turn |
| --- | --- | --- | --- | --- |
| 1 | | 0 | | 2 |
| 2 | 2 | | 0 | |
| 3 | | 1 | | 4 |
| 4 | | | | |
| 5 | 0 | 0 | 5 | |
| 6 | | | | |
| 7 | 1 | 1 | | |
| 8 | | | | |

## Result

One run each, one core, box load under 1, wall clock for the whole
uniqueness check (find a network, forbid it, prove there is no other).

| Solver | Verdict | Time |
| --- | --- | --- |
| CP-SAT, flow connectivity | unique | 0.35 s |
| CP-SAT, spanning-tree connectivity | unique | 0.11 s |
| PySAT (CaDiCaL), lazy connectivity cuts | unique | 0.02 s, 4 cuts |
| JWKNT/logical-solver, row-major search | unique | 1.53 s, 17,562,093 nodes (best of 3) |

- All three of our runs returned the same network, and the solver-free rule
  reader (`network.why_not_network`) accepts it. I checked row 8's turns and
  column 5's straights against the givens by eye. The network is not printed
  here, so the puzzle stays unspoiled.
- **A puzzle a person finds very hard is trivial for every SAT-style engine
  here.** Human difficulty does not predict solver time on this one.
- **Order of the engines is the same as on the hybrid** (#786): PySAT with
  lazy cuts first, CP-SAT some 5 to 17 times behind, and here the cuts do
  fire (4), unlike on the full-number fixture puzzles (#776).
- Tree beat flow on this run, the reverse of the full-number baseline
  (#777). One puzzle, one run: not a finding.

## How it was run

The shipped `model.build` and `sat_model.uniqueness` take only a full set of
outside numbers. A throwaway script outside the repo built the same models
from their own parts (`model._add_pieces`, `_add_root`, `_add_flow` or
`_add_tree`; `sat_model._piece_clauses`, `_Connectivity`, `_solve`) with a
count constraint only on the given numbers, and the flow sized to the whole
board. JWKNT's solver takes `-1` for a missing number; it ran from
`~/src/third-party/logical-solver`, none of its code is here.

## Not measured

More than one sparse puzzle; run-to-run spread; the hunt loop that would
strip numbers down to such a set (each strip step is one of these checks, so
at 0.02 to 0.35 s a step it is affordable on any of the three).
