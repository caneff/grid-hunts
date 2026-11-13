# Finders are scripts on sys.path, not packages

Status: accepted (Chris, 2026-11-13, all-audits sweep triage, caneff/grid-hunts#113)

Every finder under `finders/` is a folder of standalone scripts that load
their neighbours with `sys.path.insert` and a bare module name, and every
test runs as `uv run <file>`. We keep it that way and do not turn `finders/`
into an importable package with qualified imports.

The package route was weighed and declined. It would let Pants infer edges
instead of reading the hand-kept `BUILD` lists that `tests/test_pants_edges.py`
polices, let `ty` and an import-linter contract run, and end the bare-name
collisions (`rules`, `brute`, `hunt`, `render`). But it touches every finder,
the `BUILD` layout in `docs/pants.md` and every subprocess-run test, in a
checkout several agents share, for one-off hunts that gain little from a type
checker. The collisions are already caught by the Pants edge check.

## Consequences

- No type checker runs on the finders (`ruff.toml` says why), so tightening
  an `Any` to a named type, or writing a contract as a `typing.Protocol`, is
  documentation only and is not asked for by audits.
- A new finder folder still needs its `BUILD` file and its edges by hand
  (`docs/pants.md`).
