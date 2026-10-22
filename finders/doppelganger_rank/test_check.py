"""The check command end to end (#67): a board file in, the status, the
solutions and each mark's verdict printed, judged against the 4x4 answer
key (`brute.py`), which takes no part in the check.

- The key holds 768 grids, and no two numbers of any of them are equal: a
  4x4 board's status can never rest on a tie. The infeasible board is the
  one that asks for one (two places both rank 1).
- On the unique, not-unique and infeasible 4x4 boards the check prints the
  key's status. Every solution it prints is a key grid that keeps the
  clues, the unique board's is the key's one grid, and its missing digits
  and ranks are the rule reader's.
- A mark is `held` exactly when every key grid of the board keeps it, and a
  `NOT HELD` mark names a key grid that breaks it. Exit 0 only when every
  mark held.
- The tie at 6x6: two places both rank 2 and a third ranked 4, which only a
  tie can give. 6x6 has no brute-force key, so the second model
  (`reprove.py`), written apart from the check's, is the key: both say
  `not_unique`. The check finds a solution, and the reader agrees with it.
- A mark whose solve gets no time is `timeout`, never `held`.
- An empty 6x6 and an empty 9x9 board are not unique, and each printed
  solution keeps every rule by the reader.
- A board given no time is a timeout and checks no mark. A board file the
  check cannot read is refused by name, exit 2, nothing on stdout.

    uv run finders/doppelganger_rank/test_check.py
"""

import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import brute
import rules
from check import read_board
from model import MarkCheck, RankModel
from printed import grid_of, solutions
from reprove import reprove

CHECK = HERE / "check.py"
FIXTURES = HERE / "fixtures"


def run(*args):
    return subprocess.run(
        [sys.executable, str(CHECK), *map(str, args)], capture_output=True, text=True
    )


def broken_by(line):
    """The grid on a `  broken by: r1 0231 r2 ...` line."""
    return grid_of(line.removeprefix("  broken by: "))


def keeps(grid, mark):
    reading = rules.read(grid, brute.BOX)
    if mark["kind"] == "digit":
        r, c = rules.parse_cell(mark["cell"])
        return grid[r][c] == mark["digit"]
    return reading.missing[mark["unit"]] == mark["digit"]


key = brute.grids()
assert len(key) == 768, len(key)
assert all(len(set(r.numbers.values())) == 16 for _, r in key)

for name, want in [
    ("unique_4x4", "unique"),
    ("not_unique_4x4", "not_unique"),
    ("infeasible_4x4", "infeasible"),
]:
    board = json.loads((FIXTURES / f"{name}.json").read_text())
    status, grids = brute.classify(board["clues"])
    assert status == want, (name, status)
    done = run(FIXTURES / f"{name}.json")
    out = done.stdout.splitlines()
    assert out[0] == f"2 rank clues: {status}", (name, done.stdout, done.stderr)
    if status == "infeasible":
        assert out[1:] == ["no mark checked: the board's status is infeasible"], out
        assert done.returncode == 1, (name, done.returncode)
        continue

    printed = solutions(out)
    assert len(printed) == (1 if status == "unique" else 2), (name, out)
    assert all(grid in grids for grid in printed), (name, printed)
    assert len(set(printed)) == len(printed), (name, printed)
    if status == "unique":
        assert printed == grids, (name, printed, grids)
    reading = rules.read(printed[0], brute.BOX)
    r1 = f"  r1 {reading.numbers['r1', 'left']}  misses {reading.missing['r1']}"
    r1 += f"  ranks {reading.ranks['r1', 'left']} from the left,"
    r1 += f" {reading.ranks['r1', 'right']} from the right"
    assert r1 in out, (name, r1, out)
    boxes = ", ".join(f"b{b} {reading.missing[f'b{b}']}" for b in range(1, 5))
    assert f"  boxes miss {boxes}" in out, (name, out)

    verdicts = [line for line in out if line[:4] in ("held", "NOT ", "TIME")]
    assert len(verdicts) == len(board["marks"]), (name, out)
    for mark, verdict in zip(board["marks"], verdicts, strict=True):
        if all(keeps(grid, mark) for grid in grids):
            assert verdict.startswith("held      "), (name, mark, verdict)
        else:
            assert verdict.startswith("NOT HELD  "), (name, mark, verdict)
            after = out[out.index(verdict) + 1]
            counter = broken_by(after)
            assert counter in grids and not keeps(counter, mark), (name, mark, after)
    held_all = all(v.startswith("held") for v in verdicts)
    assert done.returncode == (0 if held_all else 1), (name, done.returncode)

done = run(FIXTURES / "unique_4x4.json")
assert done.stdout.splitlines()[-5:] == [
    "held      r1c1 = 0",
    "held      r1 misses 4",
    "held      b4 misses 3",
    "NOT HELD  r4c4 = 1",
    "  broken by: r1 0231 r2 3420 r3 1304 r4 4012",
], done.stdout

