# finders/AGENTS.md

Grid finders: JavaScript-adjacent Python code that hunts, verifies, and
renders candidate grids for constraint prototypes. The `.py` finder code
lives here; notes, hunt outputs, precomputed catalogues, and the `.sh`
drivers that launch a hunt overnight stay under `docs/research/` (#469).

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
  is a minimal worked example. Existing finders are not ported onto it.
- Before writing a new finder — what to search, when cuts beat a counter,
  profiling the loop, the `ctypes` C port, counting what you found:
  `docs/agents/grid-finder-lessons.md`.
- `finders/galaxy-copycat/`'s write-ups live in `docs/research/2026-09-14-copycat-scan.md`
  and `docs/research/2026-09-14-galaxy-copycat-design.md`; its boards are
  `docs/research/2026-09-14-galaxy-copycat/boards/`.
