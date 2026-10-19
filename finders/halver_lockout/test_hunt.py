"""The lockout hunt end to end, through the hunt-protocol driver (spec #52,
#56): a one-seed hunt from the empty board writes its output directory, its
hit's link decodes back to exactly the hit's lines as type 407 with
`solverIgnored` and nothing entered, and the hit passed `verify` (the driver
writes no example that failed it). `verify` refuses the same hit with its
last line taken away. A hunt whose seeds find nothing records each `Empty`
reason and is summarised as "none found", never as a proof.

A slow test, outside the gate: `just test-slow` runs it (tests/all.sh's
`finder_slow`), since a full 9x9 hunt and its backtracking verify run for
minutes and depend on the box's load. Its time is in the decision log.

    uv run finders/halver_lockout/test_hunt.py
"""

import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "hunt"))

# isort: split
import hunt
import rules
from subprocess_env import success_env
from sudoku_kit.link_codec import decode_puzzle

SCRIPT = HERE / "hunt.py"


def run(*argv):
    return subprocess.run(
        ["uv", "run", str(SCRIPT), *argv],
        capture_output=True,
        text=True,
        env=success_env(),
    )


with tempfile.TemporaryDirectory() as tmp:
    out = Path(tmp) / "hits"
    result = run("--out", str(out), "--seeds", "0:1")
    assert result.returncode == 0, result.stderr
    (event,) = [json.loads(line) for line in (out / "progress.jsonl").open()]
    assert event["outcome"] == "example", event
    (record,) = [json.loads(line) for line in (out / "examples.jsonl").open()]

    finder = hunt.HalverLockoutFinder(**hunt.DEFAULTS)
    hit = finder.candidate_from_record(record)
    assert hit.added, record
    doc = decode_puzzle(record["link"])
    assert rules.lines_from_doc(doc) == list(hit.added)
    (group,) = [c for c in doc["puzzle"]["constraints"] if c.get("type") == 407]
    assert group["solverIgnored"] is True, group
    assert all(cell == {} for cell in doc["puzzle"]["cells"]), "entered marks kept"
    assert all(rules.line_holds(hit.solution, line) for line in hit.added)

    short = hunt.Hit(hit.added[:-1], hit.solution)
    verdict = finder.verify(short)
    assert not verdict.ok and "2 solutions" in verdict.reason, verdict

    summary = run("summary", str(out))
    assert summary.returncode == 0, summary.stderr
    assert summary.stdout.startswith("1 hits in 1 seeds (0..0)"), summary.stdout
    assert record["link"] in summary.stdout

    # No time to sample a target: each seed is Empty with its reason, and the
    # summary says "none found" with the seeds and time, not a proof.
    none = Path(tmp) / "none"
    result = run("--out", str(none), "--seeds", "0:2", "--time-limit", "1e-6")
    assert result.returncode == 0, result.stderr
    summary = run("summary", str(none))
    assert summary.returncode == 0, summary.stderr
    first = summary.stdout.splitlines()[0]
    assert re.match(r"none found in 2 seeds \(0\.\.1\), wall clock \d+ s: ", first), (
        first
    )
    assert "not a proof" in first, first
    assert "seed 1: timeout" in summary.stdout, summary.stdout

print("ok")
