"""The hunt end to end at 4x4 (#69), judged against the answer key
(`brute.py`), which takes no part in the hunt:

- A hunt from an empty 4x4 board finds hits. Each hit's clues are `unique`
  by the key, its one grid is the hit's solution, and that solution is its
  seed's target. The board's mark is no constraint: some hit breaks it.
- No hit keeps a clue: the key finds every hit not unique without any one
  of its added clues.
- `verify` refuses a planted record whose grid breaks a rule, and one whose
  clue its grid does not keep, naming each; it passes the record they were
  planted from. It refuses one whose grid keeps every rule and clue but is
  not the board's only grid (a clue dropped), naming a second grid that
  the key holds, and refuses a hit as timed out, never unique, when the
  second model's re-proof gets no time.
- `summary` lists the hits, fewest added clues first, and splits the seeds
  into found, proven infeasible, timed out and capped, the capped count
  labelled as no proof, on a hunt of each.
- The ranked pick (`--pool 16`) adds the most restricting clue, and its
  hits are unique and minimal by the key too.
- A solve that times out ends its seed `timeout:` in the add loop and in
  the minimiser, and `capped:` when the seed's `--max-seconds` is what ran
  out; none is read as unique.
- The minimiser on two CP-SAT workers (`--proof-workers 2`) gives the
  same hits, a finished hunt resumes under another `--proof-workers`, and
  `--proof-workers 0` and `--workers 2` are refused.
- A board file the hunt cannot read is refused by name, exit 2, and a hunt
  does not resume on a board of another size.
- A later `verify` that rejects a hit the hunt verified as it ran
  overrules it: `summary` counts it rejected and `links` skips it.
  `summary` refuses a seed that ended for a reason it does not know.
- A hunt killed partway resumes to the same hits as the hunt that ran
  through.

    uv run finders/doppelganger_rank/test_hunt.py
"""

import json
import random
import re
import shutil
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
from cli_checks import read_jsonl, run_cli
from model import RankModel, RuleCheck
from printed import grid_of
from subprocess_env import success_env

SCRIPT = HERE / "hunt.py"
SEEDS = 20
SPLIT = re.compile(
    r"(\d+) seeds .*: found (\d+), duplicate (\d+), proven infeasible (\d+), "
    r"timed out (\d+), capped (\d+) \(a budget ran out: no proof\), "
    r"no separating clue (\d+), rejected (\d+)"
)


def run(*args):
    return run_cli(SCRIPT, *args)


def finder_with(board, **knobs):
    return hunt.DoppelgangerRankFinder(board=board, **{**hunt.DEFAULTS, **knobs})


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


def assert_key_hits(out, board):
    """Every hit in `out` is unique by the key, its one grid its seed's
    target, and minimal: not unique without any one of its clues."""
    examples = read_jsonl(out / "examples.jsonl")
    found = [e for e in read_jsonl(out / "progress.jsonl") if e["outcome"] == "example"]
    assert examples and len(found) == len(examples), (len(found), len(examples))
    finder = finder_with(str(board))
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
    return found, examples


def timed_out(finder, when):
    """`finder.propose` on seed 0 with every check `when(kwargs)` picks a
    timeout and the rest solved as usual."""
    real = RankModel.check

    def check(self, **kwargs):
        if when(kwargs):
            return RuleCheck("timeout")
        return real(self, **kwargs)

    RankModel.check = check
    try:
        return finder.propose(random.Random(0))
    finally:
        RankModel.check = real


# The ranked pick (#79) on a planted pool: c2 from the top keeps its target
# rank in one sampled grid, r1 from the left in three and r2 from the left in
# two, so c2 from the top is the most restricting clue on every seed's rng.
rare, common, middle = ("c2", "top"), ("r1", "left"), ("r2", "left")
target_ranks = {rare: 5, common: 1, middle: 9}
pool = [
    {rare: 5, common: 1, middle: 9},
    {rare: 6, common: 1, middle: 9},
    {rare: 7, common: 1, middle: 2},
]
for seed in range(20):
    rng = random.Random(seed)
    place = hunt.most_restricting([common, middle, rare], target_ranks, pool, rng)
    assert place == rare, (seed, place)
# Ties break by the seed's rng: with no sample every place ties.
picked = {
    hunt.most_restricting([common, middle, rare], target_ranks, [], random.Random(s))
    for s in range(20)
}
assert picked == {common, middle, rare}, picked


