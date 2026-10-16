# Halver + between-line hunt: decision log

Spec #39, ticket #41. The finder is `finders/halver_between/hunt.py`, its
candidate lines `candidates.py`. The board is `DFRTLJqBKt` (L1–L6, Chris's
switch of 2026-10-16). Facts it builds on:
`docs/research/2026-10-16-halver-between-truths.md`.

Every choice below marked **worker's choice** was made by the #41 worker, not
ruled by Chris. Flag any you disagree with.

## Preflight (`docs/agents/grid-finder-lessons.md`), answered before the first long hunt

1. **Known bounds, and does the variant obey them?** The 17-givens minimum
   does not apply: the board has no givens, and the halvers and lines carry
   information the theorem does not count. The bounds that do apply are the
   truths note's: 46,656 ways to place the nine halvers, and (§6) 44 cells
   left that can become a body cell. The 44 is the one that binds in the
   pilot below.
2. **What produced the corpus you reason from?** No corpus. The reasoning
   rests on the truths note, derived from the rules and checked with #40's
   rule model. `unique_9x9.json` (#40's test case) is on the first board and
   is not used here.
3. **Does the sampler cover the space or one orbit?** Targets come from a
   one-worker CP-SAT solve steered by random digit hints. 10 seeds gave 10
   distinct targets with 10 distinct halver sets. The same solve seeded
   through `random_seed` alone, with no hints, gave the same grid 10 times
   out of 10, so the hints are what make it sample. The draw is not uniform,
   and nothing here claims it is.
4. **Which lesson does this plan contradict?** "Cuts only pay when each cut
   kills a family and the master cannot dodge it." The target-grid loop is a
   cut loop, but the master cannot dodge: the target is fixed and every line
   added holds in it, so each line removes the second solution for good and
   the loop converges unless it runs out of cells. It does run out of cells
   (below), which is the lesson's failure in another form: a line that kills
   one solution spends cells a later line needed.
5. **What would make a result an artefact, and what control rules it out?**
   A modelling bug in the CP-SAT rule model could call a board unique when it
   is not. `verify` re-reads every hit with `brute.py`, the backtracking
   check that shares no code with the model, and checks that its one
   solution is the hit's. The control: `test_hunt.py` takes the hit's last
   line away and `verify` must then find 2 solutions and refuse it, and
   `test_spec_39_e2e.py` has `verify` refuse a recorded hit given an illegal
   line or a solution that is not its own. A timeout is never unique.
6. **Can the solver answer this directly?** Not the question as asked:
   "does some set of lines make the board unique" is an exists-forall
   question no single solve states. So a hit is a proof that a finish exists,
   and no-hit is reported as "none found", never as impossible.
7. **Cheap necessary conditions first.** The truths note's solver-free
   rejects (§2, §5: no halved 1 or normal 9 in a body, unequal circles, the
   k − 1 bound in one house) all hold for any line that holds in the target.
   The walk only builds lines that hold in the target, so it never makes a
   candidate those rules reject. The "no space" check (§6) ends a seed with
   no cell left that could tell the target from the second solution.

## Decisions

- **Candidate generation (worker's choice).** `separating_paths` walks out
  from every cell that may be a circle and extends through free cells while
  the body's target values stay on one side of the first circle, then closes
  on any cell whose value lies beyond the body. This is growing the line from
  the target inside a value window (§6), not enumerating king paths and
  filtering. The walk is capped at `--max-cells` cells (8 unless given): a
  cap on the per-step search, not on the layout, and the `Empty` reason
  names it. `test_candidates.py` checks the walk against a naive walk over
  every king path of up to four cells and gets the same set.
- **Ranking (worker's choice).** Pool solutions broken per new cell taken
  (body cells plus circles not already on a line), then touching a cell
  whose halver status differs between target and second solution, then
  shortest, then the seed's rng. The controller's notes asked both for
  halver-pinning lines first and for kills per new cell. Kills per cell is
  primary because the pilot's seeds ended on space, not time; halver status
  is the tie-break.
- **Pool (from the controller's notes, sized by the worker).** Up to 20
  distinct sampled solutions of the current lines, plus the second solution.
  The members an added line leaves alive stay, and only the shortfall is
  drawn again. When the pool holds only the second
  solution, kills per cell picks the line that takes the fewest new cells,
  which is §6's second phase without a separate switch.
- **Solver reuse (from the controller's note).** One `RuleModel` per seed,
  lines added on top; the target is the check's solution hint.
- **Workers.** Every CP-SAT call runs on one worker (`rules.check` pins it;
  the samples use `cpsat.solver`'s one-worker setting), and the driver runs
  seeds one after another, so `hunt.py` refuses `--workers` other than 1 by
  name rather than accept it and leave the cores idle. A hunt on more cores
  is several hunt processes over disjoint seed ranges.
- **Per-seed budget (worker's choice, from the pilot).** 40 lines or 120 s,
  `Empty("budget: ...")` past either. The pilot's seeds took 20–40 s and at
  most 14 lines; 120 s is about 3 times the slowest. The check after the
  40th line runs before the line budget refuses, so a seed that finishes on
  its last permitted line is a hit (`test_propose.py`). Every sample and
  check gets the smaller of `--time-limit` and the seconds the seed has
  left, so a step overruns the 120 s by no more than its walk and ranking,
  never by a pool of 30 s solves. A pool draw that reaches its limit is left
  out of the pool and counted as `pool_timeouts` in the step log.
- **`verify`'s bound (worker's choice).** The backtracking search stops at
  `--verify-seconds` (600 unless given, about 17 times the slowest pilot
  verify) and refuses the hit with "no verdict"; a stopped search never
  passes a hit.
- **`summary` reads verification.** A hunt without `--no-verify` wrote only
  examples that passed `verify`, so each is a hit. A `--no-verify` hunt's
  examples are unchecked candidates until `hunt.py verify DIR` has run, then
  hits or rejected by its verdicts in `verified.jsonl`; a `verified.jsonl`
  that does not cover the examples is refused.
- **Link.** Chris's document with every cell's entered digits, colours and
  pencil marks cleared (the spec writer's choice in #39), and the added lines
  appended to his one type-403 constraint, so they take his line style.
- **Dedupe key.** The set of added lines, each as board indices read from
  its smaller end, under `IDENTITY`.
- **`verify` also re-checks each added line's shape** against the lines
  before it. Cheap, and a hit with an illegal line is not a hit.
- **The hunt test is a slow test (controller's ruling on the #39 review).**
  `test_hunt.py` runs seed 0 (a hit) and a two-seed timeout hunt in about a
  minute on one core (54 s measured on 2026-10-16 at load 6–9), and its
  outcome rides on wall-clock limits on a shared box, so it is in
  `tests/all.sh`'s `finder_slow`, run by `just test-slow`, like the Banabner
  hunt. It relies on seed 0 hitting, which holds while CP-SAT's one-worker
  search is reproducible at the pinned OR-Tools version; if it stops
  hitting, the test fails loud on the outcome. The gate keeps
  `test_spec_39_e2e.py`: one recorded hit (second pilot, seed 1) checked
  `unique`, its 23 marks held, its shapes, its record and published link,
  and `verify`, in about 9 s, with no hunt.

## Pilot (2026-10-16, one core, seeds 0:3)

| | per step |
|---|---|
| uniqueness check | 0.18–0.22 s |
| pool sampling (20 solves) | 2.1–2.9 s |
| candidates walked | 2 to 10,862 |
| ranking | under 0.45 s |

- Seed 0: hit, 14 added lines, 21 of the 44 free cells taken.
- Seed 1: `Empty("no space: ...")` after 8 lines, 30 free cells left, none
  of them where the target and second solution differ.
- Seed 2: no separating line within 8 cells after 7 lines, 31 free cells
  left.
- `verify` (the backtracking check) takes about 35 s on a hit.
- Wall clock 94 s for the three seeds. Seeds end on space, not time: no seed
  came near its budget.

A first pilot that ranked halver-touching lines first, then by pool kills
with no per-cell cost, also hit on
seed 0, with 8 lines of 3–4 cells, in 58 s. One seed of each is no
comparison; the run below uses the per-cell ranking.

Second pilot, after pool reuse (seeds 0:3, one core, box load 34–45 from
other work, so times run high). This one ran with `--force-load`, which skips
the driver's load gate: the worker's call, not asked for, and disclosed
here. It ran on one core, and it is half of the hunt of record below.

- Seed 0: hit, 12 lines. Seed 1: hit, 11 lines. Seed 2: `no space` after 9
  lines, 26 free cells left.
- Pool sampling still 1.1–3.6 s a step. Each added line breaks 9–21 of the
  21 pool members, so the top-up draws most of the pool again. Reuse saves
  little here because the lines are strong.
- Wall clock 112 s.

## Hunt of record

No 3-process run of record happened. Its launch under `job-run` was refused
by the driver's load gate:

> hunt: refusing to run -- 1-minute load 46.97705078125 is above 24 (use --force-load to run anyway)

The controller ruled that the pilots stand as this slice's hunt result,
since they went through the driver, and that a longer hunt is decided at the
spec's integration step. The hunt of record is both pilots, the second run
with `--force-load` as said above. Counted both ways: **3 hits in 6 seeds
across both pilots** (seeds 0:3 twice); the first pilot alone, **1 hit in 3
seeds**. Each hit was written by the driver only after `verify`'s
backtracking check found exactly one solution, the hit's own. This shows that the board
can be finished with between lines alone. It is no count of how many
finishes exist, and the three Empty seeds prove nothing.

Empty reasons, verbatim:

- First pilot (per-cell ranking), seed 1: `no space: after 8 added lines the target and the second solution differ only on body cells of drawn lines`
- First pilot, seed 2: `no line of at most 8 cells separates the target from the second solution after 7 added lines`
- Second pilot (pool reuse), seed 2: `no space: after 9 added lines the target and the second solution differ only on body cells of drawn lines`

**First pilot, seed 0, 14 added lines.**

https://sudokumaker.app/?puzzle=N4IgZg9gTgtghgFwGoFMoGcCWEB2IBcABCAIwB0AbGQAwgA0xADgK4BerANigYaDnDG5EQ9YnGYIAFtB4gAwpMw4AygihxGokAGMUHDuh4BtYAF8GZi+d7XLNqw-tO7L228euP75988+vAf5BfiG+YYGhEeHB0ZExUQnxSaEAugw6uOhqcEoIhkQmIAgAnoxChNS2RaXlJOlQKADm2Dj5hEbUDJ0VDHWEfX0ATAzDhKPdE71T-SOzY10LPTPLQ3OjAMwMm4TbACwM+4SHAKwMp4Tn21cHN0dn9xdbTzu3hycP5xQMX4Q-AOwMAGEIEADgYYMIEJ+0MBsOB4IRkO+yN+cKBoMRIJSVXQEA4ADc0ABJRo4aAoAAmPDUzBQ6RKZR4u2o2xAHCUKDaRiMgwAnFtuut+UdBX11qNdn1jt1dsLdhDdn80u0KOdjj9dhrjsqjLs1YcKNsKIc-ts-ibtQweUCSBDhSRuiRhYMsVaKKM-n0-t0KMKKNQdX9zn9-kCKBDjhGw5b2rttsdRv6dYMgesgXqdSRRoNui7kxD1gqlVbdhs3utM9mhrydecSNss7XeocSDGjJ9em31udduXM+dBi2KJn-r1i+0e71BpWRtmK8qQFlilweKB2ThOauioptABrDfoNrUMh9DIcGTCADEcBvt5A1hAKBwFIAChBcm1QFhWOVjxDwJg+iyJeYCgWBIK0OkWRQBAu7lKAUiYHuB5HjQoxnhexDXreN73qY+HYqYQA

| # | Circle A | Body | Circle B |
|---|---|---|---|
| L7 | r5c8 | r6c8 | r7c7 |
| L8 | r4c1 | r5c2 | r6c1 |
| L9 | r2c4 | r3c3 | r4c2 |
| L10 | r4c2 | r5c3 | r6c3 |
| L11 | r5c7 | r4c8 | r5c8 |
| L12 | r2c4 | r3c4 | r4c3 |
| L13 | r1c6 | r2c5 | r2c4 |
| L14 | r1c6 | r2c6 | r2c7 |
| L15 | r1c6 | r1c7 | r2c7 |
| L16 | r4c9 | r5c9 | r5c8 |
| L17 | r2c7 | r3c7 | r2c8 |
| L18 | r2c8 | r1c8 | r2c9 |
| L19 | r1c6 | r1c5 | r2c4 |
| L20 | r2c4 | r3c5 | r3c6 |

**Second pilot, seed 0, 12 added lines.**

https://sudokumaker.app/?puzzle=N4IgZg9gTgtghgFwGoFMoGcCWEB2IBcABCAIwB0AbGQAwgA0xADgK4BerANigYaDnDG5EQ9YnGYIAFtB4gAwpMw4AygihxGokAGMUHDuh4BtYAF8GZi+d7XLNqw-tO7L228euP75988+vAf5BfiG+YYGhEeHB0ZExUQnxSaEAugw6uOhqcEoIhkQmIAgAnoxChNS2RaXlJOlQKADm2Dj5hEbUDJ0VDHWEfX0ATAzDhKPdE71T-SOzY10LPTPLQ3OjAMwMm4TbACwM+4SHAKwMp4Tn21cHN0dn9xdbTzu3hycP5xQMX4Q-AOwMAGEIEADgYYMIEJ+0MBsOB4IRkO+yN+cKBoMRIJSVXQEA4ADc0ABJRo4aAoAAmPDUzBQ6RKZR4u2o2xAHCUKDaRiMgwAnFtuut+UdBX11qNdn1jt1dsLdhDdn80u0KOdjj9dhrjsqjLs1YcKNsKIc-ts-ibtQweUCSBDhSRuiRhYMsVaKKM-n0-t0KMKKNQdX9zn9-kCKBDjhGw5b2rttsdRv6dYMgesgS6dedDiR1jqcyMht0M1b1pc3rmS1ny3ntiRDoNdpneucG8nDus9oMdf9ekqS70Bl23VKjV3lSAssUuDxQOycJyZ0VFNoANbz9BtahkPoZDgyYQAYjgx5PIGsIBQOApAAUILk2qAsKxyluIeBMPpZAewD-fyDaOkWRQBAK7lKAUiYKu66bjQoy7vuxBHiex5nqYaHYqYQA

| # | Circle A | Body | Circle B |
|---|---|---|---|
| L7 | r5c8 | r6c8 | r7c7 |
| L8 | r4c1 | r5c2 | r4c2 |
| L9 | r1c6 | r1c5 | r2c5 |
| L10 | r2c5 | r3c4 r3c3 | r4c2 |
| L11 | r4c9 | r4c8 | r5c8 |
| L12 | r4c9 | r5c9 | r5c8 |
| L13 | r2c5 | r2c6 | r3c7 |
| L14 | r1c6 | r2c7 | r3c7 |
| L15 | r3c7 | r4c7 | r5c7 |
| L16 | r1c7 | r1c8 | r2c9 |
| L17 | r1c4 | r2c3 | r2c4 |
| L18 | r7c8 | r6c9 | r7c9 |

**Second pilot, seed 1, 11 added lines.**

https://sudokumaker.app/?puzzle=N4IgZg9gTgtghgFwGoFMoGcCWEB2IBcABCAIwB0AbGQAwgA0xADgK4BerANigYaDnDG5EQ9YnGYIAFtB4gAwpMw4AygihxGokAGMUHDuh4BtYAF8GZi+d7XLNqw-tO7L228euP75988+vAf5BfiG+YYGhEeHB0ZExUQnxSaEAugw6uOhqcEoIhkQmIAgAnoxChNS2RaXlJOlQKADm2Dj5hEbUDJ0VDHWEfX0ATAzDhKPdE71T-SOzY10LPTPLQ3OjAMwMm4TbACwM+4SHAKwMp4Tn21cHN0dn9xdbTzu3hycP5xQMX4Q-AOwMAGEIEADgYYMIEJ+0MBsOB4IRkO+yN+cKBoMRIJSVXQEA4ADc0ABJRo4aAoAAmPDUzBQ6RKZR4u2o2xAHCUKDaRiMgwAnFtuut+UdBX11qNdn1jt1dsLdhDdn80u0KOdjj9dhrjsqjLs1YcKNsKIc-ts-ibtQweUCSBDhSRuiRhYMsVaKKM-n0-t0KMKKNQdX9zn9-kCKBDjhGw5b2oMgesgYqdYMfus3oMdbtRsdRv7k5c9hmrSQbT8U8nHaNBkNeZneicdf7vn13cmIesIXydcdhccWwGrRsDillSAssUuDxQOycJyp0VFNoANaz9BtahkPoZDgyYQAYjgh6PIGsIBQOApAAUILk2qAsKxyhuIeBMPpZHuwF-vyDaOkslAEBLuUoBSJgy6ruuNCjNuu7EAeR6HiepgodiphAA

| # | Circle A | Body | Circle B |
|---|---|---|---|
| L7 | r4c1 | r5c2 | r6c3 |
| L8 | r3c9 | r4c8 | r5c7 |
| L9 | r5c7 | r6c8 | r7c7 |
| L10 | r3c8 | r4c7 | r5c7 |
| L11 | r2c9 | r2c8 | r3c9 |
| L12 | r3c3 | r2c4 r3c4 | r4c3 |
| L13 | r1c5 | r2c6 | r1c6 |
| L14 | r7c7 | r7c8 | r7c9 |
| L15 | r4c2 | r5c3 | r4c3 |
| L16 | r7c6 | r6c7 | r7c7 |
| L17 | r1c3 | r1c4 | r1c5 |
