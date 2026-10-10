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
