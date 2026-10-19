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
   check took 202.8 s (check notes). It did not apply the drawing rules (4
   of its 23 lines cross an earlier line diagonally), and it was a single
   seed, so it times the check; it is no evidence that the loop with the
   drawing rules reaches a finish. The hunt of record below is that
   evidence. (Spec #52 asks for this reasoning before any search; #54's run
   came first, made for the rule check's fixtures, and this log was written
   before the hunt slice's first run.)
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

**How long a body can be for a given pair, over the whole board.** No
longer than the per-house caps above allow house by house, and no other cap:
a king-step body can leave a house after its cap and carry on in the next,
and its digits may repeat across houses. So a pair with a cap of 1 (the
narrowest) still allows a long body that never puts two cells in one row,
column or box, and the cap that binds in the hunt is `--max-cells` (8 cells,
so 6 body cells), not the rules.

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

## Decisions

- **One target-grid loop for both line types (worker's choice).** The loop,
  its ranking, `verify`, the record, `summary` and the CLI moved out of
  `halver_between/hunt.py` into the shared `finders/halver/halver_hunt.py`,
  and both finders' `hunt.py` name their line type's modules, their start
  board and their link. The spec rules the same loop and tie-breaks for
  both; a second copy of 470 lines would drift. `halver_between`'s five
  hunt suites pass on it unchanged, its published link included.
- **The board is empty**, as ruled: no givens, no given halvers, no lines.
  `record` numbers the lines from L1.
- **Link.** An empty 9x9 document (format 1.6.0, the 3x3 regions, nothing
  entered) with one type-407 constraint holding every line, diamonds first
  and last, and `"solverIgnored": true`. That is the spec's convention for
  Chris's between board (type 403 with the same flag). No line style is
  set: SudokuMaker draws its default lockout line.
- **Record.** The `halver_between` record with `diamond_a` / `diamond_b` in
  place of `circle_a` / `circle_b`, plus the solution as `digits` and
  `halvers`, both of which `halver_between` also writes.
- **Per-seed budget (worker's choice, from the pilot).** `--max-seconds 600`,
  where `halver_between` has 120: the pilot's slowest seed took 270 s, most
  of it pool sampling near the finish (one step 123 s). The other knobs keep
  `halver_between`'s defaults: 8 cells, a pool of 20, 30 s a solve, 40
  lines, a 600 s `verify`. The pilot's seeds needed 24 and 25 lines.
- **Workers.** Every CP-SAT call runs on one worker and the seeds run one
  after another, as in `halver_between`, so `--workers` other than 1 is
  refused. "The hunt driver's default workers" is read as running the hunt
  with no `--workers` flag, which is one worker here. A hunt on more cores
  is several `hunt.py` processes over disjoint `--seeds` ranges.
- **The gate's hit (worker's choice).** `test_spec_52_e2e.py` runs on the
  pilot's seed 2 (`hit_fixture.py`), whose `verify` takes 15 s against 170 s
  and 294 s for the other two. The test runs two backtracking searches, so
  it costs about 35 s in the gate.
- **The full hunt test is slow.** `test_hunt.py` runs seed 0 (a hit, about
  130 s to find and 290 s to verify on one core) and a two-seed timeout
  hunt (7 min 43 s measured on 2026-10-19 at a load of about 3), so it
  sits in `tests/all.sh`'s `finder_slow`, run by `just test-slow`. It relies on seed 0 hitting, which holds while CP-SAT's
  one-worker search is reproducible at the pinned OR-Tools version; if seed
  0 stops hitting, the test fails loud on the outcome.

## Hunt of record (2026-10-19, one core, seeds 0:3)

`job-run --name lockout-pilot-56 -- uv run finders/halver_lockout/hunt.py
--out .scratch/pilot --seeds 0:3 --step-log .scratch/pilot-steps.jsonl`,
at a 1-minute load of about 3. Its output directory and step log are
`docs/research/2026-10-19-halver-lockout-hunt/`. The run's `git_sha`,
7c4c8b6, is the preflight commit: the hunt code was still uncommitted in
the worktree, and it is the `hunt.py` and `halver_hunt.py` of this ticket's
PR with only import order changed since.

**3 hits in 3 seeds**, wall clock 958 s. Each hit was written by the driver
only after `verify`'s backtracking check found exactly one solution, the
hit's own. This shows that an empty board can be finished with lockout
lines alone; it is no count of how many finishes exist.

| seed | lines | propose | verify | free cells left |
|---|---|---|---|---|
| 0 | 25 | 134 s | 294 s | 31 |
| 1 | 25 | 270 s | 170 s | 27 |
| 2 | 24 | 77 s | 15 s | 35 |

Per step: the uniqueness check takes 0.09–0.3 s until the last two or three
lines (up to 3 s); pool sampling 1–2 s a step until the last few, then 10
to 123 s as the board nears unique; ranking under 0.5 s. No pool draw timed
out. An added line breaks 1 to 21 of the 21 pool members, 17 or more on most steps.

Read against the preflight:

- **Cells did not run out.** 27 to 35 cells were still on no line at each
  finish, so the between hunt's line economy does not carry over. Lockout
  lines are cheap in cells here because almost every one is three cells:
  70 of the 74 lines have one body cell, 3 have two and 1 has three. The
  ranking's kills per new cell favours them.
- **The preflight's guess of long bodies on extreme values was wrong.**
  Bodies are short, and a body cell's value is extreme (2 or less, or 8 or
  more) in 46 of 79 body cells. Middle values do sit on bodies: a value of
  4 or 4.5 is a body cell 7 times, each time with the diamonds the counts
  above allow.
- **The slow step is the backtracking check**, as the check notes warned:
  up to 294 s of the 600 s budget on a 25-line hit.

**Seed 2, 24 lines** (the gate's `hit_fixture.py`):

https://sudokumaker.app/?puzzle=N4IgZg9gTgtghgFwGoFMoGcCWEB2IBcABCAIwB0AbGQAwgA0xADgK4BerANigYaDnDG5EQ9YnGYIAFtB4iGIAMYoOHdDwDawAL4NtunbwN7D+0yfPHLR62au2bFh3cf3XL9889Pvbr758eAX6B-qEh4V4AuvIKuOgIUHCYOAhqRJogCACejEKE1EaZOXkk8lAoAObYOGmE6tQMDfkMpYStrQBMDF2EPU39LYNt3SO9jePNw1Odoz0AzAwLhEsALAxrhBsArAw7hHtLh+vHm7tn+4uXyycb2+d7FAyPhM8A7AzvhJ8AHAy-hP9nkCPiCvn9wQCnlCXqDPj8Id9IoVsrkeCtqJ8QOgIBwAG5oACSFRw0BQABMeAlmCh5Bxkihaup1BRnltPhRXtE6hRtkCKFz1HMeuj1gBOAUkPYdDZCiVSg5zAU8p4PfkMdQdUWLLWbcXqlkfIGc9VzQ63DoCzWLJpzEgClY9LaOu3qh3rVpbF11T1PJoUQHGuodJodVq2y06uafOZquokf4kHXBiPdf4xiVLDrzL3qH0vVoUPVx54dZ5zLYZlobSUS9o9EiK9XzFqNuNNdp2pFIrRAA

The other two hits' links and line tables are in `examples.jsonl`, and
`uv run finders/halver_lockout/hunt.py summary
docs/research/2026-10-19-halver-lockout-hunt` prints them. Its wall clock line
says "wall clock not recorded": this run predates the `ended.json` a
returning hunt now writes, and a file's modification time, which git does
not keep, is never read in its place. The run's own 958 s is the one above.
