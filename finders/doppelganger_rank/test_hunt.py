"""The hunt end to end at 4x4 (#69), judged against the answer key
(`brute.py`), which takes no part in the hunt:

- A hunt from an empty 4x4 board finds hits. Each hit's clues are `unique`
  by the key, its one grid is the hit's solution, and that solution is its
  seed's target. The board's mark is no constraint: some hit breaks it.
- No hit keeps a clue: the key finds every hit not unique without any one
  of its added clues.
- `verify` refuses a planted record whose grid breaks a rule, and one whose
  clue its grid does not keep, naming each; it passes the record they were
  planted from.
- `summary` lists the hits, fewest added clues first, and splits the seeds
  into found, proven infeasible, timed out and capped, the capped count
  labelled as no proof, on a hunt of each.
- A hunt killed partway resumes to the same hits as the hunt that ran
  through.

    uv run finders/doppelganger_rank/test_hunt.py
"""

import json
import random
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "hunt"))

# isort: split
import brute
import hunt
from subprocess_env import success_env

SCRIPT = HERE / "hunt.py"
SEEDS = 20
SPLIT = re.compile(
    r"(\d+) seeds .*: found (\d+), duplicate (\d+), proven infeasible (\d+), "
    r"timed out (\d+), capped (\d+) \(a budget ran out: no proof\), "
    r"no separating clue (\d+), rejected (\d+)"
)


def command(*args):
    return [sys.executable, str(SCRIPT), *map(str, args)]


def run(*args):
    return subprocess.run(
        command(*args), capture_output=True, text=True, env=success_env()
    )


def jsonl(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line]


def split(out):
    """The summary's seed split, as a dict, and the summary's lines."""
    result = run("summary", out)
    assert result.returncode == 0, result.stderr
    lines = result.stdout.splitlines()
    (match,) = [m for line in lines if (m := SPLIT.fullmatch(line))]
    names = ("seeds", "found", "duplicate", "infeasible", "timeout", "capped")
    names += ("inseparable", "rejected")
    counts = dict(zip(names, map(int, match.groups()), strict=True))
    assert counts["seeds"] == sum(v for k, v in counts.items() if k != "seeds")
    return counts, lines


def grid(record):
    return tuple(tuple(map(int, row)) for row in record["solution"])


with tempfile.TemporaryDirectory() as tmp:
    tmp = Path(tmp)
    empty = tmp / "empty_4x4.json"
    mark = {"kind": "digit", "cell": "r1c1", "digit": 0}
    empty.write_text(
        json.dumps({"size": 4, "box": [2, 2], "clues": [], "marks": [mark]})
    )

    # The hunt that runs through.
    out = tmp / "hits"
    result = run("--board", empty, "--out", out, "--seeds", f"0:{SEEDS}")
    assert result.returncode == 0, result.stderr
    examples = jsonl(out / "examples.jsonl")
    found = [e for e in jsonl(out / "progress.jsonl") if e["outcome"] == "example"]
    assert examples and len(found) == len(examples), (len(found), len(examples))

    finder = hunt.DoppelgangerRankFinder(board=str(empty), **hunt.DEFAULTS)
    for event, record in zip(found, examples, strict=True):
        clues = record["clues"]
        status, keep = brute.classify(clues)
        assert status == "unique" and keep == [grid(record)], (status, record)
        assert record["added"] == len(clues) and record["added"] >= 1, record
        target = finder.target(random.Random(event["seed"]), 30.0).first
        assert target == grid(record), (event["seed"], target, record)
        for clue in clues:
            rest = [c for c in clues if c is not clue]
            assert brute.classify(rest)[0] == "not_unique", (clue, record)
    assert any(grid(r)[0][0] != 0 for r in examples), "the mark held in every hit"

    counts, lines = split(out)
    assert counts["seeds"] == SEEDS and counts["found"] == len(examples), counts
    assert counts["infeasible"] == counts["timeout"] == counts["capped"] == 0, counts
    added = [int(m.group(1)) for line in lines if (m := re.match(r"hit, (\d+) ", line))]
    assert sorted(added) == added and len(added) == len(examples), added

    # verify refuses a planted bad record and passes its source.
    planted = tmp / "planted"
    result = run("--board", empty, "--out", planted, "--seeds", "0:1", "--no-verify")
    assert result.returncode == 0, result.stderr
    (record,) = jsonl(planted / "examples.jsonl")
    rows = list(record["solution"])
    rows[0] = rows[0][1] + rows[0][1:]  # r1c2's digit twice in r1
    broken_rule = {**record, "solution": rows}
    clue = record["clues"][0]
    wrong = {**clue, "rank": clue["rank"] % 16 + 1}
    broken_clue = {**record, "clues": [wrong, *record["clues"][1:]]}
    with (planted / "examples.jsonl").open("a") as f:
        for bad in (broken_rule, broken_clue):
            f.write(json.dumps(bad) + "\n")
    result = run("verify", planted)
    assert result.returncode == 0, result.stderr
    stamp, *verdicts = jsonl(planted / "verified.jsonl")
    assert [v["ok"] for v in verdicts] == [True, False, False], verdicts
    assert "holds" in verdicts[1]["reason"], verdicts[1]
    assert f"{clue['line']} from the {clue['end']} ranks" in verdicts[2]["reason"]
    _, lines = split(planted)
    assert "2 candidates rejected by `hunt.py verify`" in lines, lines
    assert any(line.startswith("hit, ") for line in lines), lines

    # The split on hunts that find nothing, each for its own reason.
    infeasible = tmp / "infeasible"
    board = HERE / "fixtures" / "infeasible_4x4.json"
    assert run("--board", board, "--out", infeasible, "--seeds", "0:2").returncode == 0
    counts, lines = split(infeasible)
    assert counts["infeasible"] == 2 and counts["found"] == 0, counts
    assert lines[0].startswith("none found in 2 seeds"), lines

    timeout = tmp / "timeout"
    result = run(
        "--board", empty, "--out", timeout, "--seeds", "0:2", "--time-limit", "0"
    )
    assert result.returncode == 0, result.stderr
    assert split(timeout)[0]["timeout"] == 2

    capped = tmp / "capped"
    result = run(
        "--board", empty, "--out", capped, "--seeds", "0:3", "--max-clues", "1"
    )
    assert result.returncode == 0, result.stderr
    counts, lines = split(capped)
    assert counts["capped"] == 3, counts
    assert sum(line.startswith("seed ") and "capped" in line for line in lines) == 3

    # A hunt killed partway resumes to the hits of the hunt that ran through.
    killed = tmp / "killed"
    argv = ("--board", empty, "--out", killed, "--seeds", f"0:{SEEDS}")
    proc = subprocess.Popen(command(*argv), env=success_env())
    progress = killed / "progress.jsonl"
    deadline = time.time() + 60
    while time.time() < deadline and proc.poll() is None:
        if progress.exists() and jsonl(progress):
            break
        time.sleep(0.01)
    proc.kill()
    proc.wait(timeout=10)
    done = len(jsonl(progress))
    assert 1 <= done < SEEDS, f"the kill left {done} of {SEEDS} seeds done"
    result = run(*argv)
    assert result.returncode == 0, result.stderr
    seeds = sorted(e["seed"] for e in jsonl(progress))
    assert seeds == list(range(SEEDS)), seeds
    assert jsonl(killed / "examples.jsonl") == examples

print("ok")
