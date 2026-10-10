# U-Bahn finder: preflight and decision log

**Date:** 2026-10-10 · **Ticket:** #773 · **Code:** `finders/ubahn/`

The base model and one condition ("exactly N of piece P in row or column
K", P a piece or blank). Rules and the model's reasoning: `2026-10-10-u-bahn-cpsat-finder.md`.
This file answers the preflight in `docs/agents/grid-finder-lessons.md` and
records what was measured while building. No long hunt has been run.

## Preflight

1. **Known bounds of the base puzzle.** None found: the research note found
   no solver, generator or counting result for U-Bahn (its § 5, with the
   places it looked). No bound is borrowed.
2. **Corpus.** None is reasoned from. The only counts on file are the 4x4
   ones below, and they are an exhaustive pass over a stated space.
3. **Sampler coverage.** Not measured beyond the 4x4 space. One seed fixes a
   random order and polarity over the edge variables and takes the first
   network a fixed search reaches. On the 4x4 space 40 seeds gave 31 distinct
   examples and 9 duplicates under D4. On 6x6 it is unknown which share of
   the space the sampler can reach or how skewed it is.
4. **Lesson contradicted.** None. "Search the smallest object that determines
   the puzzle" is followed: the network is searched and every outside number
   is derived from it. Connectivity is an encoding, not lazy cuts.
5. **What would make a result an artefact.** A flow model that is too tight
   or too loose would report wrong uniqueness. Control: the spanning-tree
   encoding, and the exhaustive 4x4 pass below, which both encodings match
   network for network. `verify` re-proves each example with the tree
   encoding.
6. **Can the solver answer it directly?** Yes, and it does: uniqueness is a
   solve, forbid, re-solve on the edge variables per example, never read off
   a sample.
7. **Cheap necessary conditions.** Not added. The note's § 4.5 lists parity
   and row-boundary conditions; none is in the model, because no solve so far
   is slow enough to need one. A condition that makes proofs slow is the time
   to measure them.

## Measured

All on one worker, this box, 2026-10-10.

- **The 4x4 space with exactly 2 crosses in r2, exhaustively.** 131,072 edge
  assignments (the crosses are forced to r2c2 and r2c3, 17 edges free). The
  brute force in `finders/ubahn/test_ubahn_brute.py` finds **557** valid
  networks, **554** distinct full sets of outside numbers, **551** networks
  unique under their full set. That matches the three counts ticket #773
  quoted from a throwaway script, so two separate programs agree.
- **Flow and tree agree on that space.** Each lists exactly those 557
  networks by solve, forbid, re-solve, and each gives the brute-force verdict
  on all 554 sets of outside numbers. About 3.7 s per encoding to list, about
  2 s per encoding for the 554 verdicts.
- **That space cannot test connectivity.** The crosses' own cells leave no
  free 2x2 block, so no edge set in it has two separate loops: with the
  flow's edge gate or the tree's level rule deleted, and with the flood fill
  deleted from the brute force, the test still passed. A second exhaustive
  space covers it: 3x4, every one of its 131,072 edge assignments, with no
  blank in r2. 365 edge sets there have no dead end, 16 of them are not
  connected, and both encodings list exactly the 349 networks.
- **A 6x6 run, 20 seeds, `--exactly 2:cross:r2`, a 5 s cap no solve reached.**
  1.3 s wall clock in all: 16 examples, 4 seeds whose network was not unique,
  no timeout, no duplicate. Twenty seeds is a sample, not a rate.

## Decisions

- **Root.** The first used cell in reading order, stated as n² / 2
  implications, shared by both encodings. So the two encodings share the
  piece table, the number sums and the root, and differ in flow against
  levels.
- **Sampling is one worker, the proof takes `--workers`.** A seed then gives
  the same network on every run, which a resumed hunt relies on.
- **`verify` proves on one worker with the tree encoding**, so a verdict
  written by `hunt verify` is the same on every run.
- **Symmetry.** The dedupe key is the grid of kinds; a kind does not change under
  rotation, so permuting cells is enough. A square board takes `dedupe.D4`;
  any other board takes the four maps that keep its shape, because D4 would
  read a 2x8 as a 4x4.
- **Blank is counted (Chris's ruling on #773, 2026-10-10).** A condition may
  name blank, and each row and column carries a fifth outside number for its
  blank cells. It is the length less the other four, so the 554 distinct
  full sets and every uniqueness verdict are unchanged.
- **A condition is not symmetric, the dedupe is.** `2:cross:r2` holds on a
  network and its left-right mirror image, and the hunt keeps one of the two.
