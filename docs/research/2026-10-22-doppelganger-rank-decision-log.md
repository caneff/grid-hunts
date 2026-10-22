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
