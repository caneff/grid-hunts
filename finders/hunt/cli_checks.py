"""Shared helpers for the standalone finder test scripts (#8).

A test script calls `check(name, cond)` for each assertion and ends with
`finish()`, which exits 1 if any check failed. `run_cli` launches a finder
script as a subprocess under `success_env`, so the hunt's load gate reads
idle (#526). The module is not named `test_*`: the gate runs every
`test_*.py` it finds by glob."""

import json
import subprocess
import sys

from subprocess_env import success_env

_failed = False


def check(name, cond):
    global _failed
    if not cond:
        _failed = True
    print(f"{'ok' if cond else 'FAIL'}: {name}")


def finish():
    sys.exit(1 if _failed else 0)


def read_jsonl(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line]


def run_cli(script, *args):
    return subprocess.run(
        [sys.executable, str(script), *map(str, args)],
        capture_output=True,
        text=True,
        env=success_env(),
    )
