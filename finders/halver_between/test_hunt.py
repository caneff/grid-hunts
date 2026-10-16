"""The hunt end to end, through the hunt-protocol driver (spec #39 seam 1):
a one-seed hunt on Chris's board writes its output directory, its hit's link
decodes back to exactly his six lines plus the hit's added lines (no entered
digits, colours or marks), and the hit passed `verify` (the driver writes no
example that failed it). `verify` refuses the same hit with its last line
taken away. A hunt whose seed finds nothing records its `Empty` reason and
is summarised as "none found", never as a proof.

A slow test, outside the gate: `just test-slow` runs it (tests/all.sh's
`finder_slow`), since a full 9x9 hunt and its backtracking verify depend on
the box's load. Its time on one core is in the decision log. The gate's
`test_spec_39_e2e.py` covers the same hit's record, link and `verify` on a
recorded hit, without a hunt.

    uv run finders/halver_between/test_hunt.py
"""

import json
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
    for name in ("run.json", "summary.json", "progress.jsonl", "examples.jsonl"):
        assert (out / name).exists(), name
    (event,) = [json.loads(line) for line in (out / "progress.jsonl").open()]
    assert event["outcome"] == "example", event
    (record,) = [json.loads(line) for line in (out / "examples.jsonl").open()]

    # The link holds Chris's six lines, then the hit's, and nothing entered.
    finder = hunt.HalverBetweenFinder(
        max_cells=8,
        pool=20,
        time_limit=30.0,
        max_lines=40,
        max_seconds=120.0,
        verify_seconds=600.0,
    )
    hit = finder.candidate_from_record(record)
    assert hit.added, record
    doc = decode_puzzle(record["link"])
    assert rules.lines_from_doc(doc) == hunt.BOARD + list(hit.added)
    assert all(cell == {} for cell in doc["puzzle"]["cells"]), "entered marks kept"
    (group,) = [
        c for c in doc["puzzle"]["constraints"] if c.get("type") == rules.BETWEEN_LINE
    ]
    (board_group,) = [
        c
        for c in hunt.BOARD_DOC["puzzle"]["constraints"]
        if c.get("type") == rules.BETWEEN_LINE
    ]
    assert group["style"] == board_group["style"], group["style"]
    # The table is the same lines in rNcM form, numbered on from L6.
    assert record["table"] == [
        f"L{i} | {rules.line_name(line)}" for i, line in enumerate(hit.added, start=7)
    ]

    # The hit's solution obeys every line, and without its last line the
    # backtracking check finds a second solution, so verify refuses it.
    assert all(
        rules.line_holds(hit.solution, line) for line in hunt.BOARD + list(hit.added)
    )
    short = hunt.Hit(hit.added[:-1], hit.solution)
    verdict = finder.verify(short)
    assert not verdict.ok and "2 solutions" in verdict.reason, verdict

    summary = run("summary", str(out))
    assert summary.returncode == 0, summary.stderr
    assert summary.stdout.startswith("1 hits in 1 seeds (0..0)"), summary.stdout
    assert record["link"] in summary.stdout

    # No time to sample a target: the seed is Empty with its reason, and the
    # summary says "none found" with the seeds and time, not a proof.
    none = Path(tmp) / "none"
    result = run("--out", str(none), "--seeds", "0:2", "--time-limit", "1e-6")
    assert result.returncode == 0, result.stderr
    events = [json.loads(line) for line in (none / "progress.jsonl").open()]
    assert [e["outcome"] for e in events] == ["empty", "empty"], events
    assert all(e["empty_reason"].startswith("timeout") for e in events), events
    summary = run("summary", str(none))
    assert summary.returncode == 0, summary.stderr
    first = summary.stdout.splitlines()[0]
    assert first.startswith("none found in 2 seeds (0..1), wall clock"), first
    assert "not a proof" in first, first
    assert "seed 1: timeout" in summary.stdout, summary.stdout

    # A directory with no hunt in it is refused by name, not read as empty.
    missing = run("summary", str(Path(tmp) / "nothing"))
    assert missing.returncode == 2, missing
    assert "holds no hunt" in missing.stderr, missing.stderr

print("ok")
