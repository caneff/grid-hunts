"""The hunt end to end at 9x9 (#72), in `just test-slow`: from Chris's
opening (`fixtures/opening_9x9.json`), seed 72 of the hunt of record finds
the recorded hit (`fixtures/hit_9x9.json`) again, `verify` passes it,
`summary` lists it as the one verified hit with the seed split, and `links`
writes the link the hunt of record wrote. The hunt runs on the defaults,
one CP-SAT worker; the hunt of record ran the minimiser on 8
(`--proof-workers 8`), which changes no hit.

    uv run finders/doppelganger_rank/test_hunt_9x9.py
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "hunt"))

# isort: split
from subprocess_env import success_env

SCRIPT = HERE / "hunt.py"
BOARD = HERE / "fixtures" / "opening_9x9.json"
fixture = json.loads((HERE / "fixtures" / "hit_9x9.json").read_text())


def run(*args):
    return subprocess.run(
        [sys.executable, str(SCRIPT), *map(str, args)],
        capture_output=True,
        text=True,
        env=success_env(),
    )


with tempfile.TemporaryDirectory() as tmp:
    out = Path(tmp) / "hunt"
    result = run("--board", BOARD, "--out", out, "--seeds", "72:73")
    assert result.returncode == 0, result.stderr
    (record,) = [json.loads(line) for line in (out / "examples.jsonl").open()]
    record.pop("__dedupe_key__")
    assert record == fixture["record"], record

    result = run("verify", out)
    assert result.returncode == 0, result.stderr
    stamp, verdict = [json.loads(line) for line in (out / "verified.jsonl").open()]
    assert verdict["ok"], verdict

    result = run("summary", out)
    assert result.returncode == 0, result.stderr
    lines = result.stdout.splitlines()
    assert lines[0] == "1 verified hits in 1 seeds (72..72)", lines
    assert lines[1] == (
        "1 seeds (72..72): found 1, duplicate 0, proven infeasible 0, "
        "timed out 0, capped 0 (a budget ran out: no proof), "
        "no separating clue 0, rejected 0"
    ), lines
    assert lines[2].startswith("hit, 11 added clues: "), lines

    result = run("links", out)
    assert result.returncode == 0, result.stderr
    assert [p.name for p in (out / "links").iterdir()] == ["72.txt"]
    assert (out / "links" / "72.txt").read_text().strip() == fixture["link"]

print("ok")
