"""hunt.py's own commands, on hand-written hunt directories built from the
recorded hit of `hit_fixture.py`, with no hunt run:

- `summary` calls an example a hit only when `verify` passed it: inline in a
  hunt without `--no-verify`, or in `hunt.py verify`'s verified.jsonl after
  one with it. Until that verify runs, a `--no-verify` hunt's examples are
  unchecked candidates, never hits; one it rejects is reported with its
  reason. A verified.jsonl that does not cover the examples is refused.
- A rejected seed with no reason says so, not a bare comma.
- `--workers` other than 1 is refused by name before any hunt starts.

    uv run finders/halver_between/test_cli.py
"""

import contextlib
import io
import json
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

# isort: split
import hit_fixture
import hunt
import rules


def call(*argv):
    """(exit status, stdout, stderr) of hunt.py's main, in process."""
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        status = hunt.main(list(argv))
    return status, out.getvalue(), err.getvalue()


def hunt_dir(path, argv, records, outcomes):
    """A hunt directory as the driver leaves one: run.json, one seed_done
    event per outcome, and examples.jsonl."""
    path.mkdir()
    run = {"argv": argv, "start_time": datetime.now(UTC).isoformat()}
    (path / "run.json").write_text(json.dumps(run))
    (path / "progress.jsonl").write_text(
        "".join(json.dumps({"event": "seed_done", **e}) + "\n" for e in outcomes)
    )
    (path / "examples.jsonl").write_text("".join(json.dumps(r) + "\n" for r in records))


finder = hunt.HalverBetweenFinder(
    max_cells=8,
    pool=20,
    time_limit=30.0,
    max_lines=40,
    max_seconds=120.0,
    verify_seconds=600.0,
)
solution = rules.RuleModel(hunt.BOARD + list(hit_fixture.ADDED)).check(60).first
good = finder.record(hunt.Hit(hit_fixture.ADDED, solution))
# The same hit with one more line whose body cell r5c2 is already on a line.
reused = rules.Line((4, 0), ((4, 1),), (3, 1))
bad = finder.record(hunt.Hit((*hit_fixture.ADDED, reused), solution))
examples = [{"seed": 0, "outcome": "example"}, {"seed": 1, "outcome": "example"}]

with tempfile.TemporaryDirectory() as tmp:
    tmp = Path(tmp)

    # Verified inline: both examples are hits.
    inline = tmp / "inline"
    hunt_dir(inline, ["--out", str(inline), "--seeds", "0:2"], [good, good], examples)
    status, text, err = call("summary", str(inline))
    assert status == 0, err
    assert text.startswith("2 hits in 2 seeds (0..1), wall clock"), text
    assert f"hit, 11 added lines: {hit_fixture.LINK}" in text, text

    # --no-verify, before `hunt.py verify`: unchecked, no hit.
    deferred = tmp / "deferred"
    argv = ["--out", str(deferred), "--seeds", "0:2", "--no-verify"]
    hunt_dir(deferred, argv, [good, bad], examples)
    status, text, err = call("summary", str(deferred))
    assert status == 0, err
    lines = text.splitlines()
    assert lines[0].startswith("no verified hit in 2 seeds (0..1)"), text
    assert lines[1].startswith("2 candidates unchecked: the hunt ran with"), text
    assert "\nhit," not in text, text
    assert f"unchecked candidate, 11 added lines: {hit_fixture.LINK}" in text, text

    # After `hunt.py verify`: the good one is a hit, the bad one rejected.
    status, _, err = call("verify", str(deferred))
    assert status == 0, err
    status, text, err = call("summary", str(deferred))
    assert status == 0, err
    lines = text.splitlines()
    assert lines[0].startswith("1 hits in 2 seeds (0..1)"), text
    assert lines[1] == "1 candidates rejected by `hunt.py verify`", text
    assert f"hit, 11 added lines: {hit_fixture.LINK}" in text, text
    assert (
        "rejected candidate, 12 added lines: r5c1 | r5c2 | r4c2: "
        "body cell r5c2 is already on a line"
    ) in text, text
    assert "unchecked" not in text, text

    # A verified.jsonl that no longer covers examples.jsonl is refused.
    with (deferred / "examples.jsonl").open("a") as f:
        f.write(json.dumps(good) + "\n")
    status, text, err = call("summary", str(deferred))
    assert status == 2, (status, text)
    assert "covers 2 examples and examples.jsonl holds 3" in err, err

    # A rejected seed with no reason recorded says so.
    rejected = tmp / "rejected"
    argv = ["--out", str(rejected), "--seeds", "0:1"]
    hunt_dir(rejected, argv, [], [{"seed": 0, "outcome": "rejected"}])
    status, text, err = call("summary", str(rejected))
    assert status == 0, err
    assert "seed 0: rejected, no reason given" in text, text

    # --workers 3 is refused by name, and no hunt directory is made.
    refused = tmp / "refused"
    status, text, err = call("--out", str(refused), "--seeds", "0:1", "--workers", "3")
    assert status == 2, (status, text)
    assert "refusing to run -- --workers 3: every seed runs on one" in err, err
    assert not refused.exists()

print("ok")
