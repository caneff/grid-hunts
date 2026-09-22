"""The checker reads the opener the way OPENER_NOTES.md says, and its count
loop reports what the model holds.

Expected clue positions and values below are the notes' table, read by hand
from the link: circled marks are clues, uncircled marks and entered digits
are hypotheses. The count loop is exercised on a model with every cell fixed
to one grid, where the only honest answer is one solution, ranked as the
oracle ranks it. Workers pinned to 1.

    uv run finders/qqrr/test_checker.py
"""

import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import checker
import model
import oracle
from grids import random_sudoku

from examples._shared import cpsat

HERE = Path(__file__).resolve().parent
op = checker.load_opener(HERE / "opener.json")

assert op.n == 9
assert op.window_clues == {(5, 5): (10, 10), (1, 4): (51, 56), (3, 3): (58, 64)}
assert op.cell_clues == {(0, 4): 33}
assert op.window_hypotheses == {(2, 1): (9, 9), (3, 0): (8, 8), (2, 0): (1, 1)}
assert op.digit_hypotheses[(0, 3)] == 7
assert op.digit_hypotheses[(8, 0)] == 8
assert len(op.digit_hypotheses) == 13
assert checker.CORNERS == {"tl": (0, 0), "tr": (0, 8), "bl": (8, 0), "br": (8, 8)}

# The bands parse as the notes say: exact, inclusive range, open-ended.
assert checker.parse_band("10", 64) == (10, 10)
assert checker.parse_band("51-56", 64) == (51, 56)
assert checker.parse_band("58+", 64) == (58, 64)


grid = random_sudoku(random.Random(7))
ranks, numbers, cranks = oracle.rank_grid(grid)
# A run whose clues are read off the grid itself: the one clue set that is
# certainly consistent. Fixing every digit makes the answer unique.
fixed = checker.Opener(
    n=9,
    window_clues={(6, 6): (ranks[6][6], ranks[6][6])},
    cell_clues={(0, 4): cranks[0][4]},
    window_hypotheses={},
    digit_hypotheses={(r, c): grid[r][c] for r in range(9) for c in range(9)},
)
report = checker.run(
    fixed, corner=None, hypotheses=True, count=2, workers=1, timeout=30
)
assert report.status == "unique", report.status
assert report.solutions[0].grid == grid
# The tables on a Solution are the oracle's; that they equal the model's is
# asserted inside run, and the stub-solver case below witnesses that assert.

# With the corner pinned to a rank the grid does not have, nothing satisfies.
wrong = cranks[0][0] % 81 + 1
fixed_wrong = checker.Opener(9, {}, {(0, 0): wrong}, {}, fixed.digit_hypotheses)
report = checker.run(
    fixed_wrong, corner=None, hypotheses=True, count=2, workers=1, timeout=30
)
assert report.status == "infeasible", report.status

# A spent budget is a timeout, never a verdict.
report = checker.run(fixed, corner=None, hypotheses=True, count=2, workers=1, timeout=0)
assert report.status == "timeout", report.status
assert report.solutions == []

# The verdict line and the solution block.
text = checker.render(
    checker.run(fixed, corner=None, hypotheses=True, count=2, workers=1, timeout=30)
)
assert text.startswith("unique:"), text
block = checker.render_solution(checker.Solution(grid, ranks, numbers, cranks), 1)
assert "window ranks" in block and "cell numbers" in block and "cell ranks" in block


def refuses(fn, *args, saying="", **kwargs):
    """True when the call raises the guard's own error, with `saying` in its message."""
    try:
        fn(*args, **kwargs)
    except (ValueError, AssertionError) as e:
        return saying in str(e)
    return False


# Bad inputs are refused, not scored: a count or worker count below 1, and a
# corner pin on a cell that already carries a different QQRR clue.
assert refuses(
    checker.run,
    fixed,
    corner=None,
    hypotheses=True,
    count=0,
    workers=1,
    timeout=30,
    saying="count",
)
assert refuses(
    checker.run,
    fixed,
    corner=None,
    hypotheses=True,
    count=2,
    workers=0,
    timeout=30,
    saying="workers",
)
clued_corner = checker.Opener(9, {}, {(0, 0): 40}, {}, {})
assert refuses(
    checker.run,
    clued_corner,
    corner="tl",
    hypotheses=False,
    count=2,
    workers=1,
    timeout=30,
    saying="already carries",
)
# The same rank on both is no contradiction.
same = checker.Opener(9, {}, {(0, 0): checker.CORNER_RANK}, {}, fixed.digit_hypotheses)
assert checker.run(
    same, corner="tl", hypotheses=True, count=1, workers=1, timeout=30
).status in (
    "infeasible",
    "multiple",
)

# A mark outside 1..64, a cage outside 1..81, or a two-cell cage fails the load.
doc = json.loads((HERE / "opener.json").read_text())


def variant(mutate, saying=""):
    d = json.loads(json.dumps(doc))
    mutate(d["puzzle"])
    path = HERE / ".variant.json"
    path.write_text(json.dumps(d))
    try:
        return refuses(checker.load_opener, path, saying=saying)
    finally:
        path.unlink()


def named(p, name):
    return next(c for c in p["constraints"] if c.get("name") == name)


assert variant(
    lambda p: named(p, checker.WINDOW_MARKS)["params"][0].__setitem__("text", "70"),
    "outside 1..64",
)
assert variant(
    lambda p: named(p, checker.CELL_CAGES)["cages"][0].__setitem__("value", "300"),
    "outside 1..81",
)
assert variant(
    lambda p: named(p, checker.CELL_CAGES)["cages"][0].__setitem__("cells", [4, 5]),
    "one cell",
)
# A mark on a border intersection (x=0 or y=0) has no window around it: the
# offset (y-1, x-1) would be negative, silently pointing at the wrong window.
assert variant(
    lambda p: named(p, checker.WINDOW_MARKS)["symbols"][0].__setitem__(0, 0),
    "border intersection",
)
assert variant(
    lambda p: named(p, checker.WINDOW_MARKS)["symbols"][0].__setitem__(1, 0),
    "border intersection",
)
assert not variant(lambda p: None)


# The oracle check inside run is live: a solver whose readings disagree with
# the oracle is refused, not reported.
class Stub:
    def __init__(self, s, bad):
        self.s, self.bad = s, bad

    def Value(self, v):
        val = self.s.Value(v)
        return val + 1 if v.Name() == self.bad else val


qm = model.build(9, ranked_cells=[(0, 4)])
for r in range(9):
    for c in range(9):
        qm.m.Add(qm.x[r][c] == grid[r][c])
solver = cpsat.solver(30)
assert solver.Solve(qm.m) in cpsat.SOLVED
assert checker._extract(solver, qm, [(0, 4)]).grid == grid
for bad in ("rank00", "num44", "q04"):
    assert refuses(checker._extract, Stub(solver, bad), qm, [(0, 4)]), bad

print("ok test_checker")
