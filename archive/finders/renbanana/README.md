# renbanana (retired)

Retired 2026-10-16 (issue #45, Chris's ruling): a finished one-off hunt, moved
here from `finders/renbanana/` with `git mv` so it stops costing gate time.

- **Last passed the gate at:** `3456ca6` (the push-to-main CI run on it
  succeeded; this folder is unchanged since `cf80af5`).
- **Results:** `docs/research/renbanana/` and `docs/research/2026-09-16-renbanana-two-stage-uniqueness.md`. Its loose modules `renbanana_{cpsat,model,render,verify}.py` moved with it to `archive/finders/`; banabner imports them.
- **Scripts elsewhere:** `docs/research/renbanana/tools/run_{arm,overnight,walk}.sh`
  still call `finders/renbanana/tools/*.py`; point them at this folder to rerun.
- **Untested from here on.** `tests/all.sh` does not list anything under
  `archive/`, so imports of `finders/hunt/` or of other loose modules, and
  any `Path(__file__).parents[n]` lookup, may have drifted.
- **Reviving** is a ticket that moves this folder back to `finders/renbanana/`
  and makes its suites pass.
