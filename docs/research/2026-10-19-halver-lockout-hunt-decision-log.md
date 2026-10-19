# Halver + lockout-line hunt: decision log

Spec #52, ticket #56. The finder is `finders/halver_lockout/hunt.py`, its
candidate lines `candidates.py` (#55), its rule check `rules.py` (#54) and
its backtracking check `brute.py` (#59). The board starts empty: a 9x9 with
no givens, no given halvers and no lines. Facts it builds on:
`docs/research/2026-10-19-halver-lockout-check-notes.md` and
`docs/research/2026-10-16-halver-between-truths.md`.

Every choice below marked **worker's choice** was made by the #56 worker, not
ruled by Chris. Flag any you disagree with.

## Preflight (`docs/agents/grid-finder-lessons.md`), answered before the first hunt run

1. **Known bounds, and does the variant obey them?** The 17-givens minimum
   does not apply: the board has no givens at all, and the halvers and the
   lines carry information the theorem does not count. What applies is the
   halver board itself: 46,656 ways to place the nine halvers (truths note),
   and each halved value (0.5, 1.5, ..., 4.5) on exactly one cell of the
   board, since the nine halver digits all differ. The cell bound of the
   between hunt (44 free cells on Chris's board) has no analogue here: the
   empty board has 81 free cells.
2. **What produced the corpus you reason from?** No corpus. The reasoning
   below is arithmetic on the rules. The one prior run is #54's: a
   target-grid loop on the empty board that reached `unique` at 23 lines
   (`finders/halver_lockout/fixtures/unique_23.json`), whose backtracking
   check took 202.8 s (check notes). It was a single seed, so it shows that
   a finish exists, not how often one does.
3. **Does the sampler cover the space or one orbit?** Targets come from the
   shared layer's `HalverModel.sample`, a one-worker CP-SAT solve steered by
   random digit hints, as in `halver_between`. That hunt measured 10 distinct
   targets from 10 seeds, and the same solve with no hints gave one grid 10
   times. The draw is not uniform and nothing here claims it is. The empty
   board has the full sudoku symmetry group; no claim is made that two hits
   are different puzzles beyond their line sets differing.
4. **Which lesson does this plan contradict?** "Cuts only pay when each cut
   kills a family and the master cannot dodge it." The target-grid loop is a
   cut loop with a fixed master: every line holds in the target, so each line
   removes the second solution for good. It converges unless it runs out of
   lines that separate. On the between board it ran out of cells; here a
   lockout line is weak (check notes: one line's narrowing barely narrows),
   so the expected failure is many lines, a slow check and a slow `verify`,
   not space.
5. **What would make a result an artefact, and what control rules it out?**
   A modelling bug in the CP-SAT model could call a board unique when it is
   not. `verify` re-reads every hit with `brute.py`, the backtracking check
   that shares no code with the model, and checks that its one solution is
   the hit's. Controls: the tests take a hit's last line away and `verify`
   must find 2 solutions, and give `verify` an illegal line, a solution that
   is not the backtracking check's and no search time, and it must refuse
   each. A timeout is never unique and never a pass.
6. **Can the solver answer this directly?** Not as asked: "some set of lines
   makes the board unique" is an exists-forall question no single solve
   states. A hit proves a finish exists; no hit is reported as "none found",
   never as impossible.
7. **Cheap necessary conditions first:** below.

## What the rules force, before any search

Values are a halver's digit / 2 and any other cell's digit, so the values a
cell can take are 0.5, 1, 1.5, ..., 4.5 (halved, odd doubled values) and
1, ..., 9 (normal). The code compares doubled values: 1 to 10, then 12, 14,
16, 18. A lockout line needs diamonds at least 4 apart in value and every
body cell strictly outside the closed range between them. Counted by hand
over the 14 values (31 ordered pairs have a gap of at least 4):

- **One pair can never be a line: a halved 1 (0.5) and a normal 9.** Nothing
  lies outside [0.5, 9], so the body has no value. The other 30 pairs leave
  room.
- **The lower diamond is at most 5 and the upper at least 4.5.** Every pair
  with a gap of 4 straddles the middle.
- **A body has at most 5 cells in any one row, column or box,** on every
  pair. A house holds distinct digits and at most one halver, so the cap is
  the digits whose normal value lies outside plus one halved value outside
  when one exists. The cap is 5 on 10 pairs, 4 on 8, 3 on 6, 2 on 4 and 1 on
  2: (0.5, 8), a halved 1 and a normal 8, whose only outside value is a
  normal 9, and (1, 9), a normal 1 and a normal 9, whose only outside value
  is a halved 1.
- **The middle values almost never sit on a body.** A normal 5 is a body
  value only between a halved 1 and a halved 9 (0.5, 4.5). A halved 9 (4.5)
  is a body value only between a normal 5 and a normal 9. A normal 4 or a
  halved 8 (4) only below (4.5, 9) or (5, 9). So a cell whose target value
  is near the middle is pinned by being a diamond, or by a line whose
  diamonds are themselves on single cells of the board.
- **What the halver rule does to these numbers.** Each halved value is on
  one cell of the whole board, so a pair that needs a halved diamond (any
  odd doubled value) names that one cell, and every line on that pair
  shares it as a diamond. A body that needs a halved value (a halved 1
  below a pair, for instance) has at most one such cell per house and at
  most one on the board.
- **Bodies may sit on both sides of the range.** A body cell below the
  smaller diamond and one above the larger are both legal, so a lockout
  body does not use the between line's one-sided window. This is the
  check notes' reason a line narrows little: one body cell keeps most of
  its 18 doubled values.

What this rules out for the walk: the (0.5, 9) pair and any body of six or
more cells in one house never reach a candidate, because the walk only keeps
a body every target value of which is outside the diamonds' range, and the
target obeys these counts. Nothing above prunes the search further than the
walk already does; its use is to read the hunt's lines. A finish must pin
every middle-valued cell by a diamond or by a line on the unique halved
diamonds, so a hit should show diamonds on middle values and long bodies on
extreme ones.

The between hunt's line economy (truths note, section 6) found that cells,
not solver time, run out. That is checked in the pilot below, not assumed.