with tempfile.TemporaryDirectory() as tmp:
    tmp = Path(tmp)
    empty = tmp / "empty_4x4.json"
    mark = {"kind": "digit", "cell": "r1c1", "digit": 0}
    empty.write_text(
        json.dumps({"size": 4, "box": [2, 2], "clues": [], "marks": [mark]})
    )

    # The hunt adds each clue by the ranked pick, from a sample of the board.
    picks = []
    ranked = hunt.most_restricting

    def spy(places, target, sample, rng):
        place = ranked(places, target, sample, rng)
        picks.append((place, len(sample)))
        # The sample keeps only grids every clue added so far holds in.
        for earlier, _ in picks[:-1]:
            assert all(grid[earlier] == target[earlier] for grid in sample), picks
        return place

    hunt.most_restricting = spy
    hit = finder_with(str(empty), pool=16).propose(random.Random(0))
    hunt.most_restricting = ranked
    assert isinstance(hit, hunt.Hit), hit
    assert picks and picks[0][1] >= hunt.DEFAULTS["pool_floor"], picks

    # The ranked pick's hits, by the key.
    ranked_out = tmp / "ranked"
    result = run("--board", empty, "--out", ranked_out, "--seeds", "0:3", "--pool", 16)
    assert result.returncode == 0, result.stderr
    assert_key_hits(ranked_out, empty)

    # A timed-out solve is never unique: in the add loop, in the minimiser,
    # and capped when the seed's own budget is what ran out.
    loop = timed_out(finder_with(str(empty)), lambda kw: "workers" not in kw)
    assert loop == hunt.Empty("timeout: the check after 0 clues (30 s)"), loop
    budget = timed_out(finder_with(str(empty), max_seconds=5.0), lambda kw: True)
    assert budget.reason.startswith("capped: 5 s ran out during the check"), budget
    minimiser = timed_out(finder_with(str(empty)), lambda kw: "workers" in kw)
    assert minimiser == hunt.Empty("timeout: the minimiser (30 s)"), minimiser

    # The hunt that runs through.
    out = tmp / "hits"
    result = run("--board", empty, "--out", out, "--seeds", f"0:{SEEDS}")
    assert result.returncode == 0, result.stderr
    found, examples = assert_key_hits(out, empty)
    assert any(grid(r)[0][0] != 0 for r in examples), "the mark held in every hit"

    # The minimiser's proofs on two workers keep every verdict, so the hits.
    wide = tmp / "wide"
    result = run(
        "--board", empty, "--out", wide, "--seeds", "0:5", "--proof-workers", 2
    )
    assert result.returncode == 0, result.stderr
    first = [r for e, r in zip(found, examples, strict=True) if e["seed"] < 5]
    assert read_jsonl(wide / "examples.jsonl") == first
    result = run("--board", empty, "--out", wide, "--seeds", "0:5")
    assert result.returncode == 0, result.stderr
    assert read_jsonl(wide / "examples.jsonl") == first
    for flag in (("--proof-workers", 0), ("--workers", 2)):
        result = run("--board", empty, "--out", tmp / "none", "--seeds", "0:1", *flag)
        assert result.returncode == 2 and f"{flag[0]} {flag[1]}" in result.stderr
        assert not (tmp / "none").exists(), flag

    # A board the hunt cannot read, and a resume on a board of another size.
    bad = tmp / "bad.json"
    rank = {"line": "r1", "end": "left", "rank": 40}
    bad.write_text(json.dumps({"size": 4, "box": [2, 2], "clues": [rank]}))
    result = run("--board", bad, "--out", tmp / "bad", "--seeds", "0:1")
    assert result.returncode == 2 and "rank 40" in result.stderr, result
    grown = tmp / "grown.json"
    grown.write_text(empty.read_text())
    resized = tmp / "resized"
    assert run("--board", grown, "--out", resized, "--seeds", "0:1").returncode == 0
    grown.write_text(json.dumps({"size": 6, "box": [2, 3], "clues": [], "marks": []}))
    progress = (resized / "progress.jsonl").read_text()
    result = run("--board", grown, "--out", resized, "--seeds", "0:1")
    assert result.returncode == 2 and "config differs" in result.stderr, result
    assert (resized / "progress.jsonl").read_text() == progress

    counts, lines = split(out)
    assert counts["seeds"] == SEEDS and counts["found"] == len(examples), counts
    assert counts["infeasible"] == counts["timeout"] == counts["capped"] == 0, counts
    added = [int(m.group(1)) for line in lines if (m := re.match(r"hit, (\d+) ", line))]
    assert sorted(added) == added and len(added) == len(examples), added

    # verify refuses a planted bad record and passes its source.
    planted = tmp / "planted"
    result = run("--board", empty, "--out", planted, "--seeds", "0:1", "--no-verify")
    assert result.returncode == 0, result.stderr
    (record,) = read_jsonl(planted / "examples.jsonl")
    rows = list(record["solution"])
    rows[0] = rows[0][1] + rows[0][1:]  # r1c2's digit twice in r1
    broken_rule = {**record, "solution": rows}
    clue = record["clues"][0]
    wrong = {**clue, "rank": clue["rank"] % 16 + 1}
    broken_clue = {**record, "clues": [wrong, *record["clues"][1:]]}
    loose = {**record, "clues": record["clues"][1:]}
    with (planted / "examples.jsonl").open("a") as f:
        for bad in (broken_rule, broken_clue, loose):
            f.write(json.dumps(bad) + "\n")
    result = run("verify", planted)
    assert result.returncode == 0, result.stderr
    stamp, *verdicts = read_jsonl(planted / "verified.jsonl")
    assert [v["ok"] for v in verdicts] == [True, False, False, False], verdicts
    assert "holds" in verdicts[1]["reason"], verdicts[1]
    assert f"{clue['line']} from the {clue['end']} ranks" in verdicts[2]["reason"]
    reason = verdicts[3]["reason"]
    assert reason.startswith("not unique: a second grid "), reason
    second = grid_of(reason.removeprefix("not unique: a second grid "))
    _, keep = brute.classify(loose["clues"])
    assert second in keep and second != grid(record), (second, record)
    _, lines = split(planted)
    assert "3 candidates rejected by `hunt.py verify`" in lines, lines

    rushed = finder_with(None, time_limit=1e-9)
    verdict = rushed.verify(rushed.candidate_from_record(record))
    assert verdict == (False, "timeout: the re-proof reached 1e-09 s"), verdict
    assert any(line.startswith("hit, ") for line in lines), lines

    # A later verify overrules the hunt's own: a hit with a clue dropped.
    reverified = tmp / "reverified"
    shutil.copytree(out, reverified)
    records = read_jsonl(reverified / "examples.jsonl")
    records[0] = {**records[0], "clues": records[0]["clues"][1:]}
    (reverified / "examples.jsonl").write_text(
        "".join(json.dumps(r) + "\n" for r in records)
    )
    assert run("verify", reverified).returncode == 0
    _, lines = split(reverified)
    assert "1 candidates rejected by `hunt.py verify`" in lines, lines
    result = run("links", reverified)
    assert result.returncode == 0, result.stderr
    assert "1 candidates skipped" in result.stdout, result.stdout
    assert len(list((reverified / "links").iterdir())) == len(records) - 1

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
    with (capped / "progress.jsonl").open("a") as f:
        odd = {"event": "seed_done", "seed": 3, "outcome": "empty"}
        f.write(json.dumps({**odd, "empty_reason": "stalled: no class"}) + "\n")
    result = run("summary", capped)
    assert result.returncode == 2 and "no known reason" in result.stderr, result

    # A hunt killed partway resumes to the hits of the hunt that ran through.
    killed = tmp / "killed"
    argv = ("--board", empty, "--out", killed, "--seeds", f"0:{SEEDS}")
    command = [sys.executable, str(SCRIPT), *map(str, argv)]
    proc = subprocess.Popen(command, env=success_env())
    progress = killed / "progress.jsonl"
    deadline = time.time() + 60
    while time.time() < deadline and proc.poll() is None:
        if progress.exists() and read_jsonl(progress):
            break
        time.sleep(0.01)
    proc.kill()
    proc.wait(timeout=10)
    done = len(read_jsonl(progress))
    assert 1 <= done < SEEDS, f"the kill left {done} of {SEEDS} seeds done"
    result = run(*argv)
    assert result.returncode == 0, result.stderr
    seeds = sorted(e["seed"] for e in read_jsonl(progress))
    assert seeds == list(range(SEEDS)), seeds
    assert read_jsonl(killed / "examples.jsonl") == examples

print("ok")
