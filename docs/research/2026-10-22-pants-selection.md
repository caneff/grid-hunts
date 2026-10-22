# Pants selection on #69's diff: what #76 measured

2026-10-22, ticket #76. Pants 2.33.1 as `pants.toml` pins it. One box (WSL2),
shared. Every number is one worker's measurement, to re-run with the command
shown.

## The case

#69 (Doppelganger rank hunt) moved a helper into `finders/hunt/verified_io.py`
and edited `finders/halver/halver_hunt.py`, beside a new
`finders/doppelganger_rank/`. The runner before #76 widened on any change
under `finders/hunt/`, so #69's narrowed run ran every non-slow suite one at a
time: about 15 min, per the ticket (CI's serial full seam was 15 min 15 s).

## What Pants selects

On a throwaway worktree of #76's branch with #69's diff applied (branch
`implement-69` at `1e3875a`, against `origin/main` at `a678311`) plus a
`finders/doppelganger_rank/BUILD`:

```
bash tests/all.sh --list --changed HEAD~1
```

| | Suites |
|---|---|
| lint (ruff check, ruff format, `uv lock --check`) | 3 |
| always run (`tests/test_all_sh.py`, `tests/test_pants_edges.py`) | 2 |
| `doppelganger_rank`'s own tests | 4 |
| importers of `verified_io` or `halver_hunt`, at any distance | 15 |
| **Selected** | **24 of 67** |

The 15 importers: `halver_between` test_cli, test_propose, test_spec_39_e2e;
`halver_lockout` test_cli, test_spec_52_e2e; `hunt/test_hunt_verify.py`;
`qqrr/hunt` test_hunt_smoke (it compiles `tie_finder.py`, an importer) and
test_tie_finder; `ubahn` test_ubahn_battenberg_e2e, battenberg_hunt,
fewest_markings, fewest_markings_e2e, hunt, hybrid_e2e, hybrid_hunt. The
slow `halver_between/test_hunt.py` and `halver_lockout/test_hunt.py` import
them too and stay outside the gate.

Pants answered in 2.6 s (`time bash tests/all.sh --list --changed HEAD~1`).
The selected run, `bash tests/all.sh --changed HEAD~2` one suite at a time,
passed 24 of 24 in 440 s.

## What the edge check caught on that diff

`tests/test_pants_edges.py` on the same tree, before the BUILD file named
any edge, failed on two: `doppelganger_rank/test_check.py` and
`test_opening.py` start `check.py` as a subprocess and import nothing from
it. The BUILD file #69 needs when it lands:

```python
finder(edges={"test_check.py": ["./check.py:py"], "test_opening.py": ["./check.py:py"]})
```

On the main tree the check found 22 such edges and one ambiguous import
(`ubahn/hybrid_render.py` imports `render`, which both `finders/hunt` and
`finders/counting_shaded` hold); the BUILD files now name each.

## Pants's own behaviour, as found

- `pants dependents` on an existing file no target owns prints nothing for it
  and exits 0, so the runner reads "not placed" off a missing `<file>:` line.
  A file that does not exist is an error, and the runner widens on a deleted
  file before asking.
- `unmatched_build_file_globs = "ignore"` (to quiet an empty `data` glob)
  makes an explicit file dependency such as `./report.py:py` fail with
  `ValueError: Provided description_of_origin while ignoring glob match
  errors`. `finder()`'s `data` owns the BUILD file instead, so no glob is
  empty and the option stays at its default.
- `pants dependencies --format=json finders::` returns the whole graph, 198
  targets, in 2.3 s; the edge check makes that one call.
