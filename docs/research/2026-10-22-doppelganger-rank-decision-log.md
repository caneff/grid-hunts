# Doppelganger + Full Rank finder: decision log

Spec #66. The finder is `finders/doppelganger_rank/`: `model.py` the CP-SAT
model, `rules.py` the solver-free rule reader, `brute.py` the 4x4 answer key
and `check.py` the check (#67). The rules and their sources are in
`docs/research/2026-10-22-doppelganger-full-rank-rules.md`. The terms are in
`GLOSSARY.md`'s "Doppelganger + Full Rank terms". Chris's opening board, as
an image, is `docs/research/2026-10-22-doppelganger-rank-opening.png`.

Every choice below marked **worker's choice** was made by a worker, not ruled
by Chris. Flag any you disagree with.

## Rulings from the grill (Chris, 2026-10-22)

The spec (#66) records the grill's rulings by topic, not as a numbered list.
It names Q10 to Q15 individually. The other numbered questions (Q1 to Q9 and
Q16 to Q18) appear only as the rules and decisions below. This log copies the
spec's wording and adds no ruling of its own.

**The rules.**

- **Doppelganger** (Kafkapharnaum's published rule). Every row, column and
  box holds one 0 and eight of the digits 1..N (N = 9 on the 9x9), so each
  misses one digit. No two rows miss the same digit, nor two columns, nor
  two boxes. A 0's row, column and box miss three different digits.
- **Full Rank.** The 9 rows and 9 columns, each read in both directions, make
  36 numbers. A rank clue at one end of a row or column gives the rank of the
  number read away from it.
- **A 0 is read as the digit 0**, so every number has nine digits, a leading
  0 included.
- **Ties are allowed.** A number's rank is 1 plus how many of the 36 are
  strictly smaller. Equal numbers share a rank, and the next rank is skipped
  (QQRR's rule, SQL `RANK`). The no-ties rule of pull prank and Diamond Rank
  is out of scope.

**The opening board.** Read from Chris's image, and Chris did not correct the
reading. Rank clues: 34 above column 1, 6 above column 9, 35 left of row 5,
4 right of row 5. Marks: r1c1 = 8, r1c9 = 1, r5c1 = 9, r5c9 = 0, and column 9
misses 9 (in the column notespace). The marks are Chris's deductions from the
four clues, not givens.

**Numbered rulings.**

- **Q10.** The hunt is the halver hunt's target-grid loop. A seed picks a
  target grid. Each step adds a rank clue, valued from the target, that
  separates a second solution. The run stops at unique, and a minimising pass
  then drops each redundant clue.
- **Q11.** Marks never constrain the hunt's target. Only the check reports
  them.
- **Q12, option (a).** `verify` re-proves uniqueness with a second CP-SAT
  model, written apart from the first. It does not use a backtracking search.
- **Q13.** A clue may go at any free place, 32 places on the opening, with no
  shape rule. Adding a later filter on the candidate list must stay easy.
- **Q14 and its follow-up.** A hit's SudokuMaker link uses the opening's
  13x13 layout and declares `minDigit: 0`. Every rank clue is cosmetic text
  at its row or column end. The full solution, notespace included, is
  entered digits and never givens. The link has no answer check.
- **Q15.** Two seams are in the gate: the check end to end, and the hunt end
  to end.
- **Folder name.** `doppelganger_rank` was the grill's choice, and Chris did
  not object.

## The opening: first check run (#68)

The board file is `finders/doppelganger_rank/fixtures/opening_9x9.json`. It
was written by hand from the reading above.

    uv run finders/doppelganger_rank/check.py finders/doppelganger_rank/fixtures/opening_9x9.json

Run on 2026-10-22 on this box, the WSL2 VM with 32 shared cores, at a load
of 1.3. It ran with `check.py`'s default time limit of **60 s per solve**.
Each solve is one CP-SAT worker (OR-Tools 9.15). The run made six solves: one
for the status, then one per mark.

**Status: `not_unique`.** The four clues allow more than one grid. The check
prints two different solutions below.

**Each mark's verdict: all five held.** Each holds in every solution of the
board:

| Mark | Verdict | Solve time |
| --- | --- | --- |
| (status) | `not_unique` | 2.8 s |
| r1c1 = 8 | held | 1.9 s |
| r1c9 = 1 | held | 13.9 s |
| r5c1 = 9 | held | 1.9 s |
| r5c9 = 0 | held | 8.4 s |
| c9 misses 9 | held | 22.1 s |

**Wall time: 52.9 s** for the whole command, measured with `/usr/bin/time`.
That includes creating `uv`'s environment. A second timing run took the
per-solve times above, 51.0 s in all. No solve came near the 60 s limit, so
no verdict is a timeout.

The full report of the first run:

```
4 rank clues: not_unique
solution 1
  r1 820467531  misses 9  ranks 33 from the left, 5 from the right
  r2 491305826  misses 7  ranks 19 from the left, 26 from the right
  r3 365298047  misses 1  ranks 15 from the left, 29 from the right
  r4 178530492  misses 6  ranks 7 from the left, 10 from the right
  r5 953146780  misses 2  ranks 35 from the left, 4 from the right
  r6 604729153  misses 8  ranks 24 from the left, 14 from the right
  r7 539072618  misses 4  ranks 20 from the left, 32 from the right
  r8 217683904  misses 5  ranks 9 from the left, 16 from the right
  r9 086914275  misses 3  ranks 3 from the left, 22 from the right
  c1 843196520  misses 7  ranks 34 from the top, 2 from the bottom
  c2 296750318  misses 4  ranks 12 from the top, 31 from the bottom
  c3 015834976  misses 2  ranks 1 from the top, 27 from the bottom
  c4 432517069  misses 8  ranks 17 from the top, 36 from the bottom
  c5 609342781  misses 5  ranks 25 from the top, 8 from the bottom
  c6 758069234  misses 1  ranks 30 from the top, 18 from the bottom
  c7 580471692  misses 3  ranks 23 from the top, 11 from the bottom
  c8 324985107  misses 6  ranks 13 from the top, 28 from the bottom
  c9 167203845  misses 9  ranks 6 from the top, 21 from the bottom
  boxes miss b1 7, b2 1, b3 9, b4 2, b5 8, b6 6, b7 4, b8 5, b9 3
solution 2
  r1 806342591  misses 7  ranks 31 from the left, 8 from the right
  r2 452079638  misses 1  ranks 18 from the left, 33 from the right
  r3 793681042  misses 5  ranks 30 from the left, 9 from the right
  r4 638907415  misses 2  ranks 26 from the left, 20 from the right
  r5 927518360  misses 4  ranks 35 from the left, 4 from the right
  r6 015234987  misses 6  ranks 1 from the left, 29 from the right
  r7 189425706  misses 3  ranks 7 from the left, 24 from the right
  r8 560793124  misses 8  ranks 23 from the left, 17 from the right
  r9 274160853  misses 9  ranks 11 from the left, 15 from the right
  c1 847690152  misses 3  ranks 34 from the top, 10 from the bottom
  c2 059321867  misses 4  ranks 3 from the top, 28 from the bottom
  c3 623875904  misses 1  ranks 25 from the top, 16 from the bottom
  c4 306952471  misses 8  ranks 13 from the top, 5 from the bottom
  c5 478013296  misses 5  ranks 19 from the top, 27 from the bottom
  c6 291784530  misses 6  ranks 12 from the top, 2 from the bottom
  c7 560439718  misses 2  ranks 22 from the top, 32 from the bottom
  c8 934168025  misses 7  ranks 36 from the top, 21 from the bottom
  c9 182507643  misses 9  ranks 6 from the top, 14 from the bottom
  boxes miss b1 1, b2 5, b3 7, b4 4, b5 6, b6 2, b7 3, b8 8, b9 9
held      r1c1 = 8
held      r1c9 = 1
held      r5c1 = 9
held      r5c9 = 0
held      c9 misses 9
```

The test of record is `finders/doppelganger_rank/test_opening.py`, in the
gate. It expects exactly this result: `not_unique`, two solutions that the
rule reader finds keep every rule, every clue and every mark, the five
`held` lines, and exit 0. It does not pin the two grids, because the solver
may print a different pair. The whole test took 63 s here.

**Worker's choices (#68):**

- **Gate, not `just test-slow`.** About a minute fits gate time. The ticket
  puts the test in the gate if the run fits gate time. CI's full serial gate
  was 15 min for 64 suites. This suite adds about a minute to it, and to
  every narrowed run of a diff under `finders/doppelganger_rank/`.
- **`--time-limit 300` in the test.** The test does not use the 60 s default.
  The slowest solve takes 22 s here. A larger limit means a slower CI runner
  takes longer instead of reporting `TIMEOUT` and failing the test. A real
  regression still fails: on a timeout the test sees a `TIMEOUT` line or the
  wrong status.

## The hunt at 4x4 (#69)

`finders/doppelganger_rank/hunt.py`, on the hunt protocol. Its docstring
states the loop, the minimiser, the seed classes and the record.
`test_hunt.py` runs it from an empty 4x4 board in the gate and judges every
hit against `brute.py`'s key.

**The sampler, measured.** The first `RankModel.sample` was the halver
hunt's: one worker, a random digit hint per cell. On an empty 4x4 it gave
6 distinct grids in 40 seeds, and every one had r1c1 = 0. The key holds
768 grids, and 576 of them have another digit there. Presolve's symmetry
breaking was the cause. With `symmetry_level = 0` and nothing else changed,
200 seeds gave 153 distinct grids, and r1c1 took every digit 0..4 (30 to 47
times each). On Chris's 9x9 opening the same sampler took 1.0 s to 5.4 s per
target (seeds 0..3), and 10 seeds gave 10 distinct targets.

Two other samplers were measured and dropped. Both used a fixed search over
the cells in a shuffled order, picking the random half of each domain:

- With presolve on, an empty 4x4 gave 48 distinct grids in 400 seeds, all
  with r1c1 = 0.
- With presolve or its symmetry pass off, 4x4 coverage was good (297 of
  400), but 3 of 4 seeds on the 9x9 opening reached the 60 s limit.

**First run.** On 2026-10-22, on this box: 20 seeds from an empty 4x4 took
12 s and found 20 hits, each with 2 or 3 added clues after minimising.

**Worker's choices (#69):**

- **A clue is picked uniformly by the seed's rng** from `separating`'s
  list, with no pool ranking like the halver hunt's. The minimiser removes
  the clues this leaves redundant.
- **A minimiser solve that times out ends the seed as `timeout:`**. Recording
  the hit instead could leave a clue the board does not need.
- **`symmetry = IDENTITY`.** The board's clues break the square's symmetry,
  and a 6x6's 2x3 boxes do not transpose.
- **A record carries the size, the box and every clue**, so `hunt.py
  verify DIR` reads a hit with no board file. The record's `clues` lists the
  board's clues first, then the `added` ones.
- **A target that ranks the same as a second grid at every free place**
  ends the seed as `no separating clue:`. No rank clue can make that target
  unique. `summary` counts these seeds apart from the four classes the
  ticket names.
- **`verified_io.example_verdicts`** is `halver_hunt`'s old `_verdicts`,
  moved into `finders/hunt/` so both hunts' `summary` read it.

## The second-model re-proof in `verify` (#70)

Worker choices, not rulings:

- **`reprove.py` shares no code with `model.py` or `rules.py`**: it has its
  own unit and reading-order geometry, and imports only `sudoku_kit` and
  OR-Tools. A cell is n + 1 booleans with an order ladder (digit at least k);
  a missing digit is a boolean per digit; two numbers compare digit by digit
  as a chain of clauses, never as summed integers. It has no leading-digit
  buckets, so it stays apart from #75's change to `RankModel`.
- **`verify` runs the re-proof after the rule reader**, under the hunt's
  `--time-limit`, and refuses `not unique: a second grid ...` or
  `timeout: ...`. It also refuses a `unique` re-proof whose grid is not the
  hit's solution, and any other status, naming it.
- **Time, one worker, 2026-10-22, a single run each:** `tie_6x6.json`
  0.2 s on `model.py`, 0.3 s on the re-proof; `opening_9x9.json` 2.9 s and
  1.8 s. Both models said `not_unique` on both boards. So at these sizes
  the re-proof costs about what the hunt's own check does.

## Leading-digit buckets in `RankModel` (#75)

`model.py`'s docstring states the constraints: ISS's `FullRank` buckets, as
the research note `docs/research/2026-10-22-doppelganger-rank-iss-buckets.md`
(on `main`, a678311) describes them, plus Chris's added scope of
2026-10-22: a clue's strictly-less literal is decided by the two leading
digits when they differ, and the whole numbers are compared only when they
are equal.

**Times, one worker, the opening (`fixtures/opening_9x9.json`).** Measured
2026-10-22 on this box at load average 10 to 14, a single run each, each
solve given 300 s:

| solve | before | after |
| --- | --- | --- |
| status (`not_unique`) | 3.1 s | 0.4 s |
| r1c1 = 8 | 2.1 s | 0.0 s |
| r1c9 = 1 | 17.5 s | 0.0 s |
| r5c1 = 9 | 2.1 s | 0.0 s |
| r5c9 = 0 | 11.1 s | 0.0 s |
| c9 misses 9 | 24.1 s | 0.0 s |
| **five mark proofs** | **56.9 s** | **0.1 s** |

Every status and mark verdict is unchanged: `test_check.py` (the 4x4
boards against the answer key, `tie_6x6`, the empty 6x6 and 9x9),
`test_opening.py`, `test_hunt.py` and `test_reprove.py` all pass.

**Mutations**, each in a throwaway worktree:

- **Lead implications stripped** (`b` forces the other's leading digit at
  most this one's, `not b` at least): `test_check.py` red, the check's rule
  reader refusing a model grid where `r1 from the right ranks 11, not 8`.
  Since the added scope, these are not redundant: with differing leads
  they are all that decides `b`.
- **Same-lead gate stripped** (`same` false no longer forces the leads to
  differ): `test_check.py` red, the same refusal.
- **Bucket bounds stripped**: every suite green. They are a pure speed-up:
  without them the five proofs took 5.7 s (slowest 1.6 s) in place of
  0.1 s. A test that saw this would need a per-solve limit under 1.6 s,
  too tight for CI.

**Worker's choices (#75):**

- **`test_opening.py` gives each solve 10 s, not 300 s.** The model before
  this change times out on three marks at 10 s, so a lost speed-up from the
  lead implications and the gate fails the gate. 10 s is about 25 times the
  slowest solve now.
- **The leading-digit one-hot is posted for clued places only**, since only
  a clue's bucket bounds read it. Other numbers' leads enter as the cell
  variable itself.

## SudokuMaker links (#71)

`hunt.py links DIR` writes `DIR/links/<seed>.txt` per verified hit
(`links.py`'s docstring states the layout). The link test decodes each
written link against its record at 4x4 and at 9x9 (`test_links.py`).

**The first 9x9 hit.** On 2026-10-22, on this box, one worker, `hunt.py
--board fixtures/opening_9x9.json --seeds 0:2 --time-limit 120
--max-seconds 600` took 3 min 36 s. Seed 0 ended `no separating clue`
after 18 clues. Seed 1 found a verified hit with 14 added clues (18 in
all). Its logs are `fixtures/links_9x9/`, the 9x9 input of the link test
only; #72 owns the 9x9 hunt and its recorded hit.

**The live-app check.** That hit's link, opened in the live app
(v2026.10.05-a3aef4c) with `shot-scraper`, 2026-10-22:
`2026-10-22-doppelganger-rank-first-link.png`. The 13x13 canvas shows the
grid, the three notespaces and every clue as in Chris's drawing. The top
and left clues sit outside the canvas, so no extra row or column was
needed. Every digit, 0 included, shows as entered, none as a given, and
the app marks no conflict. The five opening marks hold on this hit:
r1c1 = 8, r1c9 = 1, r5c1 = 9, r5c9 = 0, and c9 misses 9.

**Worker's choices (#71), flag if you disagree:**

- **The layout grows with n**: an n + 4 canvas, the row notespace at column
  n + 3, the column notespace at row n + 3, and the box notespace in the
  bottom-right corner shaped as the boxes are. At 9x9 that is Chris's
  measured layout. It lets the 4x4 hunt test reach `links` in the gate.
- **Each notespace is one region**, so the app draws it with a heavy
  border. Chris's drawing shades the row and column notespaces without
  one. Their digits are all different under the Doppelganger rule, so the
  region adds no wrong constraint. Making them no-region cells is a
  one-line change.
  Superseded in the spec-level review (finding P3): the row and column
  notespaces are now in no region, and each box notespace cell is its own
  region, as the drawing borders each.
- **A clue's text is size 0.5**, twice QQRR's 0.25, to read like the
  drawing's clue numbers.
- **`links` writes verified hits only.** It skips an unchecked or rejected
  candidate of a `--no-verify` hunt and says how many it skipped.
- **The type-0 "Given digits" constraint stays** with no givens: every
  SudokuMaker document here carries it. It checks nothing.

## The most restricting clue first (#79)

Chris ruled on 2026-10-22 that the hunt adds the most restricting
separating clue, not a uniform pick. `hunt.py`'s docstring states the loop:
a separating place scores how many grids of a sample of the board's
solutions keep the target's rank there; the lowest is added; ties go to the
seed's rng. The sample is `--pool` draws (16) of `RankModel.sample`, and it
shrinks to the grids each added clue keeps. A fresh sample is drawn when
fewer than `--pool-floor` (4) are left. `--pool 0` draws none, so every
place ties and the pick is the rng alone, #69's uniform pick.

**Random against ranked, one worker.** Measured 2026-10-22 on this box at
load average 3 to 4, one run each. Each row is one seed set run through
`DoppelgangerRankFinder.propose` by a scratch timing script. The script
wraps `RankModel.check`, `RankModel.sample` and `most_restricting` to count
calls and runs nothing of its own. Loop clues are the clues added before
the minimiser. Loop checks are the uniqueness checks of the add loop. All
checks adds the minimiser's checks. `ranked4` is `--pool 4 --pool-floor 1`.

Empty 4x4 (`size 4, box 2x2`, no clues), seeds 0..19:

| pick | hits | loop clues | added after minimising | loop checks | all checks | samples | wall s |
| --- | --- | --- | --- | --- | --- | --- | --- |
| random (`--pool 0`) | 20 | 64 | 57 | 84 | 154 | 20 | 4.6 |
| ranked (16, floor 4) | 20 | 57 | 56 | 77 | 134 | 932 | 14.6 |
| ranked4 (4, floor 1) | 20 | 61 | 58 | 81 | 144 | 264 | 7.7 |

Empty 6x6 (`size 6, box 2x3`, no clues), seeds 0..4. Seed 0 ended
`no separating clue` on every pick:

| pick | hits | loop clues | added after minimising | loop checks | all checks | samples | wall s |
| --- | --- | --- | --- | --- | --- | --- | --- |
| random (`--pool 0`) | 4 | 42 | 26 | 46 | 89 | 5 | 15.5 |
| ranked (16, floor 4) | 4 | 35 | 27 | 39 | 72 | 565 | 80.9 |
| ranked4 (4, floor 1) | 4 | 42 | 27 | 46 | 87 | 173 | 36.5 |

**Reading.** At the default pool, the ranked pick adds 11% fewer loop
clues on the 4x4 and 17% fewer on the 6x6. It runs 8% and 15% fewer loop
checks, and 13% and 19% fewer checks in all. The minimised hits are no
smaller. It is 3.2 times slower on the
4x4 and 5.2 times slower on the 6x6. The cost is the sample: the most
restricting clue rules out most of the sample by design, so nearly every
step falls under the floor and draws 16 fresh grids. At these sizes a
draw costs about what a check does, so 16 draws per step cost far more
than the checks saved. On the 9x9 opening a draw took 1.0 s to 5.4 s
(#69) and a check about 0.4 s (#75), so this trade is not measured there.
#72's 9x9 hunt is where `--pool` and `--pool-floor` get set from a
measurement; `--pool 0` gives back #69's pick with no code change.

`test_hunt.py`, which runs 20 + 1 + 2 + 2 + 3 + 20 seeds on the defaults,
went from 23 s to 42 s on this box (one run each, load average 3.4).

**Mutations**, each in a throwaway worktree under `.scratch/`, each red on
`test_hunt.py`'s own assertion:

- **Score ignores the share** (`score` returns only the rng draw): the
  planted pool test picks r1 from the left on seed 1.
- **Uniform pick** (`propose` calls `rng.choice(places)`): the spy sees no
  ranked pick.
- **No shrink** (the sample is not filtered after a clue): the spy sees a
  sampled grid that breaks an earlier added clue.

**Worker's choices (#79), flag if you disagree:**

- **The defaults are ranked, `--pool 16 --pool-floor 4`**, following the
  ruling, although they are slower at 4x4 and 6x6 (above). Superseded by
  #72: the default is now `--pool 0` (§ The 9x9 hunt).
- **The sample is drawn at the first pick, not before the first check.**
  A board that starts unique draws none. Otherwise this is the ruling's
  "before a seed's loop".
- **The target and repeated draws are left out of the sample.** The
  target keeps every rank it has, so it adds the same 1 to every place's
  count and changes no pick. A draw that reaches its time limit is left
  out, as in the halver hunt's pool.
- **The score is a count, not a share.** Every place is scored on the same
  sample, so the count orders the places as the share does.
- **A refill draws `--pool` times again with the seed's rng**, under the
  seed's `--max-seconds`. The target is drawn before any sample, so each
  seed's target is the one #69 drew.

## The 9x9 hunt (#72)

The hunt of record on Chris's opening, and the three speed changes measured
before it. All on this box (WSL2, 32 shared cores), OR-Tools 9.15. The
timing runs used a scratch script that wraps `RankModel.check` and
`RankModel.sample` to time each call around `DoppelgangerRankFinder.propose`,
with `--time-limit 120 --max-seconds 1200` and one run each. The script was
never committed.

### Where a seed's time goes

At `--pool 0`, before any change, seeds 0..3 (load average 1 to 3): 65 of
the add loop's checks said `not_unique` and took 135.6 s, at most 15.4 s
each. Its one `unique` check took 0.6 s. The minimiser's 15 `not_unique`
trials took 42.5 s and its 2 `unique` ones 2.3 s. Targets took 0.1 to 0.3 s.
The cost is in finding second grids, not in proving a board unique.

### Warm starts (Chris's added scope, 2026-10-22)

`RankModel.check` takes a `hint` grid, a CP-SAT solution hint for both of
`check_uniqueness`'s solves. The same seeds, `--pool 0`, one worker:

| hint | seed 0 | seed 1 | seed 2 | seed 3 | total |
| --- | --- | --- | --- | --- | --- |
| none | 10.6 s, inseparable after 15 | 87.7 s, hit, 13 added | 43.0 s, inseparable after 16 | 40.9 s, inseparable after 16 | 182.2 s |
| the target | 1.1 s, inseparable after 3 | 54.1 s, hit, 13 added | 1.9 s, inseparable after 5 | 15.4 s, inseparable after 6 | 72.5 s |
| the last second grid | 69.9 s, inseparable after 16 | stopped | | | |

"Inseparable after k" is a seed that ended `no separating clue` after k
added clues. **Kept: every check is hinted with the target**, in the add
loop and in the minimiser: 2.5 times faster in all. The add loop's
`not_unique` checks fell from 2.1 s to 1.1 s each on average. The hinted
solver finds a second grid near the target, so it reaches a rank twin
sooner. A rank twin is a grid that ranks like the target at every free
place, and any one is a proof that no rank clue makes that target unique.
The last-second-grid hint was 7 times slower on seed 0 and was stopped
there. Seed 1's hit is the same with or without the hint.

### The minimiser on 8 CP-SAT workers (Chris's added scope, 2026-10-22)

`--proof-workers K` runs the minimiser's checks on K workers. Seed 1,
target hint: the minimiser's 17 checks took 34.3 s on one worker and
8.2 s on 8 (load average 3.5), and the hit was the same. The add loop
stays on one worker. The ruling names the uniqueness proofs, and the
loop's last check, its one `unique` proof, took under 1 s. On more workers
the second grid the loop reads would change from run to run, and with it
the clue added. The minimiser reads only unique or not, so its hit does
not depend on the worker count. `test_hunt.py` checks this at 4x4, and
`test_hunt_9x9.py` finds seed 72's hit on one worker, the hit the hunt of
record found on 8.

### Ranked against uniform pick (the controller's note, 2026-10-22)

The same seeds, target hint, one worker each, `--pool 16` (#79's ranked
default) against `--pool 0` (#69's uniform pick), load average 1.5 to 4:

| seed | `--pool 0` | `--pool 16` |
| --- | --- | --- |
| 0 | 1.0 s, 1 draw, inseparable after 3 | 274.8 s, 177 draws, inseparable after 11 |
| 1 | 51.4 s, 1 draw, hit, 13 added | 464.4 s, 225 draws, hit, 14 added |
| 2 | 1.9 s, 1 draw, inseparable after 5 | 23.1 s, 49 draws, inseparable after 3 |
| 3 | 14.7 s, 1 draw, inseparable after 6 | 14.0 s, 65 draws, inseparable after 4 |
| **total** | **69.0 s** | **776.3 s** |

"Draws" counts `RankModel.sample` calls, the target included. **`--pool 16`
was 11 times slower and found no smaller hit**, so **`--pool 0` is now the
default**. That applies the controller's recommendation, and Chris may
overrule it. 707 s of `--pool 16`'s time went to the draws. `--pool 16`
still gives the ranked pick, and `test_hunt.py` tests it with that flag.
`test_hunt.py` fell from 42 s to 23 s on the new default. A run with no
target hint, stopped early, had spent over 550 s on seed 0 at `--pool 16`,
against 10.6 s at `--pool 0`.

### The hunt of record

    uv run finders/doppelganger_rank/hunt.py --board finders/doppelganger_rank/fixtures/opening_9x9.json \
      --out docs/research/2026-10-22-doppelganger-rank-9x9-hunt/seeds-0-60 --seeds 0:60 \
      --time-limit 120 --max-seconds 600 --proof-workers 8

and the same over `--seeds 60:120` into `seeds-60-120`, at 03a5b8b. Each
process ran under `job-run`. By MACHINE-LOAD.md, two processes ran at once,
each on one worker in its add loop and 8 in its minimiser: at most 16
workers on 32 cores. The load average was 0.9 at launch. Every other knob
was a default: `--pool 0`, `--max-clues 36`. Wall times were 12 min 6 s
for seeds 0..59 and 7 min 52 s for seeds 60..119. `hunt.py verify` on each
directory (the rule reader, then the second model's re-proof, 30 s per
hit) took 91.8 s and 49.0 s. Every hit passed both checks.

**The split, 120 seeds (0..119):** found 16, proven infeasible 0, timed
out 0, capped 0, no separating clue 104, duplicate 0, rejected 0. No
seed hit a time limit or a budget, so every seed ended in a hit or a
proof about its target.

**The 16 verified hits**, by added clues after minimising: 11 (seed 72),
12 (seeds 77, 83), 13 (seeds 1, 16, 27, 40, 42, 44, 45, 47, 87, 112) and 14
(seeds 21, 50, 92). `hunt.py summary DIR` lists each hit with its clues and
solution. Each hit's SudokuMaker link is `DIR/links/<seed>.txt`. Chris's
five marks hold in every hit, as the check proved they hold in every
solution of the opening (#68).

**No separating clue, 104 seeds**, by the added clues at the stop: 0 (2
seeds), 1 (13), 2 (7), 3 (16), 4 (18), 5 (15), 6 (5), 7 (11), 8 (1), 9 (4),
10 (7), 11 (2), 12, 13 and 17 (1 each). Each is a proof about its target
only: some other grid ranks as it does at every free place, so no set of
rank clues makes that target unique. Two targets had a twin before any
clue was added.

**What the run covered.** 120 target grids, one per seed, drawn by
`RankModel.sample` from the opening's solutions. For each one the run found
a set of rank clues that makes it unique or proved that none exists. It
says nothing about targets it did not draw. Its fewest added clues, 11, is
the fewest this run found, not a proven minimum (spec #66 puts the proven
minimum out of scope). An 11-clue hit means 15 rank clues in all.

**The recorded hit.** Seed 72's hit is
`finders/doppelganger_rank/fixtures/hit_9x9.json`: the record and the link the hunt wrote. `test_spec_66_e2e.py`
re-checks it in the gate (14.7 s here). The model says unique, with the
hit's grid as its one grid. The marks hold, `verify` passes it, and it
refuses the hit with its last clue dropped and with no time. The record
and the link are rebuilt exactly. `test_hunt_9x9.py` reruns seed 72 from
the opening in `just test-slow` (46.5 s here) and expects that record, a
`verify` pass, the summary and the same link.

**Speedups not applied** (MACHINE-LOAD.md's list):

- The add loop on 8 workers: outside the ruling, and it makes runs
  irreproducible.
- Screening a target for a rank twin before its loop: no test cheaper than
  the loop itself is known.
- More processes: two kept the box at half its cores, by MACHINE-LOAD.md.

**Mutations**, each in a throwaway worktree under `.scratch/`, each red on
its test's own assertion:

- **`verify` skips the re-proof**: `test_spec_66_e2e.py` sees
  `Verdict(ok=True)` for the hit with a clue dropped.
- **The minimiser keeps every clue**: `test_hunt_9x9.py` sees a record
  that is not the fixture's.
- **The `--proof-workers 0` refusal stripped**: `test_hunt.py` sees the
  hunt run and exit 0.

**Worker's choices (#72), flag if you disagree:**

- **Seed 72 is the recorded hit** because it has the fewest added clues
  of the 16.
- **The minimiser alone runs on `--proof-workers`.** The ruling's "last
  step of a seed" is the add loop's final check, which the loop cannot
  tell in advance and which took under 1 s.
- **`--proof-workers` defaults to 1**, so a bare run stays box-safe. The
  hunt of record passed 8.
- **120 seeds**: at the timing runs' 1 hit in 4 seeds, about 30 hits in
  about 15 minutes. The run's own rate was lower, 16 in 120.

## Closing check: the recorded hit opened in the live app (spec #66, P4)

2026-10-22, SudokuMaker v2026.10.05-a3aef4c, `shot-scraper` at 1400x1100:
seed 72's link (`2026-10-22-doppelganger-rank-9x9-hunt/seeds-60-120/links/72.txt`,
after the P3 region change) opens as Chris's layout. The 9x9 grid and its
boxes are bordered; the row and column notespaces are unbordered; each of
the box notespace's nine cells is bordered. All 15 rank clues read past
their lines' ends (34 19 36 27 6 above, 35 8 1 25 left, 31 4 15 right,
32 10 28 below), and the entered solution is intact (r1 843029671 ...
r9 634801257, missing digits in the notespaces). No screenshot is
committed: a PNG under `docs/research/` widens every narrowed gate.
