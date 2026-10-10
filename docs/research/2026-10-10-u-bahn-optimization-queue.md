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
  counted by cause, as the lessons file asks.

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
