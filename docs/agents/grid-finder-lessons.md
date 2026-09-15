# Grid finder lessons

What to do before writing the next finder. Drawn from the Ghosts all-visible
hunt (2026-09-15), which went from one example in 25 minutes to 234 verified
examples in 20 minutes on 8 cores. The run log, with the approaches that
failed and their numbers, is `docs/research/2026-09-15-ghosts-all-visible.md`.

## Model

- **Search the smallest object that determines the puzzle.** In Ghosts every
  ghost shows its ghost-neighbour count, so the ghost shape alone fixes all the
  givens and the grid never needed to be a search variable. That replaced a 7 s
  CP-SAT solve per candidate with a millisecond check. Before modelling, ask
  what the minimal generator of the clue set is, and search that.
- **Uniqueness is a "no other solution" condition, so no single CP-SAT model
  states it.** Two routes: counterexample cuts (solve, find a second solution,
  cut, repeat), or a bounded solution counter inside a local search. Cuts only
  pay when the master solve is cheap *and* each cut kills a family rather than
  one point. In Ghosts the master could always move the grid to dodge the cut:
  3-7 s per round, no convergence in 5 minutes. The counter plus local search
  won outright.
- **Test a monotone shortcut before betting on it.** Uniqueness only improves
  as givens are added, which argued for maximising the clue count. One 5-minute
  measurement killed it: the densest shape (35 ghosts, proven bound 39) still
  had 8 solutions.
- **Seed local search from a joint feasibility model.** A random shape is
  almost always unsolvable; a CP-SAT model holding grid and shape together
  makes every start solvable, at a few seconds each.

## Search loop

- **Profile before tuning the metaheuristic.** In Ghosts 99.85 % of moves died
  on the feasibility check, not the solution count, while temperature and caps
  were being tuned. Count rejections by cause first.
- **Cool on elapsed time, not step count.** A per-step decay tuned for a Python
  loop froze the C port in under a second at 500k moves/s. Time-based cooling
  carries across a 90x speed change unchanged.
- **Compare strategies by hits per CPU-minute, over enough runs.** Four climbs
  is noise: two Ghosts approaches "won" on 6-climb samples and lost later.

## Speed

- **A hot loop in `ctypes` C is worth ~90x and adds no dependency.** The
  Ghosts counter is a bitmask DFS of a few dozen lines built with the system
  `gcc` (`docs/research/ghosts/ghosts_fast.c`, loaded by `fastclimb.py`).
- **Pair it with a parity test.** Check the C against the Python on thousands
  of random inputs before trusting a result, as with the soundness harness.

## Counting what you found

- **Deduplicate under the symmetries that preserve both the houses and the
  constraint's own adjacency.** For a king-adjacency rule that is the 8
  rotations and reflections; band and stack swaps break adjacency, so they do
  not apply.
- **Report nearest-neighbour distance, not just a count.** Restarting from
  previously found examples mostly re-finds them: in Ghosts fresh seeds gave
  128 distinct examples against 102 from pool restarts, and 25 of 234 examples
  sat within 2 toggles of another.
- **Verify the whole catalogue with code that shares nothing with the
  finder.** `docs/research/ghosts/verify_all.py` recomputes the givens and
  re-checks uniqueness with a different CP-SAT encoding.
