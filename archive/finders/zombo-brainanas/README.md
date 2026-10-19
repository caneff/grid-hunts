# zombo-brainanas (retired)

Retired 2026-10-19 (issue #50, Chris's ruling): a finished one-off hunt, moved
here from `finders/` with `git mv` so it stops costing maintenance.

- **Last passed the gate at:** `cd60ca7` (the nightly full-seam CI run on it
  succeeded; neither file has changed since the move to `finders/`).
- **Results:** `docs/research/zombo-brainanas/` (found grids, notes, tools) and
  `docs/research/zombo-brainanas-generation.md`.
- **Known failure:** `docs/research/zombo-brainanas/three_size7.json` fails the
  current rules. `violation()` flags it (an all-chocolate 1x3 rectangle in the
  bottom-right corner), and `solve_valid` finds no solution even with the full
  stored grid given. Found by #36's prototype; checked again 2026-10-19.
- **Untested from here on.** `tests/all.sh` does not list anything under
  `archive/`, so imports of `finders/hunt/` or of other loose modules, and
  any `Path(__file__).parents[n]` lookup, may have drifted. The commands in
  `docs/research/zombo-brainanas-generation.md` still name `finders/` paths.
- **Reviving** is a ticket that moves these files back to `finders/` and makes
  their suites pass.
