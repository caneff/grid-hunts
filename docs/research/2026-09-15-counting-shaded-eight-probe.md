# Counting shaded: a valid grid with a shaded cell holding 8 exists [verified]

Rule (counting shaded POC, Michael Lefkowitz): normal sudoku; a digit on a shaded cell equals
the number of shaded cells in its up-to-8 king-move neighbours. Only shaded cells
carry a clue. Not all shaded cells are visible. Rulings from Chris, 2026-09-15: an
isolated shaded cell is impossible (no digit 0); uniqueness is out of scope for now;
the first goal is any valid grid plus shaded cell set where one shaded cell holds an 8.

## Result

`uv run finders/counting_shaded/probe.py` — CP-SAT, one worker, OPTIMAL in 1.40 s.
An independent Python recheck of sudoku rows/columns/boxes and the shaded cell count
passed. `*` marks a shaded cell; the 8-cell is r4c3.

```
5  8  1  9  2  4  3  6  7
9  3* 4* 7  6  8  1  2  5
2  6* 7* 5* 3* 1* 9  4  8
4* 7* 8* 6* 1  9  2  5  3
3* 5* 6* 4* 7  2* 8  1  9
1  9  2  3* 8  5* 4* 7  6
8  4  3  1  5* 7* 6* 9  2
7  2  9  8  4* 6* 5* 3* 1*
6  1  5  2  9  3* 7  8  4
```

## Model

- `x[r][c][d]` one-hot digits with the usual row/column/box exactly-one.
- `g[r][c]` shaded cell boolean; `g ⇒ Σ g(neighbours) = digit`, via
  `only_enforce_if`.
- One `e[r][c] ⇒ g ∧ digit 8` per cell, with `bool_or` over all `e`.

## Facts that fall out of the rule

- 9 never sits on a shaded cell, and a corner shaded cell holds at most 3, an edge shaded cell
  at most 5.
- A shaded cell 8 cannot be a box centre (r2c2, r2c5, …, 0-based box middles): its
  whole 3×3 would be shaded cells in one box, needing nine distinct digits ≤ 8.

![grid](shaded cells/eight-probe.png) — `uv run --with pillow finders/counting_shaded/render.py <out.png>`
