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

## Hybrid: the 4x4 answers (#782)

U-Bahn with Choco-Banana over grid cells and number cells, as spec #781 rules
it. One worker, this box, 2026-10-11. Every count below is an exhaustive pass
over the stated space, about 2 s; none is sampled or capped.

- **The space.** The whole 4x4 board with no condition: 24 edges, 2^24 =
  16,777,216 edge sets. The 131,072 the spec names is the conditioned space
  above (17 free edges), not the board; the controller ruled on #782 that
  "no condition" means the whole board. `brute.no_dead_end` reaches it by
  dropping a cell left with one arm as it goes, which leaves **16,372** edge
  sets; `hybrid.py`, the solver-free rule reader, judges each of them.
- **4x4 holds valid hybrid grids: 18.** Of the 16,372, 15,593 are U-Bahn
  networks and **18** are valid hybrid grids. **8** of the 18 have exactly 2
  crosses in r2, the conditioned space above. With the blank strip on, **8**
  of the 18 stay valid and no other grid becomes valid.
- **Circle conditions**, in the uniqueness check's words:

  | Circled cells | Grids | Class |
  | --- | --- | --- |
  | none | 18 | `not_unique` |
  | `r2c2` | 4 | `not_unique` |
  | `c1:turn r2c4` | 1 | `unique` |
  | `r1:turn r4c2` | 1 | `unique` |
  | `r2c2 r2c4` | 0 | `infeasible` |
  | `c4:turn r4:turn` | 0 | `infeasible` |
  | `r1c1` | 0 | `infeasible` |

  No single circled cell gives exactly one grid: each of the 12 cells that
  can be circled in any grid can be circled in 2, 4 or 5 of them. Only turn
  number cells and grid cells are ever circleable at 4x4.
- **Commands.**

  ```
  uv run finders/ubahn/brute.py 4 4 --circles "r2c2" \
      --circles "c1:turn r2c4" --circles "r1:turn r4c2" \
      --circles "r2c2 r2c4" --circles "c4:turn r4:turn" --circles "r1c1"
  uv run finders/ubahn/brute.py 4 4 --blank-strip
  ```

  `--draw` adds a drawing of every valid grid. `test_ubahn_brute.py` pins
  every number above but the 15,593.
- **Two programs agree.** A throwaway script kept outside the repo listed all
  2^24 edge sets with numpy, filtered dead ends by bit counts and judged the
  rest with rule code of its own (a value matrix, regions by label
  propagation). It gave the same 16,372, the same 18 grids edge for edge, and
  for each grid the same cells that can be circled. The 8 in the conditioned
  space I also counted by eye from the 18 drawings.
- **The pruning is checked against the unpruned list** on the 3x4 board,
  where both fit in the test: the same edge sets, the empty one included.

Worker's choices, none a ruling:

- **A region whose box holds the corner is reported as needing an icon
  cell.** An icon cell is a wall, so the failure is always an even region
  that is no rectangle; the reader gives it its own reason when the region's
  bounding box reaches from one side's number cells to the other's.
- **Cells are named `r2c3`, `r2:turn`, `c3:cross`**, and held as `(r, c)`
  with a number cell's strip as a negative index, so the blank strip adds
  cells without moving any.
- **`failures` lists every broken rule**, and `why_not_hybrid` is its first.
  The tests need the whole list to show a grid breaks one rule only.

## Hybrid: the CP-SAT finder (#783)

`hybrid_model.py` is the plain flow model with the hybrid's rules on top, and
`hybrid_finder.py` puts it on the hunt protocol and adds `classify`. One
worker, this box, 2026-10-11.

- **It matches the 4x4 answers.** Listed by solve, forbid, re-solve until
  infeasible, the model gives the brute force's grids edge for edge: the 18
  with no condition, the 8 with the blank strip, the 8 with 2 crosses in r2,
  and each of the seven circle conditions above, whose `classify` words are
  the table's. `test_ubahn_hybrid_model.py`, about 15 s.
