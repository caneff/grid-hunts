# U-Bahn finder: optimizations to queue

Candidate speedups for the U-Bahn finder (`finders/ubahn/`, base model in
#773), written 2026-10-10 before the base model exists. **Nothing here is
measured.** Every entry is the controller session's reasoning from the model's
structure, the first research note
(`2026-10-10-u-bahn-cpsat-finder.md` §4) and
`docs/agents/grid-finder-lessons.md`. Each is a candidate to time, not a
decision; the solve-time rule applies: an addition stays only if it pays.

One data point exists: on 4x4 with two crosses in r2, a brute-force
enumeration found 557 valid networks, 551 of them unique under their full set
of outside numbers. If that rate holds on larger boards, the full-clue
uniqueness check is cheap and almost always passes, and the cost moves to
stripping and to hunts under few conditions. That is the first thing to
measure, because it decides which half of this list matters.

## 0. Measure first

- **Baseline on 6x6 and 8x8** once #773 lands: share of sampled networks that
  are unique under full outside numbers, time per sample, time per uniqueness
  proof, and where the proof time goes (connectivity or counts). Rejections
  counted by cause, as the lessons file asks. Measured in "Baseline at 6x6
  and 8x8" below (#777), except where the proof time goes: connectivity
  against counts is not split out there.

## 1. The uniqueness proof

- **Relax, then verify.** Ask for a second network with connectivity left out
  of the model. `INFEASIBLE` there proves uniqueness without paying for flow,
  since dropping a constraint only adds solutions. A second solution is flood
  filled: connected means not unique; disconnected means add a cut for that
  component and re-solve, or fall back to the full model after a few rounds.
  The cut is the family-killing one from the first note §4.3.
- **Static small-component bans.** The cheapest disconnected solutions are
  closed rings. For each 2x2 and 2x3 ring position: if its cells form the
  closed ring, every other cell is blank. A fixed set of clauses that removes
  the commonest counterexamples from the relaxed model.
- **Constants from full outside numbers.** Used-cell count and edge count are
  fixed by the numbers, so the flow domain is sized to the real maximum and
  both totals go in as equalities.
- **Per-line automaton.** One `add_automaton` per row over its cells, with
  state (east arm open, counts so far per type), and the same per column. It
  makes each line consistent with its own numbers and its arm matching in one
  constraint, where the table plus linear sums propagate separately. State
  count is bounded by the product of (number + 1) over the line's types.
- **Redundant counts** from the first note §4.5: row-boundary vertical-edge
  bounds, per-line parity, an even total of branches. Free rejects of a bad
  set of numbers before any solve.
- **Branching order.** A decision strategy on piece-type indicators in the
  lines whose numbers leave the fewest patterns, in place of the default on
  edges.

## 2. A second engine

- **Row-by-row frontier DP.** Sweep the board one cell at a time, carrying the
  open down-arms, the partition of those arms into connected groups, and the
  counts still owed. It counts solutions exactly, so it answers uniqueness
  with no solver and no flow, and is the natural "second encoding that shares
  nothing with the first". Width-limited: the state grows with the board
  width, so it suits boards up to about 8 wide; larger is unmeasured. A hot
  loop of this shape is what the lessons file ports to `ctypes` C.

## 3. Stripping outside numbers (when Chris calls for it)

- **Derivable numbers strip without a solve.** The blank count is the line
  length minus the other four. With every column number of a type shown, the
  last row number of that type is the total minus the others.
- **Counterexample cache.** Every second network found by a failed strip is
  kept. Before a trial set of numbers goes to the solver, test it against the
  cache: a cached network that fits the trial set proves non-uniqueness in
  microseconds. `finders/hunt/minimizer.py`'s `strip` takes any predicate, so
  the cache lives in the predicate; it holds none today.
- **One model, assumption literals.** Build the model once with an enable
  literal per outside number and pass the trial set as assumptions, in place
  of rebuilding per trial. Assumptions can weaken presolve, so this one needs
  a timing before it is believed.
- **Hints.** Give each re-solve the known network as a hint with the
  differ-on-some-edge constraint, so the solver starts beside the answer.

## 4. The hunt loop

- **Sample variety.** An unconstrained solve returns the dullest network. A
  random linear objective over the piece-type indicators, or a random target
  type grid as a hint, per sample.
- **Symmetry from the conditions.** When Chris's conditions are unchanged by
  a reflection or rotation of the board, add a lex-leader constraint for that
  subgroup so the solver does not find each grid several times; dedupe under
  the board symmetries still runs.
- **Splits over hunt workers.** The hunt driver's own `--workers` (default 3)
  with one solver thread each, split by seed or by a pinned first cell.

## 5. Later

- **A human-style solver** from the LMD technique guide (first note §5), for
  a difficulty rating. Not an optimization; listed so it is not forgotten.

## Suggested order

Section 0, then "relax, then verify" and the small-component bans, since they
attack connectivity, the one costly part of the base model. The frontier DP
next if 6x6 to 8x8 is where the hunts live. Section 3 waits for the first
stripping request.

## First measurements (2026-10-10, evening)

Run by the controller session with throwaway scripts, one core, box load
about 2.5. Small samples: read them as a direction, not a rate.

### Our CP-SAT uniqueness check against JWKNT/logical-solver

Ours is `model.uniqueness` from the #773 branch at `eb56995` (flow, and tree
beside it), one run each, model build included. Theirs is `runSolve` from
`tests/engine-node.js` at `0603a978`, cloned outside this repo (it has no
licence, so none of it is committed here), best of 3, 60 s limit. Puzzles: 5
random networks per size with every outside number shown, sampled from our
model with a random edge objective, which makes them dense (31 to 36 of 36
cells used at 6x6, 92 to 99 of 100 at 10x10).

