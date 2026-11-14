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

import checker
import model
import oracle
from grids import TIE_WITNESS, random_sudoku
from sudoku_kit import cpsat

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
# Each table is printed under its heading with the oracle's values, one grid
# row per line: the first row of every table, read back off the block.
lines = block.splitlines()


def first_row_under(heading):
    return lines[lines.index(heading) + 1].split()


assert lines[1].split() == [str(d) for d in grid[0]], lines[1]
assert first_row_under("window ranks (by top-left cell)") == [
    str(v) for v in ranks[0]
], block
assert first_row_under("cell numbers") == [str(v) for v in numbers[0]], block
assert first_row_under("cell ranks") == [str(v) for v in cranks[0]], block


def refuses(fn, *args, error, saying, **kwargs):
    """True when the call raises exactly `error` (the guard's own, not a crash
    of another type) with `saying` in its message; `saying` is required, and
    an empty one would pass on any message."""
    assert saying, "name the message the refusal must carry"
    try:
        fn(*args, **kwargs)
    except Exception as e:
        return type(e) is error and saying in str(e)
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
    error=ValueError,
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
    error=ValueError,
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
    error=ValueError,
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


def variant(mutate, saying):
    d = json.loads(json.dumps(doc))
    mutate(d["puzzle"])
    path = HERE / ".variant.json"
    path.write_text(json.dumps(d))
    try:
        return refuses(checker.load_opener, path, error=ValueError, saying=saying)
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
assert not variant(lambda p: None, "no refusal")


# The oracle check inside run is live: a solver whose readings disagree with
# the oracle is refused, not reported.
class Skewed:
    """A solver whose reading of the variable named `bad` is one too high."""

    def __init__(self, s, bad):
        self.s, self.bad = s, bad

    def Value(self, v):
        val = self.s.Value(v)
        return val + 1 if v.Name() == self.bad else val

    def __getattr__(self, name):
        return getattr(self.s, name)


def run_skewed(bad):
    """`run` over the fixed grid with the solver `run` builds skewed on `bad`."""
    real_solver = cpsat.solver
    cpsat.solver = lambda *a, **kw: Skewed(real_solver(*a, **kw), bad)
    try:
        return refuses(
            checker.run,
            fixed,
            corner=None,
            hypotheses=True,
            count=1,
            workers=1,
            timeout=30,
            error=AssertionError,
            saying=saying_for[bad],
        )
    finally:
        cpsat.solver = real_solver


saying_for = {
    "rank00": "window ranks disagree",
    "num44": "cell numbers disagree",
    "q04": "model cell rank at (0, 4)",
}
for bad in saying_for:
    assert run_skewed(bad), bad


# The tie hunt (#601): on a run fixed to the witness grid the reported pair is
# the oracle's, and it is flagged when a tied cell shares a window with a
# clued cell (r2c4..r2c6 share one with r1c5). A grid without a tie has no
# answer under the constraint.
def pinned(g, cell_clues):
    digits = {(r, c): g[r][c] for r in range(9) for c in range(9)}
    return checker.Opener(9, {}, cell_clues, {}, digits)


w_ranks = oracle.window_ranks(TIE_WITNESS)
w_cranks = oracle.cell_ranks(oracle.cell_numbers(w_ranks))
report = checker.run(
    pinned(TIE_WITNESS, {(8, 8): w_cranks[8][8]}),
    corner=None,
    hypotheses=True,
    count=2,
    workers=1,
    timeout=60,
    tie=True,
)
assert report.status == "unique", report.status
(sol,) = report.solutions
assert sol.tie == oracle.seven_digit_ties(w_ranks)[0]
assert sol.tie_touches == []
assert "tie: r4c6 2|25|12|46 = r5c4 22|51|24|6, number 2251246, QQRR 39" in (
    checker.render_solution(sol, 1)
)
# r4c6 reads the window with top-left r3c5, which r3c5 itself also reads.
report = checker.run(
    pinned(TIE_WITNESS, {(2, 4): w_cranks[2][4]}),
    corner=None,
    hypotheses=True,
    count=1,
    workers=1,
    timeout=60,
    tie=True,
)
assert report.solutions[0].tie_touches == [(2, 4)]
assert "touches the QQRR cage at r3c5" in checker.render_solution(
    report.solutions[0], 1
)
report = checker.run(
    fixed, corner=None, hypotheses=True, count=2, workers=1, timeout=60, tie=True
)
assert report.status == "infeasible", report.status

# The oracle recheck of the pair is live: a model pair literal the oracle
# does not confirm is refused, not reported.
qt = model.build(9)
pairs = model.add_seeing_tie(qt)
for r in range(9):
    for c in range(9):
        qt.m.Add(qt.x[r][c] == TIE_WITNESS[r][c])
solver = cpsat.solver(30)
assert solver.Solve(qt.m) in cpsat.SOLVED
assert checker._extract(solver, qt, [], pairs).tie[:2] == ((3, 5), (4, 3))


class Lying:
    def __init__(self, s, pairs):
        self.s, self.names = s, {p.Name(): k for k, p in pairs.items()}

    def Value(self, v):
        key = self.names.get(v.Name())
        if key is not None:
            return int(key == ((1, 1), (1, 2)))
        return self.s.Value(v)


assert refuses(
    checker._extract,
    Lying(solver, pairs),
    qt,
    [],
    pairs,
    error=AssertionError,
    saying="is not a tie the oracle finds",
)
# `_extract` fills the whole tie report, the cage flag included.
sol = checker._extract(solver, qt, [], pairs, clued=[(2, 4), (8, 8)])
assert sol.tie_touches == [(2, 4)]

# The recheck is on the path `run` takes: an oracle that finds no tie refuses
# the model's pair there too.
real = checker.oracle.seven_digit_ties
checker.oracle.seven_digit_ties = lambda ranks: []
try:
    assert refuses(
        checker.run,
        pinned(TIE_WITNESS, {}),
        corner=None,
        hypotheses=True,
        count=1,
        workers=1,
        timeout=60,
        tie=True,
        error=AssertionError,
        saying="is not a tie the oracle finds",
    )
finally:
    checker.oracle.seven_digit_ties = real

# The verdict line says the tie constraint was on: "infeasible" under it
# means no tie, not a dead opener.
text = checker.render(
    checker.run(
        fixed, corner=None, hypotheses=True, count=2, workers=1, timeout=60, tie=True
    )
)
assert text.startswith("infeasible:") and "tie=on" in text, text
assert "tie=off" in checker.render(
    checker.run(fixed, corner=None, hypotheses=True, count=2, workers=1, timeout=60)
)

# The CLI hands --tie to the run: the verdict line it prints (the last one, from
# the Report) says tie=on only when the run was asked for the tie. A zero
# timeout ends each run at once, so the verdict is a timeout (exit 2).
import contextlib
import io

import qqrr_cpsat


def cli_verdict(*flags):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = qqrr_cpsat.main(
            [*flags, "--count", "1", "--workers", "1", "--timeout", "0"]
        )
    return code, out.getvalue().splitlines()[-1]


code, verdict = cli_verdict("--tie")
assert code == 2 and verdict.startswith("timeout:") and "tie=on" in verdict, verdict
code, verdict = cli_verdict()
assert code == 2 and verdict.startswith("timeout:") and "tie=off" in verdict, verdict

print("ok test_checker")