- **No tiny board has a circle in a banana.** By brute force, no valid
  grid of 3x3, 3x4, 3x5, 3x6, 4x4 or 4x5 has an odd cell whose value is its
  region's size (0, 4, 0, 49, 18 and 124 valid grids; 4x5 takes 78 s). So
  that case is tested on 5x5: with r1c2 circled the model has exactly one
  grid, checked by hand, where r1c2 is a branch in a bent banana of three.
  The model alone, not a second program, says it is the only one.
- **5x5 has 31 valid grids** by the model's own listing, run to infeasible
  (19 s); no enumeration confirms the count.
- **The circle rule past any enumeration.** A grid the model found is pinned
  in the model edge by edge, and the model must then take a circle exactly
  where the rule reader says the cell's value is its region's size. Run by
  hand over every board cell of 12 grids at 6x6, 10 at 7x7 and 8 at 5x8: no
  disagreement. The 7x7 and 5x8 grids held 4 circles in bananas, 2 on grid
  cells and 2 on number cells, all of value 3. The test keeps a smaller run (3 grids at
  6x6). This is a sample of grids, not a proof of the encoding.
- **The spec's example condition has no grid, by this model.** 7x7 with
  `r6:straight r6:turn r7:straight r7:turn` circled is infeasible, in half a
  second by `classify` and about 2 s per seed in a hunt, and so is the three
  without `r7:turn`. Every single circle, every
  pair and the other three triples have more than one grid. One engine says
  so; nothing enumerates a 7x7. Chris confirmed on 2026-10-11 that the four
  circles were read correctly from his picture and that icon cells are in no
  region, so no grid stands as that layout's result. One fact by hand: a
  bottom row's turns come in pairs, so `r7:turn` is always even.
- **First timings, a handful of seeds, not a measurement.** A grid for a
  seed with no condition: about 0.2 s at 6x6 and 0.35 s at 7x7, process
  start included, 4 seeds each, all found.

Worker's choices, none a ruling:

- **The board's only symmetry is the reflection in the main diagonal.** The
  number cells sit above and on the left, so a left-right mirror image moves
  the grid away from its row numbers: of the 18 grids at 4x4, 8 have a mirror
  image that is not valid, and every transpose is valid. The hunt dedupes
  under that reflection when the board is square, every circle's image is
  circled and there is no piece-count condition; otherwise under nothing. A
  piece-count condition names a row or a column, which the reflection swaps.
  The plain finder still dedupes under D4 whatever its condition (below).
- **A circle is one encoding for both parities**: a membership boolean per
  cell within reach, closed under same-parity neighbours, connected by a flow
  from the circled cell, as many as the cell's value. The chocolate and
  banana rules shape the region, so a circle in a chocolate needs no list of
  rectangles and a circle in a banana no list of polyominoes.
- **A hybrid seed is one solve, with no uniqueness proof.** The finder
  returns valid grids; whether a set of conditions is a puzzle is `classify`'s
  question.
- **`classify` gives each of its two solves the whole time limit**, as the
  plain uniqueness check does, so it can take twice `--timeout`. A limit of
  zero or less is `timeout` before any solve.
- **`--circles` takes one quoted list**, in `brute.py`'s cell names.
- **`model.py` gained `sample` and `network_uniqueness`**, the plain finder's
  own steering and uniqueness tail moved there unchanged so the hybrid calls
  them; `network.from_drawing` moved out of the rule reader's test.

## Hybrid: the PySAT engines (#784, #785)

`hybrid_sat.py` states the hybrid's rules as clauses over `sat_model.py`'s
network rules and runs them on CaDiCaL two ways: `--engine pysat-lazy`
refuses a full grid whose network is in several parts with a connectivity
cut and solves on, and `--engine pysat-propagator` adds a propagator that
raises a conflict during the search. One thread, this box, 2026-10-11.

