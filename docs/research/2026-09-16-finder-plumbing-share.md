# How much of a finder is plumbing gridfind would replace?

Resolves [#481](https://github.com/caneff/sudokumaker-custom-constraints/issues/481),
child of the finders-on-gridfind wayfinder map
([#478](https://github.com/caneff/sudokumaker-custom-constraints/issues/478)).
Reuses the rule classification already done in gridfind's
[2026-09-16-finder-layer-gaps.md](https://github.com/caneff/gridfind/blob/main/docs/research/2026-09-16-finder-layer-gaps.md)
(#797) rather than redoing it.

## Method

Read `finders/renbanana_cpsat.py` (986 lines) and
`finders/zombo_brainanas_cpsat.py` (893 lines) in `caneff/drills`
(worktree `sudokumaker-custom-constraints/gridfind-integration`), plus their
verify companions (`finders/renbanana_verify.py`, the `verify` subcommand
inside `zombo_brainanas_cpsat.py`) and render companions for context. Read
gridfind's layer registry (`src/gridfind/layers/door.py`), `verdict.py`,
`engine.py`'s `build_engine`/`Layer` protocol, and `offset_adjacency.py` (the
closest existing layer to renbanana's chocolate whisper). Read both finders'
git history (`git log --all -- <path>`) for bug-fix commits. Line ranges were
split at function/block boundaries (not literal per-line), counted with a
small script (`.scratch/count_ranges.py`, gitignored) that strips blank lines
and comments/docstrings from each range; "code" below means non-blank,
non-comment lines. Module docstrings (renbanana lines 1-48, zombo lines 1-29)
are excluded from all totals.

Three buckets, per map #478's definitions:

- **gridfind would replace** — counted only where an existing gridfind layer
  or API covers the line today, or the `build`/`rules=` surface under
  discussion in [gridfind#796](https://github.com/caneff/gridfind/issues/796)
  would (stated per row which).
- **`finders/hunt/` would replace** — output dir, progress/resume, dedupe,
  neighbour/component helpers, CLI/driver plumbing, generic solve-wrapper
  utilities. Rule-agnostic.
- **rule-or-search specific** — rule encodings gridfind lacks (per the gap
  doc), catalogue use, CEGAR cuts, staging/objective machinery.

## renbanana_cpsat.py (986 lines, 700 code lines in scope)

| Range | Bucket | Code lines | Reason |
|---|---|---|---|
| 50-64 | rule/search | 12 | `ortools`/`renbanana_verify` imports, module setup for this encoding |
| 65-68 | gridfind | 4 | `N`/`CELLS`/`IDX` = board cell enumeration (`gridfind.layers.board`); `MAX_BANANA` (1 line) is a rule constant, folded in |
| 69-79 | rule/search | 11 | search-tuning constants (`NOISE`,`BIG`, time slices) + solve-status labels |
| 82-90 | gridfind | 7 | `neighbours()`/`ADJACENT` = orthogonal-offset walk, duplicates `offset_pairs`/`ORTHOGONAL_OFFSETS` |
| 92-100 | rule/search | 9 | loads `rectangle-catalogue.json` — catalogue use |
| 103-167 | rule/search | 30 | `circle_cells_at`/`support_at`/`fillings_at` — catalogue readers |
| 170-185 | rule/search | 10 | `SHAPES` — catalogue-derived shape list |
| 188-198 | rule/search | 1 | `Shadings` class docstring |
| 200-298 | rule/search | 79 | `Shadings.__init__` — free per-cell shading + rectangle-lemma (no 2x2-window-of-3) + banana size cap + objective. Gap doc: no open gridfind map scopes a free/non-solution shading layer |
| 300-329 | rule/search | 15 | `_forbid_dead_placements` — catalogue use |
| 331-361 | rule/search | 20 | `_where_the_fives_go` — shading-only digit lemma, rule-specific |
| 363-372 | rule/search | 7 | `_shape_present` — rule-specific shape-presence indicator |
| 374-397 | rule/search | 15 | `_spots` — rectangle-placement indicator, catalogue-gated |
| 399-406 | rule/search | 6 | `forbid_component` — CEGAR cut |
| 408-413 | rule/search | 5 | `forbid_shading` — CEGAR cut |
| 415-425 | rule/search | 7 | `replay` — cut replay across seeds |
| 427-434 | gridfind | 8 | `Shadings.solve` — plain build-solver/solve/extract wrapper, matches `verdict.py`'s `_build_and_solve` shape (under the `build`+`num_workers` surface) |
| 437-463 | rule/search | 19 | `legal_shading` — CEGAR loop, staging |
| 469-487 | gridfind | 11 | `digit_model` sudoku core — rows/cols/boxes `AllDifferent` = `rows-distinct`/`cols-distinct`/`regions-distinct` + `board` |
| 489-508 | rule/search | 15 | whisper rule (chocolate-adjacency gap ≥ 5, conditional on the free shading). `OffsetValueGap` is unconditional/fixed-gap — no gridfind layer gates a pair rule on a free boolean today |
| 510-521 | rule/search | 11 | catalogue per-cell digit domains |
| 523-529 | rule/search | 7 | renban `AllDifferent` + min/max — groups defined by free shading, not a gridfind region |
| 531-558 | rule/search | 26 | circle constraints |
| 560-596 | rule/search | 35 | objective + diversity noise — search-staging, gap doc names this "never a layer" |
| 599-611 | gridfind | 12 | `fill_digits` — solve wrapper, same shape as `Shadings.solve` |
| 617-629 | rule/search | 12 | `profile()` — renbanana-specific feature computation |
| 632-640 | rule/search | 8 | `circle_cells()` — rule-specific |
| 643-657 | rule/search | 15 | `score()` — rule-specific |
| 660-671 | hunt | 10 | `diverse_enough()` — Hamming/shape-multiset dedupe against the pool |
| 677-689 | hunt | 12 | `as_json()` — candidate record serialization |
| 691-727 | hunt | 28 | `hunt()` signature/setup — outdir, pool, learned-cuts list, stats dict |
| 729-736 | hunt | 7 | `log()` closure — progress-file writer |
| 738-757 | hunt | 20 | seed loop start — rng/seed iteration, model instantiation call |
| 759-786 | rule/search | 24 | inner shading-solve + digit-fill call — rule-specific solve orchestration |
| 787-799 | rule/search | 13 | second digit-fill re-solve under the objective |
| 800-828 | hunt | 29 | accept/reject/diversity-check/record-write loop |
| 829-836 | hunt | 8 | cut-carry bookkeeping + per-seed logging |
| 838-840 | hunt | 3 | stats file write |
| 843-864 | rule/search | 20 | `bound()` — shading-only ceiling proof, rule-specific objective |
| 867-880 | rule/search | 11 | `parse_family()` — shape-family CLI vocabulary, rule-specific |
| 883-983 | hunt | 96 | `main()` — argparse CLI + subcommand dispatch |
| 985-986 | hunt | 2 | `__main__` guard |

**Totals (700 code lines):** gridfind would replace: **42 (6.0%)**. `finders/hunt/` would replace: **215 (30.7%)**. Rule-or-search specific: **443 (63.3%)**.

## zombo_brainanas_cpsat.py (893 lines, 722 code lines in scope)

| Range | Bucket | Code lines | Reason |
|---|---|---|---|
| 31-41 | rule/search | 10 | `ortools`/`ctypes`/`threading` imports for this model + watchdog |
| 43-44 | gridfind | 2 | `N`, `CELLS` — board size/cell enumeration |
| 45-46 | rule/search | 2 | `RECT`, `CIRCLE_WEIGHT` — rule constants |
| 47 | hunt | 1 | `WORKERS` — driver config |
| 50-52 | gridfind | 2 | `box()` — box-index formula, duplicates board geometry's region membership |
| 54-59 | gridfind | 6 | `nb()` — orthogonal neighbour stepper |
| 62-65 | rule/search | 4 | `isrect()` — rectangle-shape test |
| 68-82 | rule/search | 14 | `rects()` — rectangle-placement enumeration (catalogue-like) |
| 85-103 | rule/search | 18 | `polyominoes()` — pocket shape generation |
| 106 | rule/search | 1 | `MAX_POCKET` constant |
| 109-120 | rule/search | 11 | `placements()` — pocket-placement enumeration |
| 123-128 | rule/search | 6 | `RECTS`/`ALL_RECTS`/`POCKETS` module-level catalogues |
| 131-156 | rule/search | 22 | `build()` signature + ~20-line rule-feature parameter list |
| 157, 163-174 | gridfind | 13 | digit vars + rows/cols/boxes `AllDifferent` |
| 158-162, 175-181 | rule/search | 11 | infection/patient-zero vars (`inf`,`pz`,`rect`,`ban`) + patient-zero placement rules |
| 182-194 | rule/search | 12 | infection spread + closure. Gap doc: no gridfind map covers directed percolation-to-closure |
| 195-201 | rule/search | 6 | rectangle-lemma (2x2-window-of-3), identical to renbanana's |
| 202-207 | rule/search | 2 | banana non-rectangle exclusion clauses |
| 208-209 | gridfind | 2 | apply `givens` — matches `applier.apply`'s `WorkingState` givens channel |
| 210-211 | rule/search | 2 | `fix_shade` — free-shading concept gridfind has no layer for |
| 212-222 | rule/search | 11 | dot rule — conditional value-ratio gated by shading; closest is `pair-ratio`, but unconditional |
| 223-237 | rule/search | 14 | rectangle-circle constraint |
| 238-247 | rule/search | 9 | CEGAR cut application |
| 248-305 | rule/search | 50 | pocket/clued-banana modeling |
| 306-333 | rule/search | 22 | `min_groups` — labelled-component + BFS-distance root. Gap doc names this a 4th connectivity-encoding variant not yet folded into #771 |
| 334-350 | rule/search | 16 | circle-able rectangle-cell prep |
| 351-362 | rule/search | 12 | `min_circles`/`min_per_box` |
| 363-382 | rule/search | 14 | objective/noise/bonus terms — search-staging |
| 383-385 | rule/search | 2 | `avoid` diversity-distance constraint (baked into the model, on the rule-specific `inf` var) |
| 386-397 | rule/search | 10 | `min_cross` — box-straddle reach heuristic |
| 398-400 | rule/search | 3 | `min_infected` + `build()` return |
| 403-417 | hunt | 15 | `comps()` — generic connected-component BFS over any boolean labelling |
| 420-433 | rule/search | 11 | `violation()` — CEGAR cut-finder |
| 436-461 | hunt | 20 | `FirstSolution` — generic solve-progress/stall callback |
| 464-472 | hunt | 4 | `release_heap()` — generic CP-SAT memory-trim utility |
| 475-490 | hunt | 11 | `solve_with_watchdog()` — generic solve-with-stall-timeout wrapper |
| 493-589 | rule/search | 95 | `solve_valid()` — CEGAR round loop tightly coupled to `build()`/`violation()`; its exclude-and-resolve sub-shape (~10 lines) mirrors `enumerate_witnesses`, but the surrounding cut logic is rule-specific |
| 591-602 | gridfind | 9 | `unique()` — exact match to "solve, exclude that solution, resolve, check UNSAT" = `enumerate_witnesses`'s own pattern |
| 605-621 | hunt | 14 | `strip()` — generic greedy batch-minimization algorithm, no rule knowledge |
| 624-635 | hunt | 12 | `show()` — board pretty-printer |
| 638-646 | rule/search | 8 | `circle_candidates()` — rule-specific |
| 649-665 | rule/search | 16 | `uninfected_groups()` — infection-specific group sizing |
| 668-669 | rule/search | 2 | `clued_bananas()` — rule-specific |
| 672-696 | rule/search | 23 | `sample()` — dispatches rule-specific objective params |
| 699-726 | rule/search | 21 | `generate()` — orchestrates `strip()`+`unique()` with rule-specific circle logic |
| 729-744 | hunt | 16 | `dump()` — JSON output-file writer |
| 747-818 | hunt | 65 | `hunt()` — output dir, progress file, seed loop, avoid-glob (disk-based dedupe) |
| 821-893 | hunt | 70 | `main()` — CLI parsing + subcommand dispatch |

**Totals (722 code lines):** gridfind would replace: **34 (4.7%)**. `finders/hunt/` would replace: **228 (31.6%)**. Rule-or-search specific: **460 (63.7%)**.

## Bugs history would plausibly have caught

1. **[verified] Shared-label connectivity hole (renbanana, commits `ada84fbc`,
   `6e8d4339`, `395ffe5497`, 2026-09-08/09).** The banana size-cap's
   component label was pinned "at most the component's least cell index"
   instead of "equal to," so two disjoint banana components could share one
   label; the renban `AllDifferent`+consecutive check then ran over their
   union, silently admitting illegal shadings (never rejecting legal ones —
   `395ffe5` confirms the 0-of-200 infeasibility proof stood). Caught by
   `renbanana_verify.py`'s independent re-check, not by the CP-SAT encoding
   itself. This is exactly the "labelled-component-with-min-index-root"
   connectivity pattern the gap doc flags as **not yet a gridfind layer**
   (candidate for #771's connectivity measurement). `[inferred]` that folding
   this into gridfind's vetted connectivity encoding (e.g. fillomino's
   flow-based region discovery, which enforces true single-component
   membership rather than a label inequality) would avoid this specific hole
   class — plausible but unbuilt/unmeasured.
2. **[verified] zombo r9c1 clue-set non-uniqueness** (`docs/research/zombo-brainanas/DOTS.md`
   via commit `4420e63b`, #378; later reverted for unrelated content-ownership
   reasons in `89b89c8`). Circling r9c1 instead of r9c2 broke uniqueness via a
   1/3 deadly-rectangle swap that both admitted the same size-9 pocket clue.
   Caught by zombo's own `unique()`/`checkset.py` — the "solve, exclude,
   resolve, expect UNSAT" pattern `gridfind.verdict.enumerate_witnesses`
   already implements natively. This is evidence *for* bucketing `unique()`
   (lines 591-602) as **gridfind would replace**: it shows the plumbing
   genuinely duplicates `enumerate_witnesses`, once zombo's rules are
   expressible as gridfind layers — which, per the bucket table, they mostly
   are not today.
3. **[verified] `probe_circle_pattern.py` silent false-UNIQUE bugs** (commits
   `069b16b4`, `f2a7d4c8`, 2026-09-09; a renbanana research CLI tool, not one
   of the two target files but in the same finder family). Two rounds: an
   unchecked `--known-solution` that didn't actually solve the clue set,
   `--known` blocking the very pool `--unique` searches over, and a
   `MODEL_INVALID` status misreported as a timeout. These are CLI-flag
   validation bugs in ad hoc driver code — squarely `finders/hunt/`
   territory, not a gridfind-layer gap. `[inferred]` a shared, tested hunt
   harness with one validated flag/uniqueness-check path would prevent this
   class recurring; not proven since the harness doesn't exist yet.

## Option 3: could gridfind's *current* layers have replaced each finder's separate verifier?

- **`renbanana_verify.py` (171 lines, ~150 code lines).** Only rule 1 (plain
  9x9 sudoku, lines 84-99, ~14 code lines) maps onto gridfind layers gridfind
  ships today (`board` + `rows-distinct`/`cols-distinct`/`regions-distinct`,
  via a `verdict()` call with the grid as givens). Rules 3-6 — rectangle
  shape, banana non-rectangle, chocolate-adjacency gap conditioned on a free
  shading, renban distinct-consecutive on shading-discovered groups — have no
  current gridfind layer (per the gap doc: free/non-solution shading isn't
  scoped by any open map). So **no**, gridfind could not replace this
  verifier today; it could replace roughly 9% of it (the sudoku-legality
  slice), leaving the checker's actual point (rules 3-6) uncovered.
- **zombo's `verify` subcommand** (`main()`, dispatches to `unique()`,
  lines 883-889 calling 591-602). Unlike renbanana's checker, this was never
  an independently-*derived* verifier — it re-runs the same CEGAR model that
  generates candidates. Its *shape* (prove exactly one solution by
  solve-exclude-resolve) is exactly `enumerate_witnesses`, but the rules it
  proves uniqueness over — infection closure, the rectangle lemma, pocket
  clues — are not expressible as gridfind layers today. So **no**, not with
  today's layers; only the generic "prove uniqueness" plumbing shape
  transfers, and it transfers regardless of which of the three options below
  is chosen, since `enumerate_witnesses` is already public API.

**`finders/hunt/` share of the verifier picture:** neither verify path itself
falls in the hunt bucket (both are rule-checking, not driver plumbing), but a
shared hunt harness would still standardize *how* a finder calls its
verifier (CLI dispatch, output format) — that's part of the `main()`/CLI
lines already counted in the hunt bucket above, not extra.

## Verdict

The "gridfind would replace" share is small and stable across both finders
(6.0% renbanana, 4.7% zombo — board/cell vars, `AllDifferent`, a couple of
solve wrappers, `givens` application, and one uniqueness-proof pattern). The
"`finders/hunt/` would replace" share is five to six times larger (30.7%,
31.6%) and needs zero new gridfind surface — output dir, progress, CLI,
neighbour/component helpers, dedupe, minimization and solve-progress
utilities are all rule-agnostic already. Neither finder's separate verifier
is replaceable by gridfind's *current* layers beyond the plain-sudoku slice,
so option 3 (hunt-protocol first, gridfind as verifier only where its layers
already cover the rule) banks the larger, already-measured win without an
ADR-0001 reversal; option 2's small surface (dependency + `num_workers` +
`build`) covers everything the 4.7-6.0% share actually uses; option 1's full
public `Layer`/promotion contract has no line-count evidence paying for it
yet — it would only start earning its keep once rules gridfind's own gap doc
flags (free shading, the rectangle lemma, infection closure, a fourth
connectivity variant) are promoted into layers, which hasn't happened.