| Size | Ours, flow | Theirs | Verdicts |
| --- | --- | --- | --- |
| 6x6 | 9 to 15 ms | 0.06 to 0.6 ms | agree 5 of 5; 3 unique |
| 8x8 | 31 to 81 ms | 0.3 to 40 ms | agree 5 of 5; 2 unique |
| 10x10 | 176 to 419 ms | 338 ms, 373 ms, 7.1 s, and 2 timeouts at 60 s | agree on the 3 theirs finished; 0 unique |

- Their search is 20 to 200 times faster at 6x6, about level at 8x8, and
  loses at 10x10, where it timed out twice on puzzles ours settled in under
  0.35 s. Tree and flow were within a factor of two of each other everywhere.
- On their own sparse fixture `tests/hard8x8.json` their search took 5.8 s
  and 45 million nodes to find two solutions. Ours cannot take a sparse set
  of numbers yet, so there is no comparison there.
- **The 4x4 unique rate does not carry up.** 551 of 557 at 4x4, but 3 of 5
  at 6x6, 2 of 5 at 8x8 and 0 of 5 at 10x10 on these dense samples. The
  sampler's bias toward full boards is uncontrolled, so this says only that
  non-unique is common, not how common.

### Static rectangle cuts for connectivity

For each rectangle of cells: if a used cell lies inside and another outside,
at least one edge crosses its border. Counted over every degree-valid
network, connected or not, by full enumeration:

| Board | Connected | Disconnected | Left after row and column boundary cuts | Left after all rectangle cuts |
| --- | --- | --- | --- | --- |
| 4x4 (99 rectangles) | 15,593 | 778 | 393 (50.5%) | 0 |
| 5x4 (149 rectangles) | 546,756 | 36,442 | 21,422 (58.8%) | 968 (2.7%) |

- No connected network was removed on either board, as the argument
  requires.
- The parity strengthening (two edges when the rectangle holds an even
  number of branches) removed nothing further on these boards.
- A 4x6 run was stopped by its 900 s cap with no result.
- What this means for solve time is unmeasured: the cuts are a relaxation of
  connectivity that needs no flow variables, and the survivors would still
  need a lazy check.

## Is there a custom propagator hook? (checked 2026-10-10)

**Not in CP-SAT, in our version or upstream.**

- **Our version is the latest.** `uv.lock` pins `ortools 9.15.6755`. PyPI's
  JSON API lists that as the newest release (uploaded 2026-01-14), and
  GitHub's latest release is `v9.15` (published 2026-01-12).