- **Both match the 4x4 answers.** Listed by solve, cut or forbid, re-solve
  until infeasible, each engine gives the brute force's grids edge for edge:
  the 18 with no condition, the 8 with the blank strip, the 8 with 2 crosses
  in r2, and each of the seven circle conditions, whose `classify` words are
  the table's. `test_ubahn_hybrid_sat.py`, about 17 s.
- **Connectivity is at work on that listing.** Listing the 18 on the lazy
  engine adds 4 connectivity cuts. On the propagator engine it raises 10
  conflicts while some edge is still undecided, and adds 1 cut.
- **5x5 has 31 valid grids on both engines, the CP-SAT engine's count.**
  Three engines now give 31, the PySAT ones in under a second; no enumeration
  confirms it. With r1c2 circled both keep the bent three alone. On the lazy
  engine every one of the 65 board cells circled alone keeps exactly the
  grids of the 31 that the rule reader keeps.
- **6x6 has more than 100,000 valid grids.** A listing capped at 100,000
  reached its cap in 91 s on the lazy engine; the count is capped, not a
  total.
- **The circle rule past any enumeration.** A grid an engine found is pinned
  in the clauses edge by edge, and the clauses must then take a circle
  exactly where the rule reader says the cell's value is its region's size.
  The test runs it on a 7x7 and a 10x10 grid that hold number cells which
  can be circled in an odd region, three of value 3 and one of value 5, and
  on a 7x7 grid where a cross ends an even region of 5 cells in a row, which
  a count one step too short would take for a region of 4. No disagreement.