done = run(FIXTURES / "tie_6x6.json", "--time-limit", "30")
out = done.stdout.splitlines()
assert done.returncode == 0, (done.returncode, done.stdout, done.stderr)
tie = json.loads((FIXTURES / "tie_6x6.json").read_text())
assert reprove(6, (2, 3), tie["clues"], 30.0).status == "not_unique"
assert out[0] == "3 rank clues: not_unique", out
grid = solutions(out)[0]
reading = rules.read(grid, (2, 3))
assert reading.violations == [], reading.violations
assert reading.numbers["r3", "left"] == reading.numbers["c4", "bottom"], reading
assert reading.ranks["r3", "left"] == 2 == reading.ranks["c4", "bottom"], reading
assert reading.ranks["c5", "top"] == 4, reading.ranks
assert 3 not in reading.ranks.values(), reading.ranks
ranks = [int(w) for line in out for w in re.findall(r"(\d+) from the", line)]
assert sorted(ranks[:24]) == sorted(reading.ranks.values()), ranks


n, box, opening, marks = read_board(FIXTURES / "opening_9x9.json")
rushed = RankModel(n, box, opening).mark_holds(marks[0], time_limit=1e-9)
assert rushed == MarkCheck("timeout"), rushed


def board_file(tmp, doc):
    path = Path(tmp) / "board.json"
    path.write_text(json.dumps(doc))
    return path


with tempfile.TemporaryDirectory() as tmp:
    for n, box in [(6, [2, 3]), (9, [3, 3])]:
        empty = {"size": n, "box": box, "clues": [], "marks": []}
        done = run(board_file(tmp, empty))
        out = done.stdout.splitlines()
        assert out[0] == "0 rank clues: not_unique", (n, done.stdout, done.stderr)
        printed = solutions(out)
        assert len(printed) == 2 and printed[0] != printed[1], (n, printed)
        for grid in printed:
            assert len(grid) == n and all(len(row) == n for row in grid), grid
            assert rules.read(grid, tuple(box)).violations == [], (n, grid)

done = run(FIXTURES / "unique_4x4.json", "--time-limit", "1e-6")
assert done.returncode == 1, (done.returncode, done.stdout, done.stderr)
assert done.stdout.splitlines() == [
    "2 rank clues: timeout",
    "no mark checked: the board's status is timeout",
], done.stdout

base = json.loads((FIXTURES / "unique_4x4.json").read_text())
clue = base["clues"][0]
for why, edit in [
    ("size 5 with (2, 2) boxes", {"size": 5}),
    ("size 6 with (3, 2) boxes", {"size": 6, "box": [3, 2]}),
    ("no place r5 left on a 4x4", {"clues": [{**clue, "line": "r5"}]}),
    ("no place r1 top on a 4x4", {"clues": [{**clue, "end": "top"}]}),
    ("two clues at r1 from the left", {"clues": [clue, clue]}),
    ("rank 17 outside 1..16", {"clues": [{**clue, "rank": 17}]}),
    (
        "mark r5c1 = 0 is off a 4x4 board",
        {"marks": [{**base["marks"][0], "cell": "r5c1"}]},
    ),
    ("mark r1c1 = 5 is off a 4x4 board", {"marks": [{**base["marks"][0], "digit": 5}]}),
    (
        "mark b5 misses 4 is off a 4x4 board",
        {"marks": [{**base["marks"][1], "unit": "b5"}]},
    ),
    (
        "mark r1 misses 0 is off a 4x4 board",
        {"marks": [{**base["marks"][1], "digit": 0}]},
    ),
    ("unknown mark kind 'given'", {"marks": [{"kind": "given"}]}),
]:
    doc = {**base, **edit}
    with tempfile.TemporaryDirectory() as tmp:
        path = board_file(tmp, doc)
        done = run(path)
    assert done.returncode == 2, (why, done.returncode, done.stdout, done.stderr)
    assert done.stdout == "", (why, done.stdout)
    assert f"check.py: {path}: " in done.stderr and why in done.stderr, (
        why,
        done.stderr,
    )

no_clues = {key: value for key, value in base.items() if key != "clues"}
with tempfile.TemporaryDirectory() as tmp:
    path = board_file(tmp, no_clues)
    done = run(path)
assert done.returncode == 2 and done.stdout == "", (done.returncode, done.stdout)
assert f"check.py: {path}: 'clues'" in done.stderr, done.stderr

missing = FIXTURES / "no_such_board.json"
done = run(missing)
assert done.returncode == 2 and done.stdout == "", (done.returncode, done.stdout)
assert f"check.py: {missing}: " in done.stderr and "No such file" in done.stderr, (
    done.stderr
)

print("test_check: ok")
