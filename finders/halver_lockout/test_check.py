"""The check command on the 9x9 fixtures: the status of a lockout board's
lines, then each mark as held, NOT HELD (with a solution that breaks it) or
TIMEOUT, and exit 0 only when every mark held.

- The unique fixture with five marks its one answer keeps: all held, exit 0.
  A false mark on it: NOT HELD, with the answer as the solution that breaks
  it, exit 1.
- The not-unique fixture with no marks: its status, exit 0; with a mark one
  of its solutions breaks, NOT HELD, exit 1.
- The infeasible fixture, and any board given no time: no mark checked,
  exit 1 with the reason. A timeout is never read as unique or as held.
- A board file with no type-407 lines (halver_between's board, whose lines
  are type 403) is refused by name, exit 2.

    uv run finders/halver_lockout/test_check.py
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
CHECK = HERE / "check.py"
FIXTURES = HERE / "fixtures"
UNIQUE = FIXTURES / "unique.json"


def run(*args):
    return subprocess.run(
        [sys.executable, str(CHECK), *map(str, args)], capture_output=True, text=True
    )


done = run(UNIQUE, "--marks", FIXTURES / "unique_marks.json")
assert done.returncode == 0, (done.returncode, done.stdout, done.stderr)
assert done.stdout.splitlines() == [
    "L1-L23: unique",
    "held      r1c3 = 8",
    "held      r2c1 in {7,9}",
    "held      r1c1 is a halver",
    "held      a halver 4 in r2c5 or r2c6",
    "held      8 in r9c1 or r9c2",
], done.stdout

with tempfile.TemporaryDirectory() as tmp:
    wrong = Path(tmp) / "marks.json"
    wrong.write_text(json.dumps([{"kind": "digit", "cell": "r1c1", "digit": 2}]))
    done = run(UNIQUE, "--marks", wrong)
    assert done.returncode == 1, (done.returncode, done.stdout, done.stderr)
    assert done.stdout.splitlines() == [
        "L1-L23: unique",
        "NOT HELD  r1c1 = 2",
        "  broken by: r1 518369247 r2 729514638 r3 634278951 r4 941826573"
        " r5 873945126 r6 265137894 r7 456782319 r8 397651482 r9 182493765;"
        " halvers r1c1 r2c6 r3c9 r4c4 r5c8 r6c2 r7c7 r8c3 r9c5",
    ], done.stdout

    done = run(FIXTURES / "not_unique.json")
    assert done.returncode == 0, (done.returncode, done.stdout, done.stderr)
    assert done.stdout.splitlines() == ["L1-L3: not_unique"], done.stdout

    other = Path(tmp) / "other.json"
    other.write_text(json.dumps([{"kind": "digit", "cell": "r1c1", "digit": 5}]))
    done = run(FIXTURES / "not_unique.json", "--marks", other)
    assert done.returncode == 1, (done.returncode, done.stdout, done.stderr)
    out = done.stdout.splitlines()
    assert out[:2] == ["L1-L3: not_unique", "NOT HELD  r1c1 = 5"], out
    assert out[2].startswith("  broken by: r1 ") and len(out) == 3, out

done = run(FIXTURES / "infeasible.json", "--marks", FIXTURES / "unique_marks.json")
assert done.returncode == 1, (done.returncode, done.stdout, done.stderr)
assert done.stdout.splitlines() == [
    "L1-L6: infeasible",
    "no mark checked: the board's status is infeasible",
], done.stdout

done = run(UNIQUE, "--marks", FIXTURES / "unique_marks.json", "--time-limit", "1e-6")
assert done.returncode == 1, (done.returncode, done.stdout, done.stderr)
assert done.stdout.splitlines() == [
    "L1-L23: timeout",
    "no mark checked: the board's status is timeout",
], done.stdout

between = HERE.parent / "halver_between" / "board.json"
done = run(between)
assert done.returncode == 2, (done.returncode, done.stdout, done.stderr)
assert done.stdout == "", done.stdout
assert f"{between}: no lockout lines (constraint type 407)" in done.stderr, done.stderr

print("ok")
