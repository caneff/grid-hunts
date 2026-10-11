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
  (spec #781): values, regions, circles, a terminal drawing. `brute.py R C`
  counts a tiny board's valid hybrid grids and classifies circle conditions,
  with `--min-bananas N` under that condition too;
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
  `hybrid_finder.py render DIR` draws each example of a hunt as a picture,
  `DIR/renders/<seed>.png` (`hybrid_render.py`, #791): the board with its
  outside numbers and network, chocolate in one colour and a tint per banana,
  a ring on every valid circle and a heavier one in a second colour on a
  circle that is a condition; `--seed N --png FILE` draws one example and
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
  circle is refused by name. `penpa_decode.py` is the test decoder, shared
  by `test_penpa.py` and `test_ubahn_hybrid_links.py`. The browser check takes
  the same `--circles` and `--numbers` to confirm where they sit on the page.
  `finders/ubahn/penpa-browser-check.mjs LINKFILE` is the real-browser check
  (the success dialog, the Line tool, the icons'
  order, the centre point); it needs Chromium and the live page, so
  it stays out of both gates.
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
