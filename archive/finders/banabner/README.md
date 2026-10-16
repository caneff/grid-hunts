# banabner (retired)

Retired 2026-10-16 (issue #45, Chris's ruling): a finished one-off hunt, moved
here from `finders/banabner/` with `git mv` so it stops costing gate time.

- **Last passed the gate at:** `fec7648` (the last completed green push to
  main before the move; this folder is unchanged since `cf80af5`).
- **Results:** `docs/research/banabner/` (decision log, checked grids, lineup record). It imports `renbanana_*.py`, now in `archive/finders/`.
- **Untested from here on.** `tests/all.sh` does not list anything under
  `archive/`, so imports of `finders/hunt/` or of other loose modules, and
  any `Path(__file__).parents[n]` lookup, may have drifted.
- **Reviving** is a ticket that moves this folder back to `finders/banabner/`
  and makes its suites pass.
