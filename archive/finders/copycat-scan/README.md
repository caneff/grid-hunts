# copycat-scan (retired)

Retired 2026-10-16 (issue #45, Chris's ruling): a finished one-off hunt, moved
here from `finders/copycat-scan/` with `git mv` so it stops costing gate time.

- **Last passed the gate at:** `3456ca6` (the push-to-main CI run on it
  succeeded; this folder is unchanged since `cf80af5`).
- **Results:** `docs/research/2026-09-14-copycat-scan.md`.
- **Untested from here on.** `tests/all.sh` does not list anything under
  `archive/`, so imports of `finders/hunt/` or of other loose modules, and
  any `Path(__file__).parents[n]` lookup, may have drifted.
- **Reviving** is a ticket that moves this folder back to `finders/copycat-scan/`
  and makes its suites pass.
