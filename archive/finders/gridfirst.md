# gridfirst.py (retired)

Retired 2026-11-13 (issue #142, spec #118): a broken sampler, moved here from
`finders/counting_shaded/` with `git mv` and kept as a recorded dead end.

- **Last passed the gate at:** `5760635` (the push-to-main CI run on it
  succeeded; the file is unchanged since `50569ac`).
- **Why it is dead:** its header says it: `random_grid()` only applies
  sudoku-preserving symmetries to one base grid, so it samples one equivalence
  class, and its reported ceiling of 9 shaded cells is an artefact. The true
  ceiling is 26 (`joint.py --maximize`, confirmed by `recheck_ceiling.py`).
  Account: `docs/research/2026-09-16-counting-shaded-connected-decision-log.md` § 3.
- **Untested from here on.** `tests/all.sh` does not list anything under
  `archive/`; its imports of sibling `finders/counting_shaded/` modules may
  have drifted.
- **Reviving** is a ticket that moves it back to `finders/counting_shaded/`
  and makes its suites pass.
