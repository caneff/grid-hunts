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
   line away and `verify` must then find 2 solutions and refuse it. A
   timeout is never unique.
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
  the samples use `cpsat.solver`'s one-worker setting). The driver runs seeds
  one after another and its `--workers` is not read by this finder, so a
  hunt on more cores is several hunt processes over disjoint seed ranges.
- **Per-seed budget (worker's choice, from the pilot).** 40 lines or 120 s,
  `Empty("budget: ...")` past either. The pilot's seeds took 20–40 s and at
  most 14 lines; 120 s is about 3 times the slowest.
- **Link.** Chris's document with every cell's entered digits, colours and
  pencil marks cleared (the spec writer's choice in #39), and the added lines
  appended to his one type-403 constraint, so they take his line style.
- **Dedupe key.** The set of added lines, each as board indices read from
  its smaller end, under `IDENTITY`.
- **`verify` also re-checks each added line's shape** against the lines
  before it. Cheap, and a hit with an illegal line is not a hit.
- **The hunt test stays in the gate (worker's choice).** `test_hunt.py` runs
  seed 0 (a hit) and a two-seed timeout hunt in about 53 s on one core, near
  `test_brute.py`'s own time. It relies on seed 0 hitting, which holds while
  CP-SAT's one-worker search is reproducible at the pinned OR-Tools version;
  if it stops hitting, the test fails loud on the outcome.

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
the driver's load gate: the worker's call, not approved, and not used for the
hunt of record.

- Seed 0: hit, 12 lines. Seed 1: hit, 11 lines. Seed 2: `no space` after 9
  lines, 26 free cells left.
- Pool sampling still 1.1–3.6 s a step. Each added line breaks 9–21 of the
  21 pool members, so the top-up draws most of the pool again. Reuse saves
  little here because the lines are strong.
- Wall clock 112 s.

## Hunt of record

Recorded after the run, below.