- **Installed package, inspected `[ran]`.** `ortools.sat.python` holds two
  modules, `cp_model` and `cp_model_helper`. The only callback class is
  `CpSolverSolutionCallback`, which fires on a full solution and can read
  values and stop the search. `CpSolver` has two more callback attributes,
  `log_callback` and `best_bound_callback`. `CpModel` has hints and
  assumptions. Nothing takes a propagator, a lazy constraint or a cut from
  user code. The "lazy" and "cut" words in `sat_parameters` describe the
  solver's own LP handling.
- **Upstream main `[ran]`.** `ortools/sat/python/cp_model.py` on the default
  branch has the same callback classes and no propagator or lazy hook.
- **Upstream statements `[read]`.** "You cannot embed any arbitrary code
  inside a CP solver (original or CP-SAT)", answer to "my own constraints
  Google or-tools", Stack Overflow, question dated 2017-11-06,
  https://stackoverflow.com/questions/47145729/my-own-constraints-google-or-tools .
  A user states the same gap in "custom propagator needed ?", gregy4,
  2022-05-19, https://github.com/google/or-tools/discussions/3303 ; the
  maintainer's replies there offer modelling advice and no hook. A search of
  the repo's discussions for "user propagator", "lazy constraints callback"
  and "custom constraint python propagate" returned nothing newer on the
  subject.
- **Inside the C++ `[inferred]`.** CP-SAT's own propagators implement an
  internal `PropagatorInterface` (`integer.h`), so a propagator is possible
  only by writing C++ against the solver's internals and building OR-Tools
  ourselves. Not a supported API. Not verified beyond the description in
  d-krupke's CP-SAT primer manuscript.

**Hooks that do exist elsewhere.**

- **The legacy CP solver in the same package.**
  `ortools.constraint_solver.pywrapcp` has `PyConstraint` (`Post`,
  `InitialPropagateWrapper`, demons) and `PyDecisionBuilder` in our install
  `[ran: attribute check only, nothing solved]`. It has no clause learning,
  and the 2017 answer above calls it deprecated in favour of CP-SAT.