- **The spec's example condition has no grid on these engines either.** The
  controller asked for this as the independent check on the CP-SAT claim
  above (#784, comment of 2026-10-11): one core, 60 s limit.

  ```
  uv run finders/ubahn/hybrid_finder.py classify --rows 7 --cols 7 \
      --engine pysat-lazy --timeout 60 \
      --circles "r6:straight r6:turn r7:straight r7:turn"
  uv run finders/ubahn/hybrid_finder.py classify --rows 7 --cols 7 \
      --engine pysat-lazy --timeout 60 \
      --circles "r6:straight r6:turn r7:straight"
  ```

  | Circled cells | `pysat-lazy` | `pysat-propagator` | `cpsat` |
  | --- | --- | --- | --- |
  | `r6:straight r6:turn r7:straight r7:turn` | `infeasible` | `infeasible` | `infeasible` |
  | `r6:straight r6:turn r7:straight` | `infeasible` | `infeasible` | `infeasible` |

  Each PySAT run took about 0.35 s and each CP-SAT run about 0.75 s, process
  start included; none came near the limit. The `pysat-propagator` and
  `cpsat` columns are the same two commands with `--engine` changed, `cpsat`
  with `--workers 1`. On the lazy engine every single circle, every pair and
  the other three triples of the four read `not_unique`, as the CP-SAT engine
  has them. So three engines agree, but two of them share every clause but
  connectivity, and still nothing enumerates a 7x7.
- **How independent the check is.** The chocolate, banana and circle rules
  here were written from spec #781 and from `hybrid.py`; `hybrid_model.py`'s
  rule code was not read. What was read of the CP-SAT engine: its `build`,
  `grid` and `classify` signatures, its test, and this log, including the
  line below that describes its circle encoding in words. Shared with it by
  design: the rule reader, the brute force, and the spec's two rules of
  thumb (the 2x2 rule for chocolate, one clause per rectangle for banana).
- **First timings, a handful of seeds, not a measurement.** A grid for a seed
  with no condition, 20 seeds each, all found, in one process with no process
  start:

  | Board | `pysat-lazy` s per seed | Cuts | `pysat-propagator` s per seed | Conflicts |
  | --- | --- | --- | --- | --- |
  | 6x6 | 0.03 | 17 | 0.05 | 154 |
  | 7x7 | 0.06 | 5 | 0.15 | 325 |
  | 8x8 | 0.06 | 12 | 0.12 | 132 |
  | 10x10 | 0.13 | 29 | 0.24 | 152 |

  The first 3,000 grids of 6x6, capped there: 1.7 s with 122 cuts on the lazy
  engine, 3.9 s with 131 conflicts and 30 cuts on the propagator engine. The
  propagator is written in Python and is called on every edge the solver
  assigns. The clauses take 0.05 s to build at 10x10.

Worker's choices, none a ruling:

- **The engines are named `pysat-lazy` and `pysat-propagator`.**
- **The lazy engine is a plain loop, not PySAT's lazy propagator.** It
  solves, flood fills the grid in Python, adds the cut and solves again on
  the same solver. #776 measured that `is_lazy = True` did not stop the
  callbacks into Python during the search and named this loop as the way
  round them. The cut clause itself is the prototype's, moved into
  `sat_model.cut_clauses` so both callers share it.
- **A circle counts its region, in rounds.** Round 0 reaches the circled
  cell; a cell is reached in a round when it has the circled cell's parity
  and it or a cell beside it was reached the round before. After as many
  rounds as the cell's largest value, the cells reached are counted in unary
  and the count equals the value. So the spec writer's "a rectangle of that
  area covering the cell" for a circle in a chocolate is not listed: the
  chocolate clauses already make the region a rectangle.
- **A number cell's value is a unary count**, and its parity is read off the
  count, so the circle rule and the parity share one counter.
- **A seed steers the phases, not the order.** The seed picks which way each
  edge is tried first (`set_phases`); CaDiCaL picks the order. The CP-SAT
  engine fixes the order too. 20 seeds gave 20 different grids at each of
  6x6, 7x7, 8x8 and 10x10, and 12 seeds reached all 4 grids of 4x4 with r2c2
  circled.
- **`classify` has one time limit for both solves**, as `sat_model.py`'s
  check has, where the CP-SAT engine gives each solve the whole limit. A
  timing that compares the engines' `classify` has to allow for that.
  `--workers` is taken and ignored: CaDiCaL runs on one thread.
- **What the two counts mean.** `cuts` counts connectivity cuts, clauses
  added for a full set of edges in several parts. `conflicts` counts what the
  propagator raised while some edge was undecided; one it raises on a full
  set of edges is counted as a cut.
- **The propagator's reason clause.** With the cells one edge that is on
  reaches over edges not turned off, and another edge that is on outside
  them: not both on, or some edge leaving those cells is on. It holds for
  every network whatever is assigned, so a wrong reading of the solver's
  state could cost a conflict but never a grid. The propagator only raises
  conflicts; it forces no edge on.
- **What no test sees of the propagator.** Two planted bugs in its
  bookkeeping pass every test: forgetting that a fixed edge outlives a
  backtrack, and keeping one decision level too many. Either leaves it with
  a wrong picture of the search, which costs conflicts and never a grid, and
  the agreed tests read grids and counts only. A third, never un-assigning on
  backtrack, is caught: the propagator then adds 131 cuts on the 4x4 listing
  where the lazy engine adds 4, and the test holds it under the lazy
  engine's count. Checked once by hand instead: after each of 378
  satisfiable solves (4x4, 6x6, 8x8, no condition) the propagator's edges
  were the solver's model, every edge, with fixed edges among them.
- **The propagator engine's 5x5 circle sweep is every fifth cell** plus r1c2,
  not all 65: it runs the lazy engine's clauses, and the full sweep on it
  would add about 8 s to the build loop.

## Hybrid: the picture (#791)

`hybrid_finder.py render DIR` draws each example of a hunt as
`DIR/renders/<seed>.png`; `--seed N --png FILE` draws one. Chris asked for
the picture on 2026-10-11 ("render that grid", "also render the choco
banans", "the renderer should also circle valid circles", "make the turns
look more connected"). No solver runs: values, regions and valid circles are
`hybrid.py`'s.

Worker's choices, none a ruling:

- **A given circle's ring is purple and 7 px, a merely valid circle's red and
  4 px.** Colour and weight both differ, so the two can be told apart in
  greyscale too.
- **A grid that is no hybrid grid on the board drawn is refused**, with the
  rule reader's reason, and nothing is written. So a chocolate in a picture is
  always a rectangle. `--blank-strip` on a four-strip record redraws the
  regions over five strips, and most four-strip grids break there (10 of the
  18 at 4x4): those are refused with the reason, not drawn.
- **`--blank-strip` adds the strip; a record of a hunt that had it on is
  drawn with five without the flag.**
- **A directory's pictures go to `renders/`**, the directory the driver's own
  `render` hook writes, under the same `<seed>.png` names, and a rerun
  replaces the set. The hybrid finder has no `render` hook: a hunt writes no
  picture until the command is run.
- **Tints past the eighth banana are generated** (pale hues a golden-ratio
  step apart), so no two bananas of one picture share a tint; the first eight
  are the prototype's.
- **A track bar is 8 px and runs 4 px past each cell centre**, as in the
  picture Chris was shown. A ring on a grid cell is drawn under the track.

## Hybrid: at least N banana regions (#792)

`--min-bananas N` asks for N or more separate banana regions, counted over
grid cells and number cells together as `hybrid.regions` finds them. One
thread, this box, 2026-10-11.

- **The 4x4 answers**, an exhaustive pass over the 18 valid grids: 16 have
  one banana region and 2 have two, the two being each other's image in the
  main diagonal. With the blank strip all 8 have one.

  | Asked for | Grids | Class |
  | --- | --- | --- |
  | at least 1 | 18 | `not_unique` |
  | at least 2 | 2 | `not_unique` |
  | at least 2, `r2c4` circled | 1 | `unique` |
  | at least 3 | 0 | `infeasible` |
  | at least 2, blank strip | 0 | `infeasible` |

  ```
  uv run finders/ubahn/brute.py 4 4 --min-bananas 2 --circles "r2c4"
  uv run finders/ubahn/brute.py 4 4 --min-bananas 3
  uv run finders/ubahn/brute.py 4 4 --blank-strip --min-bananas 2
  ```

  `test_ubahn_hybrid_bananas.py` pins the table on the brute force, on each
  of the three engines and on the CLI. `brute.py` refuses an N under 1, as
  the finder does. A hunt on 4x4 asked for 2 writes one
  example, since it dedupes under that reflection.
- **5x5**, listed in full by `pysat-lazy` (31 grids) and counted by the rule
  reader: every one has 2 banana regions or more, 6 have 3 or more, 4 have 4
  or more, 4 have 5 or more, 2 have 6, none has 7. Each PySAT engine lists
  exactly those grids for every N from 1 to 7, and `cpsat` gives the same
  class.
- **With a piece count**, 5x5 again: `2:branch:r1` leaves 8 grids, 7 with
  two banana regions and one with six, so asking for 3 as well leaves
  exactly one, and every engine says `unique` with that grid.
- **With the blank strip** no 5x5 grid exists, so the test goes to 6x6 by
  seed (four seeds an engine, a sample): each grid asked for 3 passes the
  rule reader on the board with the strip.
- **The encoding: labels, not a count and not a cut.** An odd cell takes
  one label or more out of N, an even cell none; two odd cells side by side
  take the same labels, so a region's cells all take the same ones; every
  label is taken by some cell. On the PySAT engines a cell takes label k
  only when a cell before it in reading order takes label k - 1: numbering
  the regions by their first cells, region i then takes no label past i, so
  the last label being taken needs N regions. The CP-SAT model states it
  another way, each odd cell taking exactly one label with no order. Either
  way a grid with N regions or more has such a labelling and one with fewer
  has none, so it is exact; every clause is local, so the solver builds the
  condition into the search and no finished grid is refused for it, on any
  engine. Worker's choice, not a ruling; the filer's other route, refusing a
  full grid with too few regions by a clause over the cells that would have
  to change, was not built or timed.
- **What the review changed.** The first PySAT version also kept each cell
  to one label by a clause per pair of labels. The correctness review
  deleted those clauses and every test stayed green: the order already
  implies them. They are gone, and the order is the clause the tests hold.
- **All three engines carry it**, so no engine refuses the flag.
- **Time per grid at 7x7**, `pysat-lazy`, no other condition, one grid per
  seed from seed 0, a 60 s limit on each solve, timed around the engine's
  `grid` call (model build included), one thread. Load on the box was about
  4 while it ran, so the seconds are for comparing rows, not a benchmark.

  | N | Seeds | Found | Timeouts | Reader passes | Median s | Mean s | Slowest s |
  | --- | --- | --- | --- | --- | --- | --- | --- |
  | none | 50 | 50 | 0 | 50 | 0.054 | 0.067 | 0.190 |
  | 2 | 50 | 50 | 0 | 50 | 0.074 | 0.088 | 0.212 |
  | 5 | 50 | 50 | 0 | 50 | 0.282 | 0.313 | 0.871 |
  | 8 | 50 | 50 | 0 | 50 | 0.919 | 1.012 | 3.706 |
  | 12 | 10 | 8 | 2 | 8 | 24.116 | 29.303 | 59.545 |

  The N = 12 row was asked for 10 seeds only. Its median, mean and slowest
  are over the 8 grids found, and its 2 timeouts are timeouts, not grids
  that do not exist. Nothing here says what the most banana regions a 7x7
  grid can have is.

  ```
  uv run finders/ubahn/time_bananas.py run --min-bananas 0,2,5,8 --seeds 50 \
      --progress docs/research/2026-10-11-u-bahn-min-bananas-timing/pysat-lazy-7x7.jsonl
  uv run finders/ubahn/time_bananas.py run --min-bananas 12 --seeds 10 \
      --progress docs/research/2026-10-11-u-bahn-min-bananas-timing/pysat-lazy-7x7.jsonl
  uv run finders/ubahn/time_bananas.py report \
      docs/research/2026-10-11-u-bahn-min-bananas-timing/pysat-lazy-7x7.jsonl
  ```

  The rows are in that file. An earlier run on the first encoding, with the
  one-label clauses, is not kept; its N = 2 and N = 5 medians were 0.083 s
  and 0.311 s.
- **What the seeds gave without the condition** (a sample of 50, not the
  board): 14 grids with one banana region, 14 with two, 10 with three, 10
  with four, 2 with five. Asked for 5, the 50 grids had 5 (43), 6 (4) and
  7 (3).
- **A hunt's `run.json` names the condition only when it is asked for.**
  The driver refuses to resume a hunt whose config differs, and a hunt from
  before the condition has no such key. Every record carries `min_bananas`;
  a record without it is read as asking for none, and one whose
  `min_bananas` is not a whole number of 0 or more is refused.

## Hybrid: what the spec's review changed (#781)

One review of the whole spec on `spec-781`, 2026-10-11. Its findings that
changed what a command does:

- **A repeat is the same network, not the same kinds.** The hunt's dedupe
  key was the grid of kinds, the plain finder's. Two networks can have the
  same kind in every cell and both be valid hybrid grids: the reviewer drew a
  6x6 pair that differs in four edges, and counted 104 shared keys among
  11,895 in the first 12,000 grids of a capped 6x6 listing (not the board's
  total); 4x4 and 5x5, listed in full, have none. The second network of such
  a pair was dropped as a repeat. The key is now every cell's east arm and
  south arm, and the diagonal reflection swaps the two. The controller's
  choice, not a ruling: flag it if a repeat should mean the kinds.
- **The default engine is `pysat-lazy`** (Chris's ruling, 2026-10-11, on the
  timing in the optimization-queue note). `cpsat` and `pysat-propagator`
  stay selectable.
- **The timing report counts every seed on file.** A second run over other
  seeds into one progress file used to keep the later run's seed count and
  every solve, so a timeout among them lost its capped label. A progress
  line of an unknown kind is now refused.
- **`render` refuses a record with no `circles`**, a plain hunt's, by name
  and with exit 2.

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
