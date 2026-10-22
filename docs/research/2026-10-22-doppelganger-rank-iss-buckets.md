# Doppelganger rank: ISS's leading-digit buckets as CP-SAT constraints

Spec #66. A probe of a faster rank encoding for `finders/doppelganger_rank/model.py`,
taken from ISS's Full Rank handler (`FullRank` in `js/solver/handlers.js`,
ISS commit `2e386f8`, reference clone `~/src/reference/Interactive-Sudoku-Solver`).

## The ISS idea

A number's leading digit is the cell at its end of the line. The 36 leading
cells are exactly the four edge lines: column 1 (rows read from the left),
column 9 (rows from the right), row 1 (columns from the top) and row 9
(columns from the bottom); a corner cell leads two numbers. In classic
sudoku each edge line holds every digit once, so every digit leads exactly
four numbers, and ISS reads a clue's leading digit straight off its rank:
`(rank + 3) >> 2`. Only the up to four numbers in that **bucket** are ever
compared digit by digit.

## The Doppelganger version

Every line's digits still all differ, and each edge line holds 0 and eight
of 1..9. So:

- `cnt[0] = 4`: every line holds a 0.
- `cnt[d] = 4 - #{edge lines among c1, c9, r1, r9 whose missing digit is d}`
  for d in 1..9.
- A clue of rank R whose number leads with d satisfies
  `below(d) + 1 <= R <= below(d) + cnt[d]`, where `below(d)` is the sum of
  `cnt` over smaller digits.
- Between two numbers, a smaller leading digit forces strictly less, and a
  larger one forces not less.

This is the reasoning behind Chris's marks on the opening: column 9 missing
9 caps the 9 bucket, so rank 35 leads with 9 and rank 34 with 8.

## The probe

A scratch script, not in the repo, subclassed `RankModel` and posted the
constraints above as **redundant** ones beside the existing pairwise
comparisons: a one-hot of each leading digit, `cnt[d]` tied to the edge
lines' missing digits, the bucket bounds on each clue, and leading-digit
implications onto each clue's strictly-less literals. Each run was one
worker with a 300 s limit, on 2026-10-22, at load average about 2 on the
shared box.

Opening board (`finders/doppelganger_rank/fixtures/opening_9x9.json`):

| encoding | check (finds 2 solutions) | 5 mark proofs (each infeasible) |
| --- | --- | --- |
| current | 2.7 s | 49.9 s (1.9, 13.9, 1.9, 8.7, 23.5) |
| + buckets | 6.7 s | 0.7 s |
| + buckets + lead implications | 3.1 s | 0.8 s |

Finding a solution is no faster, but a proof that no solution exists is
about 60 times faster. The hunt's last step on each seed and its minimiser
are such proofs.

On the four small fixtures (`infeasible_4x4`, `not_unique_4x4`,
`unique_4x4`, `tie_6x6`) the buckets + implications variant gave the same
status and the same mark verdicts as the current model. Those fixtures'
expected statuses come from the brute-force answer key.

## Limits

One 9x9 board and one run each, so the times are a measurement, not a
benchmark. The 6x6 and 9x9 board shapes share the edge-line structure;
nothing here depends on n beyond `cnt[0] = 4`.
