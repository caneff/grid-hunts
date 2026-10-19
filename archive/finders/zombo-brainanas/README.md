# zombo-brainanas (retired)

Retired 2026-10-19 (issue #50, Chris's ruling): a finished one-off hunt, moved
here from `finders/` with `git mv` so it stops costing maintenance.

- **Last passed the gate at:** `cd60ca7` (the push and nightly full-seam CI
  runs on it succeeded, with both files still under `finders/`).
- **Results:** `docs/research/zombo-brainanas/` (found grids, notes, tools) and
  `docs/research/zombo-brainanas-generation.md`.
- **Known failure:** `docs/research/zombo-brainanas/three_size7.json` fails the
  current rules. `violation()` flags it (the uninfected cells r8c6-r8c8 form a
  rectangle-shaped banana), and `solve_valid` finds no solution even with the
  full stored grid given. Found by #36's prototype; checked again 2026-10-19.
- **Untested from here on.** `tests/all.sh` does not list anything under
  `archive/`. Neither file imports other repo modules, so the move itself
  breaks no import; drift would come from `finders/hunt/` or the solver
  libraries changing under them.
- **Old paths:** dated notes under `docs/research/` (the plumbing-share and
  counting-shaded logs, `zombo-brainanas/tools/README.md`) still name the old
  `finders/zombo_brainanas_*` paths; they are records of their day.
- **Reviving** is a ticket that moves these files back to `finders/` and makes
  their suites pass.
