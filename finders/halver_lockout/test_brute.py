"""The backtracking check and the CP-SAT rule check agree on status and on
solution sets, up to a limit: on every 4x4 board (2x2 boxes) with one
lockout line of 3 or 4 cells, and on the hand-built 9x9 fixtures, one
infeasible, one unique and one not unique. A search past its deadline raises
`OutOfTime` and returns no count.

On 4x4 the largest gap between two values is 4 - 0.5 = 3.5, so a gap of 4
leaves every lockout line there with no solution, and both checks say so.
The 4x4 comparison runs at a gap of 2, SudokuMaker's own gap for four digits
(half the digit count, rounded down), so its bodies have values to take.

    uv run finders/halver_lockout/test_brute.py
"""

import json
import sys
import time
from pathlib import Path

from ortools.sat.python import cp_model

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import brute
import rules
from rules import Line

LIMIT = 2000


class _Collect(cp_model.CpSolverSolutionCallback):
    def __init__(self, board, limit):
        super().__init__()
        self.board, self.limit, self.found = board, limit, set()

    def on_solution_callback(self):
        n = self.board.n
        digits = tuple(
            tuple(self.Value(self.board.x[r, c]) for c in range(n)) for r in range(n)
        )
        halvers = frozenset(c for c, h in self.board.h.items() if self.Value(h))
        self.found.add(rules.Solution(digits, halvers))
        if len(self.found) >= self.limit:
            self.StopSearch()


def cpsat_solutions(lines, n, box, gap, limit):
    """Up to `limit` solutions of the CP-SAT model, as a set."""
    board = rules.RuleModel(lines, n=n, box=box, gap=gap)
    solver = cp_model.CpSolver()
    solver.parameters.enumerate_all_solutions = True
    solver.parameters.num_workers = 1
    solver.parameters.max_time_in_seconds = 60
    collect = _Collect(board, limit)
    status = solver.Solve(board.model, collect)
    assert status in (cp_model.OPTIMAL, cp_model.FEASIBLE, cp_model.INFEASIBLE), (
        solver.StatusName(status)
    )
    return collect.found


def brute_solutions(lines, n, box, gap, limit):
    found = brute.solutions(lines, n, box, limit=limit, gap=gap)
    assert len(found) == len(set(found)), "the search found a solution twice"
    return {rules.Solution(digits, halvers) for digits, halvers in found}


def status(count):
    return {0: "infeasible", 1: "unique"}.get(count, "not_unique")


def agree(lines, n, box, gap, limit=LIMIT):
    """Both checks give the same solution set, or both reach `limit`; every
    solution keeps every line, read in plain Python. Returns the status."""
    model = cpsat_solutions(lines, n, box, gap, limit)
    search = brute_solutions(lines, n, box, gap, limit)
    if len(model) < limit or len(search) < limit:
        assert model == search, (lines, len(model), len(search))
    for solution in model | search:
        assert all(rules.line_holds(solution, ln, gap=gap) for ln in lines), lines
    return status(len(model))


# Every 4x4 lockout line of 3 or 4 king-step cells, one per path and its
# reverse.
cells = [(r, c) for r in range(4) for c in range(4)]


def extend(path):
    r, c = path[-1]
    for dr in (-1, 0, 1):
        for dc in (-1, 0, 1):
            step = (r + dr, c + dc)
            if step != (r, c) and step in cells and step not in path:
                yield [*path, step]


paths, every = [[cell] for cell in cells], set()
for size in (2, 3, 4):
    paths = [longer for path in paths for longer in extend(path)]
    if size > 2:
        every |= {min(tuple(p), tuple(reversed(p))) for p in paths}
assert len(every) == 204 + 882, len(every)

statuses = {}
for path in sorted(every):
    line = Line(path[0], tuple(path[1:-1]), path[-1])
    got = agree([line], 4, (2, 2), gap=2)
    statuses[got] = statuses.get(got, 0) + 1
assert set(statuses) == {"infeasible", "not_unique"}, statuses

# At the 9x9 gap of 4, a 4x4 line has no solution from either check.
for path in sorted(every)[:20]:
    line = Line(path[0], tuple(path[1:-1]), path[-1])
    assert agree([line], 4, (2, 2), gap=4) == "infeasible", line

# The 9x9 fixtures: each status, with the same solutions from both checks.
for name, expected in [
    ("infeasible", "infeasible"),
    ("unique", "unique"),
    ("not_unique", "not_unique"),
]:
    lines = rules.load_lines(HERE / "fixtures" / f"{name}.json")
    assert agree(lines, 9, (3, 3), gap=rules.GAP, limit=50) == expected, name

# The unique fixture's one answer is the CP-SAT check's.
unique = rules.load_lines(HERE / "fixtures" / "unique.json")
answer = rules.RuleModel(unique).check(time_limit=60)
assert answer.status == "unique", answer.status
assert brute_solutions(unique, 9, (3, 3), rules.GAP, 2) == {answer.first}

# A deadline already past stops the search before its first node: no count,
# never a short one read as a count.
try:
    brute.solutions(unique, 9, (3, 3), limit=2, deadline=time.monotonic() - 1)
except brute.OutOfTime:
    pass
else:
    raise AssertionError("a search past its deadline returned a count")

print("ok", json.dumps(statuses, sort_keys=True))
