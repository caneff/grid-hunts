"""hunt.py summary, on hand-written hunt directories built from the recorded
hit of `hit_fixture.py`, with no hunt run:

- a hunt whose seeds wrote verified examples reports each hit with its link
  and line table, and its wall clock from run.json's start to the end the
  hunt recorded in ended.json;
- a hunt whose seeds all ended Empty reports "none found" with the seeds,
  the wall clock and each seed's reason, and says it is no proof; with no
  recorded end (a hunt killed, or a copy that left it out) the wall clock is
  "not recorded", never read off a file's modification time;
- a directory with no hunt in it is refused by name.

    uv run finders/halver_lockout/test_cli.py
"""

import contextlib
import io
import json
import sys
import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

# isort: split
import hit_fixture
import hunt


def call(*argv):
    """(exit status, stdout, stderr) of hunt.py's main, in process."""
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        status = hunt.main(list(argv))
    return status, out.getvalue(), err.getvalue()


START = datetime(2026, 10, 19, 19, 51, 38, tzinfo=UTC)


def hunt_dir(path, records, outcomes, seconds=None):
    """A hunt directory as the driver leaves one: run.json, one seed_done
    event per outcome, and examples.jsonl; with `seconds`, the ended.json a
    hunt that returned writes that long after its start."""
    path.mkdir()
    argv = ["--out", str(path), "--seeds", f"0:{len(outcomes)}"]
    run = {"argv": argv, "start_time": START.isoformat()}
    (path / "run.json").write_text(json.dumps(run))
    if seconds is not None:
        end = START + timedelta(seconds=seconds)
        (path / hunt.halver_hunt.ENDED).write_text(json.dumps({"end": end.isoformat()}))
    (path / "progress.jsonl").write_text(
        "".join(json.dumps({"event": "seed_done", **e}) + "\n" for e in outcomes)
    )
    (path / "examples.jsonl").write_text("".join(json.dumps(r) + "\n" for r in records))


finder = hunt.HalverLockoutFinder(**hunt.DEFAULTS)
good = finder.record(hunt.Hit(hit_fixture.ADDED, hit_fixture.SOLUTION))

with tempfile.TemporaryDirectory() as tmp:
    tmp = Path(tmp)

    hits = tmp / "hits"
    hunt_dir(hits, [good], [{"seed": 0, "outcome": "example"}], seconds=958)
    status, text, err = call("summary", str(hits))
    assert status == 0, err
    assert text.startswith("1 hits in 1 seeds (0..0), wall clock 958 s\n"), text
    assert f"hit, 24 added lines: {hit_fixture.LINK}" in text, text
    assert f"  L1 | {hit_fixture.TABLE[0]}" in text, text

    none = tmp / "none"
    reasons = [
        "timeout: sampling a target (30s)",
        "budget: 40 lines added and still not unique",
    ]
    outcomes = [
        {"seed": i, "outcome": "empty", "empty_reason": r}
        for i, r in enumerate(reasons)
    ]
    hunt_dir(none, [], outcomes)
    status, text, err = call("summary", str(none))
    assert status == 0, err
    first, *rest = text.splitlines()
    assert first.startswith(
        "none found in 2 seeds (0..1), wall clock not recorded: "
    ), first
    assert first.endswith("not a proof that no finish exists"), first
    for i, reason in enumerate(reasons):
        assert f"seed {i}: {reason}" in rest, rest

    status, _, err = call("summary", str(tmp / "nothing"))
    assert status == 2, err
    assert "holds no hunt" in err, err

print("ok")
