"""Shared helpers for the standalone finder test scripts (#8).

A test script calls `check(name, cond)` for each assertion and ends with
`finish()`, which exits 1 if any check failed. `check_refusal` asserts a
refusal's exit 2 and its text. `run_cli` launches a finder
script as a subprocess under `success_env`, so the hunt's load gate reads
idle (#526). The module is not named `test_*`: the gate runs every
`test_*.py` it finds by glob."""

import json
import subprocess
import sys
from pathlib import Path

from subprocess_env import success_env

_failed = False


def check(name, cond):
    global _failed
    if not cond:
        _failed = True
    print(f"{'ok' if cond else 'FAIL'}: {name}")


def finish():
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
    """`env` is `success_env`'s overrides: a test of the load gate passes its
    own HUNT_FAKE_LOAD1."""
    return subprocess.run(
        [sys.executable, str(script), *map(str, args)],
        capture_output=True,
        text=True,
        env=success_env(env),
    )
