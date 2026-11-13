"""Helpers for the standalone finder test scripts (#8).

`run_cli` runs a finder under `success_env` so the load gate reads idle.
Not named `test_*`: the gate runs every `test_*.py` it globs."""

import json
import subprocess
import sys
from pathlib import Path

from subprocess_env import success_env

_failed = False


def check(name, cond):
    """Print `ok`/`FAIL` for one assertion and remember a failure for `finish`."""
    global _failed
    if not cond:
        _failed = True
    print(f"{'ok' if cond else 'FAIL'}: {name}")


def finish():
    """Exit 1 if any `check` failed, else 0."""
    sys.exit(1 if _failed else 0)


def check_refusal(name, result, text):
    """A refusal check: the hunt exited 2 and said `text` on stderr. A bare
    nonzero exit would also pass on an unrelated crash (exit 1, traceback)."""
    check(
        f"{name} (exit 2, stderr names {text!r}; stderr: {result.stderr[-300:]})",
        result.returncode == 2 and text in result.stderr,
    )


def read_jsonl(path, missing_ok=False):
    path = Path(path)
    if missing_ok and not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def run_cli(script, *args, env=None):
    """Run `script` with `args` as a subprocess under `success_env(env)`; a
    test of the load gate passes its own HUNT_FAKE_LOAD1 in `env`."""
    return subprocess.run(
        [sys.executable, str(script), *map(str, args)],
        capture_output=True,
        text=True,
        env=success_env(env),
    )
