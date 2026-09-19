# Counting shaded, all visible: a unique 31-cell grid with an 8 [verified]

Target (Chris, 2026-09-15): every shaded cell is visible and shows its digit; those
digits are the only givens and make the sudoku unique; one shaded cell holds 8.
A shape fixes its givens (each shaded cell shows its shaded-neighbour count), so this
is a search over shaded cell shapes.

## Result

`docs/research/counting_shaded/allvisible-hits.jsonl` line 0: 31 shaded cells, one 8 (r7c3).
`uv run --with pillow finders/counting_shaded/check_hit.py docs/research/counting_shaded/allvisible-hits.jsonl 0 sol.png puz.png`
recomputes the counts, checks the 8, and has CP-SAT (all-different model, no
code shared with the finder) enumerate solutions: exactly 1.

Puzzle: ![puzzle](shaded cells/allvisible-31-puzzle.png)
Solution: ![solution](shaded cells/allvisible-31-solution.png)

Not minimised: 31 is the first hit, not the fewest shaded cells.

## What worked and what did not

| approach | outcome |
|---|---|
| fix a random grid, CEGAR on shape (`allvisible.py` @ abccd56) | a grid admits only 1-13 shapes (3 grids sampled); master infeasible after 1 cut |
| joint grid+shape CEGAR (`allvisible.py`) with relabeling cuts and static unavoidable-set clauses (deadly rectangles, two-line cycles, band hexagons, band 3-cycles) | ~7 s per master solve; 41-63 cuts in 5 min, no unique; counterexamples stay 6-8 cells |
| shape hill climb, cap-200 counter, single toggles, 20+ shaded cell seeds (`shapes.py`) | best 22 solutions in 2 min |
| same, annealed from T=1, cap 2000 | worse: all 2000+ |
| same, T=0.1, toggle one cell or a cell plus a neighbour, 26+ shaded cell seeds | **hit in 165 s** (seed 3, climb 5); other climbs 13-980 |

Shape search wins because a uniqueness check on a fixed set of givens is a
millisecond bitmask count, while the CEGAR master re-solves a large CP-SAT
model per cut. Seeds come from the grid+shaded cell CP-SAT model so every seed is
solvable.

Run: `uv run finders/counting_shaded/shapes.py --seconds 240 --climb-seconds 40 --min-shaded 26 --seed 3 --out DIR`

## Next

- Minimise the shaded cell count: climb with the score (solutions, shaded cells) and accept
  removals that keep 1 solution.
- Rate-of-hits over more seeds, then decide whether the finder moves to
  `finders/` through the code lane.

## Dense shapes from CP-SAT (`dense.py`, 2026-09-15)

Maximise the shaded cell count in the grid+shaded cell model (10 s per solve, one worker,
random digit hints), check with the counter, cut the second solution, re-solve
up to 5 rounds per model. 300 s, seed 1: **30 solves, 0 unique.** Shaded cell counts
reached 27-33 (never proven optimal), second solutions differed in 4-30 cells.
The solver does not reach the 36+ shaded cells the idea needs within 10 s; whether
such shapes exist at all is untested. Box load average was 5-6 during the run.

## C climb harvest: 234 verified examples (2026-09-15)

- **Max density** (8-worker CP-SAT, 300 s): best 35 shaded cells, bound 39; the
  35-cell shape had 8 solutions. Density alone does not give uniqueness.
- **C climb** (`counting_shaded_fast.c` via `fastclimb.py`, parity-tested against
  `shapes.py` on 20 000 shapes): ~500k moves/s, ~90x the Python climb. With
  the Python cooling it froze in <1 s; cooling over the run (T 2 -> 0.05) with
  king-walk moves of up to 6 toggles gave 2 hits in 6 x 10 s climbs.
- **Harvest** (`charvest.py`): 8 processes x 1200 s, one worker each.
  Seeds 201-204 fresh CP-SAT seed every loop, 205-208 30 % fresh + pool
  restarts. Distinct after cross-process dedupe: fresh 128, pool 102.
  Fresh seeds win; pool restarts mostly re-find their own shapes.
- **Verified**: `verify_all.py` merged these with the earlier Python hits:
  **234 examples, 48 duplicates, 0 failures**, in
  `shaded cells/examples-verified.jsonl` (shape, givens, solution).
- Shaded cell counts: 25 (1), 26 (8), 27 (17), 28 (41), 29 (51), 30 (60), 31 (40),
  32 (15), 33 (1).
- Spread: nearest-neighbour toggle distance (under symmetry) median 8;
  25 examples are within 1-2 toggles of another.

Fewest shaded cells, 25: ![puzzle](shaded cells/allvisible-25-puzzle.png)
![solution](shaded cells/allvisible-25-solution.png)
