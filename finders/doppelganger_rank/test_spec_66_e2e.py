"""Spec #66 end to end, in the gate, through the commands, on one recorded
9x9 hit (`fixtures/hit_9x9.json`, seed 72 of the hunt of record, #72: the
fewest added clues, 11, of its 16 hits):

- `check.py` on Chris's four opening clues plus the hit's 11, with his five
  marks: `unique`, the one printed solution is the hit's, and every mark
  `held`, exit 0.
- `hunt.py verify` on a hunt directory holding the hit passes it: the rule
  reader finds every rule and clue kept, and the second model re-proves it
  unique. `summary` lists it as the one verified hit, and `links` writes
  a short link (minted offline) whose document has the solution entered in
  the grid, the digits from 0 and the rank clues as 0.5-size text.
- The hit with its last added clue dropped: `verify` refuses it, naming a
  second grid that keeps every rule and every other clue, `summary`
  counts it rejected and `links` writes it no link. Given no time, `verify`
  refuses the hit as timed out, never unique.

What this seam is blind to. Seam: `just check`. Blind to: the slow 9x9
hunt test (`test_hunt_9x9.py`, `just test-slow`), so to whether the hunt
still finds a 9x9 hit, and to how the hit reads as a puzzle in the live
app.

    uv run finders/doppelganger_rank/test_spec_66_e2e.py
"""

import json
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "hunt"))

# isort: split
import links
import rules
import short_link
from cli_checks import read_jsonl, run_cli
from printed import grid_of, solutions

HUNT, CHECK = HERE / "hunt.py", HERE / "check.py"
fixture = json.loads((HERE / "fixtures" / "hit_9x9.json").read_text())
record = fixture["record"]
opening = json.loads((HERE / "fixtures" / "opening_9x9.json").read_text())
n, box = record["size"], tuple(record["box"])
solution = tuple(tuple(map(int, row)) for row in record["solution"])
assert record["clues"][:4] == opening["clues"] and record["added"] == 11, record


def hunt_dir(out, records):
    out.mkdir()
    argv = ["--out", str(out), "--seeds", f"72:{72 + len(records)}"]
    (out / "run.json").write_text(json.dumps({"argv": argv, "config": {}}))
    events = [
        {"event": "seed_done", "seed": 72 + k, "outcome": "example"}
        for k in range(len(records))
    ]
    for name, rows in (("progress", events), ("examples", records)):
        (out / f"{name}.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))


with short_link.fake_mint() as fake, tempfile.TemporaryDirectory() as tmp:
    tmp = Path(tmp)

    board = tmp / "board.json"
    board.write_text(json.dumps({**opening, "clues": record["clues"]}))
    done = run_cli(CHECK, board, "--time-limit", 60)
    out = done.stdout.splitlines()
    assert done.returncode == 0, (done.stdout, done.stderr)
    assert out[0] == "15 rank clues: unique", out
    assert solutions(out) == [solution], out
    verdicts = [line for line in out if line[:4] in ("held", "NOT ", "TIME")]
    assert len(verdicts) == 5 and all(v.startswith("held") for v in verdicts), out

    hits = tmp / "hit"
    hunt_dir(hits, [record])
    assert run_cli(HUNT, "verify", hits).returncode == 0
    stamp, verdict = read_jsonl(hits / "verified.jsonl")
    assert verdict["ok"], verdict
    lines = run_cli(HUNT, "summary", hits).stdout.splitlines()
    assert lines[0] == "1 verified hits in 1 seeds (72..72)", lines
    assert lines[2].startswith("hit, 11 added clues: "), lines
    assert run_cli(HUNT, "links", hits).returncode == 0
    doc = short_link.fake_doc(fake, (hits / "links" / "72.txt").read_text().strip())
    assert doc == links.link_doc(record), doc
    cells = doc["puzzle"]["cells"]
    assert doc["puzzle"]["minDigit"] == 0 and doc["puzzle"]["maxDigit"] == n
    (text,) = [c for c in doc["puzzle"]["constraints"] if c.get("type") == 2002]
    assert {p["size"] for p in text["params"]} == {0.5}, text["params"]
    side = n + 4
    for r, row in enumerate(solution):
        for c, digit in enumerate(row):
            assert cells[r * side + c] == {"value": digit}, (r, c, cells[r * side + c])

    loose = {**record, "clues": record["clues"][:-1], "added": 10}
    refused = tmp / "loose"
    hunt_dir(refused, [loose])
    assert run_cli(HUNT, "verify", refused).returncode == 0
    stamp, verdict = read_jsonl(refused / "verified.jsonl")
    assert verdict["reason"].startswith("not unique: a second grid "), verdict
    second = grid_of(verdict["reason"].removeprefix("not unique: a second grid "))
    other = rules.read(second, box)
    assert second != solution and not other.violations, second
    assert not other.broken_clues(loose["clues"]), other.broken_clues(loose["clues"])
    lines = run_cli(HUNT, "summary", refused).stdout.splitlines()
    assert "1 candidates rejected by `hunt.py verify`" in lines, lines
    done = run_cli(HUNT, "links", refused)
    assert "wrote 0 links" in done.stdout and "1 candidates skipped" in done.stdout

    rushed = tmp / "rushed"
    hunt_dir(rushed, [record])
    assert run_cli(HUNT, "verify", rushed, "--time-limit", 1e-9).returncode == 0
    stamp, verdict = read_jsonl(rushed / "verified.jsonl")
    assert verdict["reason"] == "timeout: the re-proof reached 1e-09 s", verdict

print("ok")
