# Banabner hunt decision log

The decision log the Banabner hunt (spec #758) keeps as it runs: what was
decided, what it rested on, what it cost. The finder is
`finders/banabner/banabner_finder.py`; its model is
`finders/banabner/banabner_model.py`.

## 2026-10-09 — #761 model finds grids; first-grid times

The joint model (exact-cover bananas, nabner tables, difference-4 whisper,
chocolate sides <= 4, the difference-4 catalogue on both sides) found a legal
grid on every seed tried. Four plain model solves, 1 CP-SAT worker each, seeds
0-3, 300 s cap, run side by side: 170, 183, 244 and 248 s, all `OPTIMAL`
(feasible, no objective). The first grid found (seed 0, 4 workers, 109 s) was
checked by hand and pinned as `finders/banabner/known_grid.json`.

Space covered by every search below: chocolate rectangle sides <= 4. That is a
proven fact of the rules (#761, the proof is in `MAX_CHOC_SIDE`'s comment), so
it is not a cap.

Consequence: `finders/banabner/test_hunt.py`, one 1-worker seed, takes 3-4
minutes and sits in the slow finder tier (`just test-slow`), not in
`just check`.

## 2026-10-09 — #762 speedups: before and after

The speedups: a 5-cell banana holds only odd digits; at most 5 cells of a
house lie in 5-cell bananas; each even digit has a placement avoiding them;
and a lex-leader over the 8 board symmetries.

Commands, one per seed `S` in 0-3, the eight run side by side on an otherwise
lightly loaded box (1-minute load 5.4 at launch, 32 cores):

```
uv run finders/banabner/banabner_finder.py --out DIR --seeds S:S+1 --workers 1 --timeout 600 --no-speedups   # before (#761)
uv run finders/banabner/banabner_finder.py --out DIR --seeds S:S+1 --workers 1 --timeout 600                 # after (#762)
```

Wall clock per hunt, process start to exit, each run recording one grid that
`hunt` verified:

| seed | before (s) | after (s) |
|---|---|---|
| 0 | 195 | 226 |
| 1 | 293 | 156 |
| 2 | 310 | 365 |
| 3 | 217 | 361 |
| mean | 254 | 277 |

Reading: on four seeds the speedups did not shorten the time to a first grid;
the after mean is 9% higher, and the per-seed spread (156-365 s) is wider than
the difference, so four seeds do not separate the two. The lex-leader is not
expected to help a first-grid search: its value is in the catalogue search
(no grid found again as a rotation or reflection) and in an INFEASIBLE proof.
A comparison of grids found per hour, or of a proof, is what would test it.

The worker kept the speedups on by default, since #762 asks for them.
`--no-speedups` turns them off. This is a claim for the reviewer to re-run.

## 2026-10-09 — #764 two-hour hunt: preflight

The preflight of `docs/agents/grid-finder-lessons.md`, answered before launch.

1. **Known bounds, and does the variant obey them?** No givens are placed and
   no uniqueness is asked: the hunt finds legal filled grids, so the 17-givens
   bound says nothing here. The bounds that do apply are proven facts of these
   rules, all in the model: chocolate rectangle sides <= 4 (`MAX_CHOC_SIDE`),
   a banana has 3-5 cells (nabner allows at most five pairwise
   non-consecutive digits; one or two cells form a rectangle), and a 5-cell
   banana is exactly {1,3,5,7,9}.
2. **What produced the corpus reasoned from?** The difference-4 rectangle
   catalogue (#760, completed by #767: every layer with both sides <= 4
   enumerated in full, no fill-count cap left inside the searched space). The
   ten grids in `checked-grids/` come from #761/#762 seeds with the flags in
   their `run` field. The hunt reasons from the catalogue only; it does not
   read the earlier grids, and its own run starts with nothing forbidden.
3. **Space or one orbit?** The lex-leader keeps one grid per orbit of the 8
   board symmetries, and every found grid is forbidden by a no-good cut, so a
   later seed must find a grid outside every earlier orbit. The driver dedupes
   under D4 as a second check. Digit reversal (d -> 10-d) preserves every rule
   but moves the circles, so it is deliberately not broken: checked on all ten
   `checked-grids/` grids, each reversed grid passes `check` and is a different
   D4 orbit. A reversed pair counts as two grids in this hunt.
4. **Which lesson does the plan contradict?** "Compare strategies by hits per
   CPU-minute, over enough runs": #762 compared the speedups on four seeds of
   time to a first grid and found no gain, and the hunt keeps them on anyway.
   The case differs because this hunt is an enumeration with cuts, not a
   first-grid race: under the lex-leader one no-good cut removes a whole
   8-grid orbit, and without it a rotated copy of a found grid stays legal and
   costs a full solve to be thrown away as a duplicate. An INFEASIBLE, if one
   comes, is also what the lex-leader and the facts are for.
5. **What would make the result an artefact, and what control rules it out?**
   A model bug that accepts an illegal grid: every grid is re-read inline by
   `renbanana_verify.check` at difference 4 with nabner, a checker written from
   the rules, and again by `build_lineup.py` before publishing. A model bug
   that rejects legal grids would make an INFEASIBLE false and the count low:
   the ten known grids, found partly without the speedups, are the control
   (`test_known_grid.py` checks the pinned grid is accepted by the model).
6. **Can the solver answer directly?** "How many grids exist" has no single
   solve; the hunt asks the solver one question per seed (a new grid, or a
   proof that none is left) and reports only what those answers say. A
   timeout is labelled capped, never read as exhaustion.
7. **Cheap necessary conditions** are #762's facts (odd 5-cell bananas, at
   most 5 such cells per house, an even-digit placement avoiding them), kept on.

**Speedups applied:** #762's facts and lex-leader; the catalogue on both the
shading and the digit side; 8 CP-SAT portfolio workers on each solve (the
seeds are sequential, since each forbids the grids before it).

**Not applied, named:** per-task splits (e.g. fixing the top-left shading per
split) to run seeds in parallel, not built and would need a split proof of
coverage; warm start from the previous grid's solution as a hint, not built,
and it would bias the search toward neighbours; reusing one incremental model
across seeds instead of rebuilding it (a few seconds a seed, small against a
solve of minutes); no C hot loop applies, the solve is CP-SAT's.

**Launch:** `.scratch/run-hunt.sh 8` under `job-run --name banabner-hunt-764`:
seeds 0:1000, `--timeout 1200` per seed, `--workers 8`, a 7200 s wall
(`timeout -s TERM`), and `examples.jsonl`, `progress.jsonl`, `summary.json`
and `run.json` copied into `docs/research/banabner/hunt-2h/` every 300 s. The
hunt output itself lives in `~/.cache/banabner-hunt-764/out`. Expected wall
clock: 2 h. The result decides how many grids the Banabner Lineup offers
for puzzle setting, and whether the space ran dry (an INFEASIBLE) within 2 h.

## 2026-10-09 — #764 two-hour hunt: results

The run as launched above: `run.json` records argv, config
(`timeout 1200, max_choc_side 4, speedups true`), git sha `c626aec` and start
17:23:15 UTC. The 7200 s wall stopped it at 19:23 UTC (`timeout` exit 124).
The driver's output is synced in `docs/research/banabner/hunt-2h/`
(`examples.jsonl`, `progress.jsonl`, `summary.json`, `run.json`,
`verified.jsonl`).

**Space covered.** Legal Dutch Chocolate Banabner grids (difference 4, nabner
bananas, normal sudoku, no givens) whose chocolate rectangles have both sides
at most 4. Every legal grid meets that limit: it is a proven fact of the rules
(`banabner_model.MAX_CHOC_SIDE`), not a cap, so the searched space is the whole
space. Grids are counted up to the board's 8 rotations and reflections. Digit
reversal (d -> 10-d) is not broken, so a grid and its reversal would count as two.

**Results, by seed outcome** (`summary.json`):

| outcome | seeds |
|---|---|
| proven infeasible (no grid left) | 0 |
| timed out at 1200 s (capped) | 0 |
| found a new grid | 44 (seeds 0-43) |
| stopped mid-solve by the 2 h wall (capped) | 1 (seed 44) |

44 grids in 7200 s, about 164 s a grid with 8 workers, steady across the run.
The search was not exhausted: no seed proved the space empty. **This run says
nothing about how many grids exist** beyond "at least 44 + the 10 earlier",
and nothing about whether that number is small.

**Checks.** All 44 pass `banabner_finder.check` (`renbanana_verify.check` at
difference 4, nabner) inline as found, again in the driver's `verify` pass
(`verified.jsonl`: 44 of 44 ok), and a third time in `build_lineup.py`. They
are 44 distinct D4 orbits, every one already in lex-leader form. None is one of
the 10 earlier grids in `checked-grids/` and no two are reversals of each other.
The 44 are added to `checked-grids/examples.jsonl` as `764-<seed>`.

**What they look like.** Circle score (the lineup's count): 4 to 12, median 7;
one grid scores 12 (`764-14`), against the best earlier grid's 13 (`761-2`).
Largest chocolate group: 4 cells in 27 grids, 6 in 13, 9 (a 3x3) in 2.
The hunt does not aim at circles; a circle-seeking objective is a different
search.

**Lineup.** The Banabner Lineup is
https://claude.ai/artifact/N5uQ4JBGdGydL5V3aAUyGB, republished as version 7
(`1791574193-f200`) from `build_lineup.py` over `checked-grids/` and the
controller's opener solutions (`.scratch/banabner-opener-solutions/`, outside
git), merged onto the live version 6: 56 grids, every card and Record entry of
version 6 kept. The opener's Record entry now also lives in
`lineup-record.json`, so a rebuild keeps it.

**Wrapper.** The hunt ran from a throwaway wrapper (not committed): the finder
under `timeout -s TERM 7200`, a 300 s loop copying the four driver files above
into `hunt-2h/`, under `job-run --name banabner-hunt-764`.
