# Grid finder lessons

What to do before writing the next finder. Drawn from the counting shaded all-visible
hunt (2026-09-15), which went from one example in 25 minutes to 234 verified
examples in 20 minutes on 8 cores. The run log, with the approaches that
failed and their numbers, is `docs/research/2026-09-15-counting-shaded-all-visible.md`.

## Preflight — answer these in writing before spending compute

This list exists because the lessons below were already written when a later
hunt re-derived six of them the hard way
(`docs/research/2026-09-16-counting-shaded-connected-decision-log.md`). Knowing them is
not the problem; consulting them is. Answer these before the first long run,
and keep a decision log as that one does — what was decided, what it rested on,
what it cost.

1. **What are the known bounds of the base puzzle, and does your variant still
   obey them?** A theorem costs nothing where it applies, and misleads where it
   does not. The 17-givens minimum (McGuire, Tugemann & Civario 2012) is a
   result about a board carrying **digit givens and nothing else**. Any extra
   clue type — a renban, a whisper, a shaded cell the solver must still locate —
   carries information the theorem does not count, and such puzzles are unique
   with far fewer givens. That is the normal case in this repo, so the bound
   usually does *not* apply.
   It applied to the connected counting shaded hunt only because of a reduction proved
   first: with every shaded cell visible the shaded cell rule is redundant (all solutions
   agree on the shaded cells, so the rule has the same truth value in each), and
   the board really is a plain sudoku whose givens are the shaded cell digits. State
   the reduction before borrowing the bound.
2. **What produced any corpus you are about to reason from, and with what
   flags?** A corpus inherits its generator's parameters. A distribution bound
   read off a catalogue whose generator had `--min-shaded 26` is that flag, not
   a fact.
3. **Does your sampler cover the space or one orbit of it?** A sampler built
   from the puzzle's own symmetry group produces isomorphic outputs that look
   different. Check by isomorphism, not by eye.
4. **Which lesson below does this plan contradict?** Name it and say why this
   case differs. "More givens should help uniqueness" is already falsified.
5. **What would make your result an artefact, and what control rules that
   out?** Then check the control actually changes the model — a control that
   cannot turn the constraint off is not a control.
6. **Can the solver answer this directly? Then do not answer it from your
   data.** The costliest habit in the counting shaded hunt was reporting bounds read off
   a corpus — "no unique example below 25", "the window is 18–21" — when one
   feasibility solve per size settled it in seconds and contradicted both
   guesses. A sample maximum is a fact about the sample. Ask the oracle, and
   quote the sample only when no oracle exists.
7. **Derive the cheap necessary conditions before searching.** They prune far
   more than they cost. In counting shaded, "every digit 1–8 must appear on a shaded cell" —
   two lines of reasoning from the digit-swap argument — turned the search from
   one configuration per 300 s into thirteen per 150 s, *and* proved five sizes
   impossible outright.

## Model

- **Search the smallest object that determines the puzzle.** In counting shaded every
  shaded cell shows its shaded-neighbour count, so the shaded cell shape alone fixes all the
  givens and the grid never needed to be a search variable. That replaced a 7 s
  CP-SAT solve per candidate with a millisecond check. Before modelling, ask
  what the minimal generator of the clue set is, and search that.
- **Uniqueness is a "no other solution" condition, so no single CP-SAT model
  states it.** Two routes: counterexample cuts (solve, find a second solution,
  cut, repeat), or a bounded solution counter inside a local search. Cuts only
  pay when the master solve is cheap *and* each cut kills a family rather than
  one point. In counting shaded the master could always move the grid to dodge the cut:
  3-7 s per round, no convergence in 5 minutes. The counter plus local search
  won outright.
- **Test a monotone shortcut before betting on it.** Uniqueness only improves
  as givens are added, which argued for maximising the clue count. One 5-minute
  measurement killed it: the densest shape (35 shaded cells, proven bound 39) still
  had 8 solutions.
- **Feasibility beats minimality when two lessons conflict.** Searching the
  smallest determining object is right only while every candidate it produces
  can actually be realised. Shape-only search for connected counting shaded returned
  admissible shapes that no grid completes — 0 solutions — because the shape
  model could not see solvability. An unsolvable candidate is not a candidate.
- **Seed local search from a joint feasibility model.** A random shape is
  almost always unsolvable; a CP-SAT model holding grid and shape together
  makes every start solvable, at a few seconds each.

## Search loop

- **Profile before tuning the metaheuristic.** In counting shaded 99.85 % of moves died
  on the feasibility check, not the solution count, while temperature and caps
  were being tuned. Count rejections by cause first.
- **Cool on elapsed time, not step count.** A per-step decay tuned for a Python
  loop froze the C port in under a second at 500k moves/s. Time-based cooling
  carries across a 90x speed change unchanged.
- **Compare strategies by hits per CPU-minute, over enough runs.** Four climbs
  is noise: two counting shaded approaches "won" on 6-climb samples and lost later.

## Speed

- **A hot loop in `ctypes` C is worth ~90x and adds no dependency.** The
  counting shaded counter is a bitmask DFS of a few dozen lines built with the system
  `gcc` (`finders/counting_shaded/counting_shaded_fast.c`, loaded by `fastclimb.py`).
- **Pair it with a parity test.** Check the C against the Python on thousands
  of random inputs before trusting a result, as with the soundness harness.

## Reading the solver

- **`OPTIMAL` is a claim about your model, not about the puzzle.** A bound that
  will constrain future search earns a second encoding that shares nothing with
  the first — different variable shape, different constraint form, different
  auxiliary structure. The counting shaded 26-cell ceiling was re-proved that way
  (`finders/counting_shaded/recheck_ceiling.py`, `--exactly 27` INFEASIBLE).
- **`UNKNOWN` is a timeout, never a proof.** Only `INFEASIBLE` proves a band
  empty. Never let a timeout print as exhaustion, and never let one count as
  "this clue can be dropped" — `minimal.py` and `zombo_brainanas_cpsat.py`
  both keep the clue on a timeout.
- **Check a geometric encoding against a direct implementation.** Flow
  connectivity and spanning-tree connectivity were each checked against flood
  fill on hundreds of random shapes (300/300, 200/200) before any ceiling drawn
  from them was believed.
- **Connectivity: prefer an encoding to lazy cuts.** A flood-fill cut kills one
  component layout and the solver finds another — 2073 cuts in 120s with no
  connected shape, against 77s for single-commodity flow. Size the flow domains
  to the real maximum, not to the cell count.

## Counting what you found

- **Deduplicate under the symmetries that preserve both the houses and the
  constraint's own adjacency.** For a king-adjacency rule that is the 8
  rotations and reflections; band and stack swaps break adjacency, so they do
  not apply.
- **Report nearest-neighbour distance, not just a count.** Restarting from
  previously found examples mostly re-finds them: in counting shaded fresh seeds gave
  128 distinct examples against 102 from pool restarts, and 25 of 234 examples
  sat within 2 toggles of another.
- **Verify the whole catalogue with code that shares nothing with the
  finder.** `finders/counting_shaded/verify_all.py` recomputes the givens and
  re-checks uniqueness with a different CP-SAT encoding.
