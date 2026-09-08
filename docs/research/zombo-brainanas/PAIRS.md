# Box-9 circle pairs: which two cells can both carry a circle?

Each of the 36 cell pairs in box 9 was solved as two open circles (rectangle case in-model,
pocket case exact through the placement library, commit efe3ac2). Every pair was proven in
under 30 s at 8 workers; no pair timed out. Witness grids are in `found/pair_*.json`.

| | r7c7 | r7c8 | r7c9 | r8c7 | r8c8 | r8c9 | r9c7 | r9c8 | r9c9 |
|---|---|---|---|---|---|---|---|---|---|
| r7c7 | · | Y | Y | Y | Y | Y | Y | Y | Y |
| r7c8 | Y | · | **N** | Y | Y | Y | Y | Y | Y |
| r7c9 | Y | **N** | · | Y | Y | Y | Y | Y | Y |
| r8c7 | Y | Y | Y | · | Y | Y | **N** | Y | Y |
| r8c8 | Y | Y | Y | Y | · | **N** | Y | **N** | **N** |
| r8c9 | Y | Y | Y | Y | **N** | · | Y | **N** | Y |
| r9c7 | Y | Y | Y | **N** | Y | Y | · | Y | Y |
| r9c8 | Y | Y | Y | Y | **N** | **N** | Y | · | Y |
| r9c9 | Y | Y | Y | Y | **N** | Y | Y | Y | · |

Feasible 30, infeasible 6: r7c8+r7c9, r8c7+r9c7, r8c8+r8c9, r8c8+r9c8, r8c8+r9c9, r8c9+r9c8

Every infeasible pair involves r8c8 with a cell of the bottom-right 2x2 (r8c9, r9c8, r9c9),
or is one of r7c8+r7c9, r8c7+r9c7, r8c9+r9c8.

## Shading kinds per pair

For each feasible pair, can circle A / circle B sit on infected (I) or uninfected (U) cells?
Solved with the pair's shading fixed, both circles open, 120 s limit; nothing timed out.

| pair | II | IU | UI | UU |
|---|---|---|---|---|
| r7c7+r7c8 | - | Y | Y | - |
| r7c7+r7c9 | - | Y | Y | - |
| r7c7+r8c7 | - | Y | - | - |
| r7c7+r8c8 | Y | - | Y | - |
| r7c7+r8c9 | Y | - | Y | - |
| r7c7+r9c7 | - | Y | Y | - |
| r7c7+r9c8 | Y | Y | Y | - |
| r7c7+r9c9 | - | Y | Y | - |
| r7c8+r8c7 | - | Y | - | - |
| r7c8+r8c8 | - | - | Y | - |
| r7c8+r8c9 | - | - | Y | - |
| r7c8+r9c7 | - | Y | Y | - |
| r7c8+r9c8 | - | Y | Y | - |
| r7c8+r9c9 | - | Y | Y | - |
| r7c9+r8c7 | - | Y | Y | - |
| r7c9+r8c8 | - | - | Y | - |
| r7c9+r8c9 | - | - | Y | - |
| r7c9+r9c7 | - | Y | Y | - |
| r7c9+r9c8 | - | Y | Y | - |
| r7c9+r9c9 | - | Y | Y | - |
| r8c7+r8c8 | - | - | Y | - |
| r8c7+r8c9 | - | Y | Y | - |
| r8c7+r9c8 | - | - | Y | - |
| r8c7+r9c9 | - | Y | Y | - |
| r8c8+r9c7 | - | Y | - | - |
| r8c9+r9c7 | - | Y | Y | - |
| r8c9+r9c9 | - | Y | - | - |
| r9c7+r9c8 | - | - | Y | - |
| r9c7+r9c9 | - | Y | Y | - |
| r9c8+r9c9 | - | Y | - | - |

UU never happens: two pockets cannot both be clued inside box 9. II only with r7c7 cut off
from the 9's rectangle (r7c7 with r8c8, r8c9, r9c8). Everything else is one rectangle circle
plus one pocket circle. There is no symmetry to exploit: transposing swaps boxes 2/4, 3/7, 6/8
and moves the patient zeros, so all 30 pairs are distinct configurations.

## Optimal grid per pair kind (r8c8 excluded)

tools/pairopt.py: shading of the pair fixed, both circles open, maximize circles, 90 s stall,
avoiding every earlier found grid by >= 12 cells. Grids are found/pairopt_<pair>_<kind>.json.

| pair | kind | circles | clued bananas | infected |
|---|---|---|---|---|
| r7c8+r9c8 | IU | 12 | 2 | 27 |
| r7c7+r7c8 | UI | 11 | 2 | 29 |
| r7c7+r9c8 | UI | 11 | 1 | 28 |
| r7c9+r8c7 | IU | 11 | 1 | 29 |
| r7c9+r9c8 | UI | 11 | 1 | 30 |
| r8c7+r9c8 | UI | 11 | 2 | 29 |
| r8c7+r9c9 | UI | 11 | 1 | 26 |
| r9c7+r9c9 | UI | 11 | 2 | 29 |
| r7c7+r7c9 | IU | 10 | 1 | 23 |
| r7c7+r7c9 | UI | 10 | 2 | 30 |
| r7c7+r8c9 | II | 10 | 1 | 27 |
| r7c7+r8c9 | UI | 10 | 1 | 29 |
| r7c7+r9c7 | IU | 10 | 1 | 27 |
| r7c7+r9c7 | UI | 10 | 1 | 28 |
| r7c7+r9c8 | II | 10 | 1 | 30 |
| r7c7+r9c8 | IU | 10 | 1 | 27 |
| r7c7+r9c9 | UI | 10 | 2 | 30 |
| r7c8+r8c9 | UI | 10 | 2 | 30 |
| r7c8+r9c7 | UI | 10 | 2 | 30 |
| r7c8+r9c8 | UI | 10 | 1 | 29 |
| r7c8+r9c9 | IU | 10 | 1 | 24 |
| r7c9+r8c7 | UI | 10 | 1 | 28 |
| r7c9+r8c9 | UI | 10 | 1 | 27 |
| r7c9+r9c7 | UI | 10 | 1 | 27 |
| r7c9+r9c7 | IU | 10 | 2 | 31 |
| r8c7+r8c9 | IU | 10 | 1 | 27 |
| r8c7+r8c9 | UI | 10 | 1 | 31 |
| r8c7+r9c9 | IU | 10 | 1 | 26 |
| r8c9+r9c7 | UI | 10 | 1 | 27 |
| r8c9+r9c7 | IU | 10 | 1 | 27 |
| r8c9+r9c9 | IU | 10 | 1 | 28 |
| r9c7+r9c8 | UI | 10 | 1 | 26 |
| r9c7+r9c9 | IU | 10 | 1 | 24 |
| r7c7+r8c7 | IU | 9 | 1 | 26 |
| r7c7+r9c9 | IU | 9 | 1 | 23 |
| r7c8+r9c7 | IU | 9 | 1 | 25 |
| r7c8+r9c9 | UI | 9 | 1 | 30 |
| r7c9+r9c9 | UI | 8 | 1 | 31 |
| r7c8+r8c7 | IU | 7 | 1 | 28 |
| r7c9+r9c8 | IU | 7 | 1 | 32 |
| r7c9+r9c9 | IU | 7 | 1 | 32 |
| r7c7+r7c8 | IU | 6 | 1 | 29 |

42 of 43 kinds found a grid; best is r7c8+r9c8 IU at 12 circles.
