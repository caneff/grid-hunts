# galaxy-copycat (retired)

Retired 2026-10-16 (issue #45, Chris's ruling): a finished one-off hunt, moved
here from `finders/galaxy-copycat/` with `git mv` so it stops costing gate time.

- **Last passed the gate at:** `fec7648` (the last completed green push to
  main before the move; this folder is unchanged since `cf80af5`).
- **Results:** `docs/research/2026-09-14-galaxy-copycat-design.md`, `docs/research/2026-09-14-copycat-scan.md` and the boards in `docs/research/2026-09-14-galaxy-copycat/`.
- **Untested from here on.** `tests/all.sh` does not list anything under
  `archive/`, so imports of `finders/hunt/` or of other loose modules, and
  any `Path(__file__).parents[n]` lookup, may have drifted.
- **Reviving** is a ticket that moves this folder back to `finders/galaxy-copycat/`
  and makes its suites pass.