- **PySAT with CaDiCaL (not a dependency when this was written; added by
  #776, see the last section).** `pysat.engines.Propagator`
  attaches user code to the SAT solver through the IPASIR-UP interface:
  `on_assignment`, `propagate`, `provide_reason`, `check_model`,
  `add_clause`. "External engines (pysat.engines)", PySAT documentation,
  https://pysathq.github.io/docs/html/api/engines.html . `check_model` plus
  `add_clause` is exactly a lazy connectivity cut that the solver learns from
  and keeps across the solve, forbid, re-solve loop. Costs: a new dependency
  (`python-sat`), the piece counts must be encoded as cardinality clauses,
  and a Python callback on every assignment is slow, so only the
  full-model check is likely to pay. Unmeasured here; measured in "PySAT
  with lazy connectivity cuts" below.

## PySAT with lazy connectivity cuts (2026-10-10, #776)

**PySAT is faster on all 15 fixture puzzles
(`finders/ubahn/fixtures/timing-puzzles.json`), 1.9 to 5.2 times, and added no
connectivity cut on any of them.** That is not the same as connectivity never
mattering: 4 of the 15 puzzles have fillings in several parts, and the check
stopped before the solver proposed one. So the fixture shows that a SAT model
with no flow variables beats the flow encoding on these boards. It does not
show whether learned cuts beat flow.

The check is `finders/ubahn/sat_model.py`: `python-sat 1.9.dev15`, solver
`Cadical195`, a `pysat.engines.Propagator` whose `check_model` flood fills
each full assignment and returns one clause per connected part. CP-SAT is
`model.uniqueness` with the flow encoding, `ortools 9.15.6755`. Both verdicts
agree on every puzzle, and `test_ubahn_sat.py` holds the PySAT check to the
brute-force counts on all 554 number sets of the 4x4 space as well.

Measured at `5887c8c`, one core, box load about 3.2, same session:

    job-run --name ubahn-776-time-sat -- uv run finders/ubahn/time_sat.py --reps 3 --time-limit 60

Times are the fastest of 3 runs in milliseconds, model build included. No run
reached the 60 s limit, so no row is capped.

| Puzzle | PySAT | ms | Cuts | CP-SAT flow | ms | Agree |
| --- | --- | --- | --- | --- | --- | --- |
| 6x6 seed 0 | not_unique | 2.8 | 0 | not_unique | 14.5 | yes |
| 6x6 seed 1 | unique | 2.3 | 0 | unique | 8.1 | yes |
| 6x6 seed 2 | unique | 2.6 | 0 | unique | 9.8 | yes |
| 6x6 seed 3 | unique | 3.5 | 0 | unique | 8.7 | yes |
| 6x6 seed 4 | not_unique | 2.9 | 0 | not_unique | 11.5 | yes |
| 8x8 seed 0 | not_unique | 28.4 | 0 | not_unique | 83.6 | yes |
| 8x8 seed 1 | unique | 11.2 | 0 | unique | 28.8 | yes |
| 8x8 seed 2 | not_unique | 10.6 | 0 | not_unique | 33.8 | yes |
| 8x8 seed 3 | unique | 12.6 | 0 | unique | 32.9 | yes |
| 8x8 seed 4 | not_unique | 10.3 | 0 | not_unique | 44.6 | yes |
| 10x10 seed 0 | not_unique | 58.4 | 0 | not_unique | 204.2 | yes |
| 10x10 seed 1 | not_unique | 70.7 | 0 | not_unique | 170.3 | yes |
| 10x10 seed 2 | not_unique | 51.8 | 0 | not_unique | 192.4 | yes |
| 10x10 seed 3 | not_unique | 155.6 | 0 | not_unique | 301.7 | yes |
| 10x10 seed 4 | not_unique | 126.3 | 0 | not_unique | 416.9 | yes |

| Size | PySAT | CP-SAT flow | CP-SAT time over PySAT time | Faster |
| --- | --- | --- | --- | --- |
| 6x6 | 2.3 to 3.5 ms | 8.1 to 14.5 ms | 2.5 to 5.2 | PySAT, 5 of 5 |
| 8x8 | 10.3 to 28.4 ms | 28.8 to 83.6 ms | 2.6 to 4.3 | PySAT, 5 of 5 |
| 10x10 | 51.8 to 155.6 ms | 170.3 to 416.9 ms | 1.9 to 3.7 | PySAT, 5 of 5 |

- **Cuts: 0 on every row, for two different reasons.** Only the 5 `unique`
  rows are proofs, and each of those has exactly one filling, a network, so
  there was nothing to cut. The 10 `not_unique` rows are not proofs: the check
  stops at the second network, and CaDiCaL reached two networks before any
  filling in several parts. Counting every filling with no cut at all:

      uv run finders/ubahn/time_sat.py --fillings 300

  | Puzzle | In one part | In several parts | Counted |
  | --- | --- | --- | --- |
  | 6x6 seed 0 | 2 | 0 | all |
  | 6x6 seed 1 | 1 | 0 | all |
  | 6x6 seed 2 | 1 | 0 | all |
  | 6x6 seed 3 | 1 | 0 | all |
  | 6x6 seed 4 | 2 | 0 | all |
  | 8x8 seed 0 | 9 | 1 | all |
  | 8x8 seed 1 | 1 | 0 | all |
  | 8x8 seed 2 | 10 | 0 | all |
  | 8x8 seed 3 | 1 | 0 | all |
  | 8x8 seed 4 | 9 | 0 | all |
  | 10x10 seed 0 | 295 | 5 | first 300 only |
  | 10x10 seed 1 | 5 | 0 | all |
  | 10x10 seed 2 | 56 | 0 | all |
  | 10x10 seed 3 | 295 | 5 | first 300 only |
  | 10x10 seed 4 | 221 | 79 | first 300 only |

  The three capped rows are counts of the first 300 fillings the solver
  listed, not totals or rates. So fillings in several parts exist on 8x8
  seed 0 and on three of the five 10x10 boards, and a check that had to list
  every network there, or prove one unique among them, would need cuts.
- **The cut is tested where it fires.** `test_ubahn_sat.py` has two 4x4 sets
  of numbers that a network shares with a filling in several parts (2 cuts
  each, verdicts as CP-SAT gives them) and two 2x2 loops on a 2x5 board
  (refused, 2 cuts). On the 554 number sets of the 4x4 space with 2 crosses
  in r2 the test prints its total: 0 cuts.
- **The propagator calls back into Python throughout the search, not only on
  a full assignment.** `is_lazy = True` did not stop it:

      uv run python -m cProfile -s ncalls finders/ubahn/time_sat.py --reps 1

  counted 253,652 `on_assignment`, 124,756 `propagate` and 124,756
  `add_clause` calls against 25 `check_model` calls, over one PySAT run of
  each of the 15 puzzles. What those calls cost in time is not measured in
  this repo. A plain loop (solve, flood fill in Python, add the clause, solve
  again on the same solver) would make none of them and keep the learned
  clauses. Not built here; the hybrid's `pysat-lazy` engine is that loop
  (`hybrid_sat.py`, #784).
- **Time limit.** CaDiCaL takes no wall-clock limit through PySAT and
  `interrupt` raises `NotImplementedError`, so the check solves in slices of
  2,000 conflicts and reads the clock between slices. A limit can be overrun
  by up to one slice.
- **JWKNT/logical-solver: not run.** Optional in the ticket.
- **The static rectangle cuts were not added.** Optional in the ticket.

**What this changes for the finder: nothing yet (the worker's reading, not a
ruling).** The check is 2 to 5 times faster, but each one already costs under
half a second, and nothing on record says uniqueness checks dominate a hunt.
The question the prototype was built for is still open: no run here made the
solver learn from a cut on a board of hunt size. The fixture can answer it
without new puzzles. Count all the networks of 8x8 seed 0 and of the three
10x10 boards above with both engines, which forces the cuts, and compare.

## Baseline at 6x6 and 8x8 (2026-10-11, #777)

**On the finder's own proposal step, with no condition: 79% of 6x6 proposals
and 46% of 8x8 proposals are unique under their full outside numbers. A
proposal costs about 47 ms at 6x6 and 144 ms at 8x8 on flow, and the
uniqueness proof is about a fifth of that.** Sampling the network is the
larger share, not the proof. 500 seeds per cell, none timed out, no cell is a
hand-picked puzzle.

What ran: `measure_baseline.py` at `9773868`, which calls the finder's own
`sample` and `prove` (the two halves of `propose`, split for this ticket) per
seed on one CP-SAT worker, so a seed gives the network the hunt's same seed
would. Sampling is always flow, as shipped; `--connectivity` picks the
encoding of the uniqueness proof only, so the `tree` rows prove the very same
networks. One core, box load about 1, one hunt at a time, in this order:

    job-run --name ubahn-777-baseline-2 -- bash -c '
      for size in 6 8; do for conn in flow tree; do
        uv run finders/ubahn/measure_baseline.py --rows $size --cols $size \
          --connectivity $conn --seeds 0:500 --timeout 60
      done; done'

Wall clock 3 min 19 s. One cell reruns alone as
`uv run finders/ubahn/measure_baseline.py --rows 6 --cols 6 --connectivity
flow --seeds 0:500` (about 25 s); the per-seed lines go to stderr.

How to read the tables:

- **Unique** is unique over the seeds whose proof reached a verdict; a seed
  the time limit stopped is counted and left out of the share and the time
  columns, never read as unique or not.
- **Sample** is the solve that draws the network, `model.build` included.
  **Proof** is `model.uniqueness` on that network's full outside numbers,
  build included. **Proposal** is the two together. **Proof share** is the
  proof's median over the proposal's median.
- **Duplicate** is a unique network whose grid of kinds repeats an earlier
  unique one under the board's symmetries, keyed as the hunt driver keys it.
  `verify` is not run, so the driver's "rejected" cause has no row here.

| Board | Proof encoding | Seeds | Decided | Unique | Not unique | Duplicate | Timeout |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 6x6 | flow | 500 | 500 | 396 (79%) | 104 | 0 | 0 |
| 6x6 | tree | 500 | 500 | 396 (79%) | 104 | 0 | 0 |
| 8x8 | flow | 500 | 500 | 230 (46%) | 270 | 0 | 0 |
| 8x8 | tree | 500 | 500 | 230 (46%) | 270 | 0 | 0 |

| Board | Proof encoding | Sample median ms | Proof median ms | Proof 90th ms | Proof max ms | Proposal median ms | Proof share |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 6x6 | flow | 35.7 | 10.8 | 15.3 | 32.0 | 46.9 | 23% |
| 6x6 | tree | 35.6 | 12.2 | 18.2 | 36.5 | 48.4 | 25% |
| 8x8 | flow | 110.8 | 32.3 | 52.6 | 326.4 | 144.1 | 22% |
| 8x8 | tree | 110.8 | 37.2 | 56.4 | 157.5 | 148.3 | 25% |

- **Flow and tree agree on every seed.** They prove the same 1000 networks
  and give the same cause on all of them, so the equal counts are by
  construction; what differs is cost. Tree's proof is 13% (6x6) and 15% (8x8)
  slower at the median and 90th percentile; its worst proof is 36.5 vs 32.0
  ms at 6x6 and 157.5 vs 326.4 ms at 8x8.
- **Sampling is about 76% to 77% of a proposal's median time.** A speedup of
  the proof alone is worth at most a fifth of a no-condition hunt's
  per-proposal cost.
- **A not-unique seed's check stops at its second network and still costs
  more than a unique one's proof:** median 14.6 vs 9.9 ms (6x6 flow), 36.4
  vs 27.3 ms (8x8 flow), read off the per-seed progress lines.
- **No repeats in these 500 seeds** on either board: dedupe cost nothing.
- **An earlier run sampled with tree as well** (`d021f4c`, 14 min wall clock,
  the same 500 seeds per cell, replaced by the run above). Tree sampling had
  medians of 27.5 ms (6x6) and 75.9 ms (8x8), under flow's, and a heavy
  tail: one 6x6 sample took 24.5 s and 8 of the 500 at 8x8 reached the 60 s
  limit, which is 8 of that run's 14 minutes. It drew the same networks as
  flow, so the tail is the tree sampler's cost, not a different draw. The
  shipped finder samples with flow, so it never meets it.
- **Against the hand-sampled fixture** (the "First measurements" section: 3
  of 5 unique at 6x6, 2 of 5 at 8x8; flow proofs 9 to 15 ms and 31 to 81
  ms): the finder's own draws are unique more often than the fixture's dense
  samples (79% and 46%), and the proof times sit in the fixture's range. The
  fixture's 5 per size cannot tell 3 of 5 from 79%; 500 can.
- **What this decides for the queue.** At 6x6 four proposals in five need no
  stripping to be a puzzle and a proposal is under 50 ms, so the full-clue
  check is not the bottleneck at either size; at 8x8 more than half the
  proposals are not unique and pay a proof for it. Hunts under a condition
  (`--exactly`) and stripping are not measured here.
- **Not measured:** 10x10; any condition; more than one worker; where the
  proof time goes (connectivity against the counts); the time a sample
  spends in `model.build` against its solve.

## The three hybrid engines, timed (2026-10-11, #786)

**On Chris's six cases, one core, 100 seeds each: both PySAT engines are more
than 2 times faster than CP-SAT at 8x8 and at 10x10. `pysat-lazy` is 8.4 and
11.2 times faster at the median, `pysat-propagator` 3.9 and 5.7 times.** No
solve of the 1,800 reached the 60 s limit, so no count below is capped and the
cap rule never fired. Chris ruled on the verdict at the end on 2026-10-11:
the hybrid finder's default engine is now `pysat-lazy`.

What ran: `time_engines.py` at `b3f460b`, the hybrid of spec #781 (U-Bahn
with Choco-Banana over grid cells and number cells), one engine at a time,
each engine's six cases in one process. One core, box load about 1, nothing
else of ours running:

    job-run --name ubahn-786-engines -- bash -c '
      for engine in cpsat pysat-lazy pysat-propagator; do
        uv run finders/ubahn/time_engines.py run --engine $engine \
          --progress docs/research/2026-10-11-u-bahn-hybrid-engine-timing/$engine.jsonl \
          --seeds 0:100 --timeout 60
      done'
    uv run finders/ubahn/time_engines.py report \
      docs/research/2026-10-11-u-bahn-hybrid-engine-timing/cpsat.jsonl \
      docs/research/2026-10-11-u-bahn-hybrid-engine-timing/pysat-lazy.jsonl \
      docs/research/2026-10-11-u-bahn-hybrid-engine-timing/pysat-propagator.jsonl

Wall clock 9 min 18 s, about 7.5 min of it CP-SAT. The progress files are in
the repo, one line per solve, and the second command prints both tables below
from them. One cell reruns alone with `--case 8x8` and a fresh `--progress`
file.

How to read the table:

- **A time** is the engine's own call, `grid` or `classify`, from the
  conditions to the answer: building the model or the clauses is inside it.
  Process start and the imports are outside it, because each engine ran its
  600 solves in one process. The split between build and solve was not
  measured.
- **Found** is a grid returned, and every one of the 1,200 found grids was
  re-read by the solver-free rule reader (`hybrid.py`), outside the timed
  call; a refused grid would have stopped the run. **Proven impossible** is
  the engine's proof that no grid meets the conditions. **Timed out** is a
  solve the 60 s limit stopped; it would be labelled capped and left out of
  the time columns. There was none.
- **A seed does not name the same grid on every engine.** CP-SAT takes the
  seed as an order over the edges and the PySAT engines as a phase per edge.
  Each engine is timed on "a valid grid for this seed", not on reaching one
  given grid.
- **Cuts and conflicts** are totals over the case's 100 solves. A cut is a
  clause added for a full grid whose network is in several parts. A conflict
  is one the propagator raised while some edge was still undecided.
- **The 7x7 example timed a proof of no grid, not a search.** The four
  circles on `r6:straight r6:turn r7:straight r7:turn` have no grid on any
  engine, as the decision log already had it, so both example cases land in
  the proven-impossible column. Three engines agree; two of them share every
  clause but connectivity, and nothing enumerates a 7x7. Chris confirmed on
  2026-10-11 that the circles were read correctly from his picture, so no
  grid stands as that layout's result.
- **`classify` takes no seed**, so its 100 seeds are 100 repeats of one call.
  The 60 s limit is per solve inside the CP-SAT engine's `classify`, which
  makes up to two, and over the whole call in the PySAT engines'. Here every
  `classify` proved there is no grid in its first solve, so the limit meant
  the same thing on all three; on a condition that has a grid it would not.

| Case | Engine | Seeds | Found | Proven impossible | Timed out | Solves timed | Median ms | Mean ms | 90th ms | Max ms | Cuts | Conflicts |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 6x6 | cpsat | 100 | 100 | 0 | 0 | 100 | 149.4 | 151.9 | 163.2 | 200.1 | - | - |
| 7x7 | cpsat | 100 | 100 | 0 | 0 | 100 | 277.6 | 290.6 | 335.5 | 455.0 | - | - |
| 8x8 | cpsat | 100 | 100 | 0 | 0 | 100 | 461.2 | 470.4 | 514.9 | 589.8 | - | - |
| 10x10 | cpsat | 100 | 100 | 0 | 0 | 100 | 1298.1 | 1324.7 | 1486.2 | 1745.9 | - | - |
| 7x7 example, grid | cpsat | 100 | 0 | 100 | 0 | 100 | 1224.2 | 1822.3 | 3473.6 | 10097.8 | - | - |
| 7x7 example, classify | cpsat | 100 | 0 | 100 | 0 | 100 | 408.8 | 409.7 | 418.1 | 432.7 | - | - |
| 6x6 | pysat-lazy | 100 | 100 | 0 | 0 | 100 | 23.9 | 25.3 | 37.2 | 52.2 | 43 | 0 |
| 7x7 | pysat-lazy | 100 | 100 | 0 | 0 | 100 | 48.5 | 60.0 | 110.4 | 162.3 | 39 | 0 |
| 8x8 | pysat-lazy | 100 | 100 | 0 | 0 | 100 | 55.2 | 63.4 | 85.9 | 137.3 | 86 | 0 |
| 10x10 | pysat-lazy | 100 | 100 | 0 | 0 | 100 | 116.4 | 134.2 | 186.0 | 311.2 | 86 | 0 |
| 7x7 example, grid | pysat-lazy | 100 | 0 | 100 | 0 | 100 | 38.9 | 40.8 | 52.7 | 61.9 | 0 | 0 |
| 7x7 example, classify | pysat-lazy | 100 | 0 | 100 | 0 | 100 | 42.3 | 44.2 | 56.3 | 63.6 | 0 | 0 |
| 6x6 | pysat-propagator | 100 | 100 | 0 | 0 | 100 | 45.9 | 46.2 | 66.9 | 122.9 | 3 | 678 |
| 7x7 | pysat-propagator | 100 | 100 | 0 | 0 | 100 | 123.4 | 157.2 | 249.2 | 408.0 | 0 | 1603 |
| 8x8 | pysat-propagator | 100 | 100 | 0 | 0 | 100 | 119.4 | 127.9 | 158.0 | 310.2 | 0 | 627 |
| 10x10 | pysat-propagator | 100 | 100 | 0 | 0 | 100 | 229.7 | 270.4 | 441.1 | 728.0 | 1 | 616 |
| 7x7 example, grid | pysat-propagator | 100 | 0 | 100 | 0 | 100 | 49.8 | 52.0 | 63.3 | 76.6 | 0 | 0 |
| 7x7 example, classify | pysat-propagator | 100 | 0 | 100 | 0 | 100 | 52.8 | 54.7 | 67.5 | 77.6 | 0 | 0 |

- **CP-SAT's proof of no grid depends on the seed and has a long tail:**
  median 1.2 s, 90th percentile 3.5 s, worst 10.1 s for the grid call on the
  example, where `classify` on the same conditions, which takes no seed,
  stays at 0.41 s. The PySAT engines prove it in about 40 to 50 ms either
  way.
- **The lazy engine's cuts are rare:** 39 to 86 over 100 solves with no
  condition, under one a solve. The propagator raises 6 to 16 conflicts a
  solve and leaves almost no cut to add, and it is about half as fast as the
  lazy engine: it is Python called on every edge the solver assigns.
- **The lazy engine's lead is largest on the largest board:** 6.3 times at
  6x6, 5.7 at 7x7, 8.4 at 8x8 and 11.2 at 10x10.

The reading against the bar (spec #781: PySAT wins only if it is at least 2
times faster than CP-SAT at 8x8 and 10x10). "Times faster" is CP-SAT's
median over the engine's median, which is the worker's choice of statistic,
not a ruling; the 90th percentiles give 6.0 and 8.0 times for the lazy engine
and 3.3 and 3.4 for the propagator, so the choice does not change the
reading.

| Case | Engine | `cpsat` median ms | Engine median ms | Times faster than `cpsat` |
| --- | --- | --- | --- | --- |
| 6x6 | pysat-lazy | 149.4 | 23.9 | 6.26 |
| 7x7 | pysat-lazy | 277.6 | 48.5 | 5.72 |
| 8x8 | pysat-lazy | 461.2 | 55.2 | 8.35 |
| 10x10 | pysat-lazy | 1298.1 | 116.4 | 11.15 |
| 7x7 example, grid | pysat-lazy | 1224.2 | 38.9 | 31.46 |
| 7x7 example, classify | pysat-lazy | 408.8 | 42.3 | 9.65 |
| 6x6 | pysat-propagator | 149.4 | 45.9 | 3.26 |
| 7x7 | pysat-propagator | 277.6 | 123.4 | 2.25 |
| 8x8 | pysat-propagator | 461.2 | 119.4 | 3.86 |
| 10x10 | pysat-propagator | 1298.1 | 229.7 | 5.65 |
| 7x7 example, grid | pysat-propagator | 1224.2 | 49.8 | 24.57 |
| 7x7 example, classify | pysat-propagator | 408.8 | 52.8 | 7.75 |

**Verdict, for Chris to rule on:**

- `pysat-lazy` is at least 2 times faster than `cpsat` at 8x8 and 10x10: yes
- `pysat-propagator` is at least 2 times faster than `cpsat` at 8x8 and 10x10: yes

By the bar, PySAT wins, and of the two the lazy engine is the faster at every
case.

**Ruled by Chris, 2026-10-11:** `pysat-lazy` is the default `--engine` of the
hybrid finder and of its `classify` command. `cpsat` and `pysat-propagator`
stay selectable, and the plain U-Bahn finder stays on CP-SAT. The timing
above ran while `--engine` still defaulted to `cpsat`; every command line
in this section names its engine, so none of them reads differently now.

**Not measured:** a condition that has grids (every circle case timed here is
the one infeasible example); `classify` on a condition with one grid or
several, where the two limits differ; a piece-count condition; the blank
strip; boards past 10x10; CP-SAT on more than one worker; a second run of
the same seeds, so run-to-run spread is unknown; where each engine's time
goes between build and solve.
