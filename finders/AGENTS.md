# finders/AGENTS.md

Grid finders: JavaScript-adjacent Python code that hunts, verifies, and
renders candidate grids for constraint prototypes. The `.py` finder code
lives here; notes, hunt outputs, precomputed catalogues, and the `.sh`
drivers that launch a hunt overnight stay under `docs/research/` (#469).
A finder's own input fixture stays beside its code: `finders/qqrr/` holds
the opener link, its decoded JSON and the notes that classify its marks,
because the checker reads them and nothing under `docs/research/` does
(owner ruling on #595, S1).

## Renbanana chocolate facts are precalculated (always on)

- **Never re-derive a chocolate rectangle fact the catalogue already holds.**
  `docs/research/renbanana/rectangle-catalogue.json` enumerates, per shape and
  per box offset, which placements can be filled at all, the per-cell digit
  domains, and which cells can carry a circle. Every generator question about
  a chocolate rectangle is answered from it, in stage 1 and stage 3 alike —
  not left for the solver to search out on each shading.
- It is layer B (the rectangle plus the boxes, nothing outside), so a real grid
  only narrows its answers. That is what makes reading it sound.
- `finders/renbanana/tools/test_catalogue_is_used.py` fails if a call site
  drops it. Run it after touching `renbanana_cpsat.py`.
- The catalogue is rebuilt by `finders/renbanana/tools/build_rectangle_catalogue.py
  --difference <n>`; difference 5 reproduces the file above byte for byte, and
  other differences write `rectangle-catalogue-d<n>.json` beside it (#760).
  At difference 4 the biggest layers hit the builder's count cap (`truncated`:
  the count is a floor, the support is exact from CP-SAT).
- The Banabner finder (`finders/banabner/`) reads `rectangle-catalogue-d4.json`
  the same way, at both call sites; `finders/banabner/test_catalogue_is_used.py`
  fails if one drops it.

## Pointers

- Before writing a new finder, start from `finders/hunt/`: the shared hunt
  protocol (a `typing.Protocol` of `propose`/`verify`/`record`/`key`/
  `symmetry`, and the `hunt` CLI's `run(finder, argv)`) that gives a fresh
  hunt its output directory and dedupe for free. `finders/hunt/toy_finder.py`
  is a minimal worked example; `finders/qqrr/hunt/tie_finder.py`, a new finder
  over `chan_big.py`'s model, is the first real one. Other existing finders
  are not ported onto it.
- `finders/ubahn/` is the U-Bahn finder (a pencil puzzle, no sudoku), on the
  hunt protocol: `ubahn_finder.py` its docstring and flags, `model.py` the
  CP-SAT model, `network.py` the solver-free rules `verify` reads;
  `sat_model.py` is a prototype second uniqueness check on PySAT (#776), which
  the plain finder does not call. `measure_baseline.py` times a hunt's proposal
  step per seed and cause (#777; by hand, outside both gates). Conditions
  arrive one at a time as finder rules. Preflight answers and measurements:
  `docs/research/2026-10-10-u-bahn-finder-decision-log.md`.
  `hybrid.py` is the solver-free rule reader of the hybrid with Choco-Banana
  (spec #781): values, regions, circles, windows and Battenberg markings,
  a terminal drawing. `brute.py R C`
  counts a tiny board's valid hybrid grids and classifies circle conditions,
  with `--min-bananas N` under that condition too; `--battenberg "CELLS"`
  classifies a set of Battenberg markings, each window by its top-left cell,
  and `--battenberg-only` adds the negative constraint (#21);
  the 4x4 answers every engine must match are in the decision log, § Hybrid.
  `hybrid_finder.py` is the hybrid finder on the hunt protocol (#783): the
  conditions `--circles "r6:turn r2c3"`, `--exactly N:PIECE:rK`,
  `--blank-strip` and `--min-bananas N` (at least N banana regions, #792,
  on every engine) in, valid grids out, one per seed, each re-read by
  `hybrid.py` in `verify`; `hybrid_finder.py classify` takes the same
  conditions and answers `infeasible`, `unique`, `not_unique` or `timeout`;
  `--help` prints the usage text. `--engine` picks the solver: `cpsat`
  (`hybrid_model.py`, the plain model plus the hybrid's rules), or
  `pysat-lazy`, the default by Chris's ruling of 2026-10-11, and
  `pysat-propagator` (`hybrid_sat.py`, #784 and #785: the
  rules as clauses over `sat_model.py`'s, with connectivity kept by cuts on
  full grids or by a propagator during the search).
  `hybrid_sat.listing` returns up to a cap of grids with its cut and conflict
  counts.
  **A new hybrid condition is written on the PySAT engines only** (Chris's
  ruling of 2026-10-12): its clauses in `hybrid_sat.py`, which both PySAT
  engines share, its reading in `hybrid.py` and its 4x4 answers from
  `brute.py`. `--engine cpsat` refuses the new flag by name and is given no
  model of it. The conditions already on all three engines stay there.
  `--battenberg "c1:turn r3c1"` is the first such condition (spec #20, #22):
  each named window, a 2x2 of board cells named by its top-left cell, is a
  checkerboard window in every grid returned, and `--battenberg-only` is the
  negative constraint, no checkerboard window but the marked ones, the
  number strips included. Both go on the hunt and on `classify`, with
  `--circles` if wanted; a window not wholly on the board is refused, naming
  the cell. A record carries `battenberg`, `battenberg_only` and
  `checkerboard_windows`, every checkerboard window of its grid. The 4x4
  answers and the 5x5 check against the rule reader: the decision log,
  § Hybrid: Battenberg markings.
  `--number-circles K` is the condition "at least K valid circles on number
  cells" (#794), on all three engines; a grid cell that is a valid circle
  counts for nothing. `hybrid_finder.py climb --out DIR` is its hunt: it
  raises K until no grid reaches it, each step a hunt directory
  `DIR/at-least-K` and a line of `DIR/climb.jsonl`, and calls the maximum
  proven only when one more came back as no grid, never on a time limit
  reached. The 7x7 run of record: the decision log, § Hybrid: the most valid
  circles on number cells.
  `hybrid_finder.py fewest-markings --out DIR` finds the fewest Battenberg
  markings that leave exactly one grid with the negative constraint on
  (spec #29, #30), on the PySAT engines only. It classifies no markings, then
  every set of 1 window, then every set of 2, the other conditions as fixed
  background, and stops at the first size with a `unique` set, up to
  `--max-size K` (3 unless given); `--workers N` splits one size's sets over
  N processes. Each set tried is a line of `DIR/sets.jsonl`, so a killed run
  resumes, a last line cut short dropped and any other line that does not
  read refused; a mirror pair is solved once where the conditions keep the
  reflection; each unique set of the smallest size is a hunt directory under
  `DIR` that `verify`, `render` and `links` read, its grid the one the set's
  own solve found. A set that reached the time
  limit is named and the minimum is then not called proven (#33: settling
  one needs a new directory). `test_ubahn_fewest_markings_e2e.py` is spec
  #29 end to end. The 4x4 answer
  and the 7x7 run of record: the decision log, § Hybrid: the fewest Battenberg
  markings.
  `hybrid_finder.py render DIR` draws each example of a hunt as a picture,
  `DIR/renders/<seed>.png` (`hybrid_render.py`, #791): the board with its
  outside numbers and network, chocolate in one colour and a tint per banana,
  a heavy ring in a second colour on a circle that is a condition and no ring
  on any other valid circle (#31), and a small checkerboard symbol at the centre
  of every checkerboard window, heavier and in the second colour on a window
  that is a Battenberg marking of the hunt (#23); `--seed N --png FILE` draws one example and
  `--blank-strip` the fifth strip.
  `time_engines.py run --engine E --progress FILE` times one engine on
  Chris's six cases and `time_engines.py report FILE...` prints the table and
  the reading against the 2-times bar (#786; by hand, outside both gates). The
  run of record and its progress files:
  `docs/research/2026-10-10-u-bahn-optimization-queue.md`, § The three hybrid
  engines, timed.
  `time_bananas.py run --progress FILE` times one grid per seed for each
  `--min-bananas N` and `time_bananas.py report FILE` prints the table (#792;
  by hand, outside both gates). The run of record is in the decision log,
  § Hybrid: at least N banana regions, and its rows in
  `docs/research/2026-10-11-u-bahn-min-bananas-timing/`.
  `ubahn_finder.py links DIR [--blank-number]` writes a Penpa+ link per example
  to `DIR/links/<seed>.txt` (`penpa.py`, #774; wire format
  `docs/research/2026-10-10-u-bahn-penpa-link.md`). The three published links
  it is tested against are `finders/ubahn/fixtures/`.
  `hybrid_finder.py links DIR --circles "CELLS" --numbers "CELLS"
  [--blank-strip]` writes the hybrid's Penpa+ link per example (#795): only
  the circles and the number cells you name are shown, the grid dotted, the
  combined rules text, the plain link's lines-only answer check; an invalid
  circle is refused by name. `--battenberg "CELLS"` puts Penpa+'s checkerboard
  symbol on the centre of each named window and a sentence in the rules, and
  `--battenberg-only` a second sentence, that every one is given (#24; the
  symbol and its wire form: the link note, § 10); a window that is no
  checkerboard window of the example is refused by name. `penpa_decode.py` is the test decoder, shared
  by `test_penpa.py` and `test_ubahn_hybrid_links.py`. The browser check takes
  the same `--circles`, `--numbers` and `--battenberg` to confirm where they
  sit on the page.
  `finders/ubahn/penpa-browser-check.mjs LINKFILE` is the real-browser check
  (the success dialog, the Line tool, the icons'
  order, the centre point); it needs Chromium and the live page, so
  it stays out of both gates.
- `finders/halver_between/` is the halver + between-line rule check (spec #39):
  `rules.py` the CP-SAT model and per-mark check, `brute.py` the independent
  backtracking check, `report.py` the status of Chris's board and his marks;
  facts to build on: `docs/research/2026-10-16-halver-between-truths.md`.
- `finders/galaxy-copycat/`'s write-ups live in `docs/research/2026-09-14-copycat-scan.md`
  and `docs/research/2026-09-14-galaxy-copycat-design.md`; its boards are
  `docs/research/2026-09-14-galaxy-copycat/boards/`.
- `finders/galaxy-copycat/human_solver.py` is the candidate-carrying human
  solver for copycat + paired region-sum lines — the acceptance test for
  whether a board is human-solvable (design doc, "Ruling (2026-09-17)").
- **Before starting a hunt, answer the preflight** at the top of
  `docs/agents/grid-finder-lessons.md` in writing, and keep a decision log as
  the hunt runs. Six lessons in that file were re-derived the expensive way by
  a later hunt that never read it; the preflight is what closes that loop.
  The doc also covers what to search, when cuts beat a counter, reading solver
  status honestly, profiling the loop, the `ctypes` C port and counting what
  you found. A worked log:
  `docs/research/2026-09-16-counting-shaded-connected-decision-log.md`.
