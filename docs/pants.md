# Pants chooses the narrowed run's suites

`bash tests/all.sh --changed <base>` asks Pants which suites a diff reaches:
the suites among the transitive dependents of the changed files, in one call
(`pants dependents --transitive --closed <files>`). Pants selects and nothing
more; every suite still runs from the tree as `uv run <file>`. Nobody calls
Pants by hand to run the gate, and the header of `tests/all.sh` is the one
statement of when a run narrows and when it widens.

Pants 2.33.1, as `pants.toml` pins it: no daemon, one process, no result
cache, the same settings as `caneff/sudokumaker-custom-constraints`. Install
the launcher once per box
(https://www.pantsbuild.org/stable/docs/getting-started/installing-pants);
CI installs it with `pantsbuild/actions/init-pants`. With no `pants` on the
PATH a narrowed run widens to the whole seam and says so.

## Wiring a code directory

Every directory under `finders/` that holds Python has a `BUILD` file of one
`code_dir(...)` call (`tests/pants_prelude.py`). `code_dir()` owns the
directory's `*.py` and, as `data`, every other file under it but `.md`, the
`BUILD` file included; each Python file depends on that data, so a fixture or
`BUILD` change selects the whole directory and everything that imports from it.

A finder imports its neighbours through `sys.path.insert`, which Pants does
not read. `pants.toml`'s `[source] root_patterns` make each such directory a
source root (`/finders/*` and `/finders/qqrr/hunt`), so `import verified_io`
resolves to `finders/hunt/verified_io.py`. Two roots holding a module of one
name resolve to the importer's own root; an import neither root owns is
ambiguous, and `tests/test_pants_edges.py` fails on it until the BUILD file
names the one meant (`finders/ubahn/BUILD` names `finders/hunt/render.py`).

A new finder folder needs its `BUILD` file before the gate passes: without
one, `tests/test_pants_edges.py` fails naming its suites, and any change in
the folder widens the run.

## An edge no import shows

A test that starts a script as a subprocess does not import it, so its
`BUILD` file names it under `edges`:

```python
code_dir(edges={"test_report.py": ["./report.py:py"]})
```

`tests/test_pants_edges.py` reads every finder source for a string naming a
`.py` file (`"hunt.py"`, `HERE / "toy_finder.py"`) and fails on each one the
source does not reach in Pants's graph, so a missing entry is a red gate, not
a suite skipped in silence. It also holds a short table of known edges, each
with the suites a change must and must not select.

Files a suite reads under `docs/` belong to no target, so a change to one
widens the run, as before.

## What was measured

`docs/research/2026-10-22-pants-selection.md`: the selection #69's diff gets,
and the time Pants takes to answer.
