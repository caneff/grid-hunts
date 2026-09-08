# How many brainanas can a grid have?

Question (Chris): maximize the number of uninfected groups, clued or not.

## Counting them in the model

Two attempts, one that works:

1. Sum over the pocket placement library (a placement whose cells are all
   uninfected and whose border is all infected IS a whole group). As an
   objective term it runs (`pairopt.py ... pock`, 37 grids, best 4 groups) but
   one solve peaks at 7.7 GB RSS at 8 workers, so pock hunts need a 13 GB cap
   and two processes. As a constraint (`sum >= 5`) one solve climbed past
   16 GB and died: CP-SAT turns `>= 1` over 200k literals into a clause, a
   `>= 5` cardinality it does not. A Euler-number count (Gray's formula on
   2x2 windows) is cheap but undercounts: 135 of 195 found grids have holes,
   chocolate rectangles floating inside a banana.
2. Spanning-tree labeling (model d2cdd33, `min_groups`, `pocket_weight`):
   every uninfected cell carries the label of its group and a distance to
   the group's one root (label == own index); a non-root needs a neighbour
   with the same label one step closer; adjacent uninfected cells share a
   label. ~300 bools, exact. Verified against the flood fill on want3_200
   (4 groups feasible, 5 infeasible with that shading fixed).

## Results (tools/groups.py, box-9 pair open, no pocket library)

| brainanas | verdict | time |
|---|---|---|
| 5 | FEASIBLE | 20 s, grid `found/groups_5` (sizes 21, 12, 7, 6, 5) |
| 6 | unknown | 600 s timeout at 8 workers, then 3600 s timeout at 16 workers (`scratch-zombo/hunt/plant/six.log`) |

Before this the record across every arm was 4 (5 grids of 195). The
`pairpock` arm (37 grids) maximized the library count and never beat 4.

## Five brainanas and two circles in box 9: impossible

Chris asked for 5 brainanas with 2 circles in box 9. Two sweeps, both exact:

- `pairopt.py ... g5` (42 pair kinds without r8c8, both circles open, pair
  shading fixed, `min_groups=5`, circles maximized): every kind INFEASIBLE,
  34-98 s each, no timeouts. That run also excludes grids within 12 cells of
  `found/`, so:
- `tools/kinds5.py` (all 49 feasible pair kinds from PAIRS.md including r8c8,
  same model without the exclusion and without an objective): every kind
  INFEASIBLE, no timeouts.

Since every way to put two circles in box 9 is one of those pair kinds, no
valid grid has 5 brainanas and 2 box-9 circles. The `found/groups_5` witness
has one box-9 circle (r9c7). Open: 5 brainanas with one box-9 circle and
circles maximized elsewhere; whether 6 brainanas exist at all (hour-long run
pending).

## Five brainanas and two circles in box 8: 38 of 144 cases infeasible (cut)

Same sweep for box 8 (`tools/pairs8.py`: 36 cell pairs x 4 shading kinds,
both circles open, pair shading fixed, `min_groups=5`, no objective). Box 8
keeps 203k pocket placements against box 9's 133k, so 8 workers crossed the
9 GB cap on the hard kinds; the run that held was 2 processes, 13 GB, 4
workers, 133 s per case. Cut at Chris's second status ask with 38 of 144
cases done, every one INFEASIBLE, no timeouts (`pairs8_partial.log`; pairs
r7c4+* complete, r7c5+r7c6, r7c5+r8c4, r7c5+r8c5 partial). Follow-up issue
covers the remaining 106 cases; the script skips cases already in the log.
