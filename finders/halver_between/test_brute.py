"""The backtracking check and the CP-SAT rule check agree, on a hand-built
4x4 case with a known answer and on random small line sets.

The known case (boxes 2x2) has two lines, A and B, and one answer:

    3 2 1 4      halvers: r1c4 (4), r2c2 (1), r3c1 (2), r4c3 (3)
    4 1 2 3
    2 3 4 1      A: r3c4 | r4c3 r3c2 | r2c1   values 1 | 1.5 3 | 4
    1 4 3 2      B: r2c4 | r2c3 r1c3 | r2c2   values 3 | 2 1 | 0.5

It pins the semantics: B's circle r2c2 is a halver, a halved 1, and B's body
holds a plain 1, which sits between only because 0.5 < 1 (a halved 1 can
never be a body cell: 0.5 is the smallest value on any board). A's body holds
a halved 3, 1.5, strictly between 1 and 4. A's larger circle is its second, B's
its first. A third line E from r3c1 (a halved 2, value 1) to r3c4 (a plain 1)
has equal circles in the only answer, so adding it leaves no solution.

    uv run finders/halver_between/test_brute.py
"""

import random
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import brute
import rules
from rules import Line, parse_cell


def line(*names):
    cells = [parse_cell(name) for name in names]
    return Line(cells[0], tuple(cells[1:-1]), cells[-1])


A = line("r3c4", "r4c3", "r3c2", "r2c1")
B = line("r2c4", "r2c3", "r1c3", "r2c2")
E = line("r3c1", "r3c2", "r3c3", "r3c4")
KNOWN = rules.Solution(
    ((3, 2, 1, 4), (4, 1, 2, 3), (2, 3, 4, 1), (1, 4, 3, 2)),
    frozenset(parse_cell(c) for c in ("r1c4", "r2c2", "r3c1", "r4c3")),
)


def as_solution(found):
    digits, halvers = found
    return rules.Solution(digits, halvers)


def brute_status(lines, n, box, limit=2):
    found = brute.solutions(lines, n, box, limit=limit)
    return {0: "infeasible", 1: "unique"}.get(len(found), "not_unique"), found


# The known case: one answer, the same one from both checks.
cpsat_result = rules.RuleModel([A, B], n=4, box=(2, 2)).check()
assert cpsat_result.status == "unique", cpsat_result
assert cpsat_result.first == KNOWN, cpsat_result.first
found = brute.solutions([A, B], 4, (2, 2), limit=2)
assert [as_solution(f) for f in found] == [KNOWN], found

# Equal circles leave E no body value: no solution from either check, though
# E alone has solutions.
assert rules.RuleModel([A, B, E], n=4, box=(2, 2)).check().status == "infeasible"
assert brute.solutions([A, B, E], 4, (2, 2), limit=2) == []
assert rules.RuleModel([E], n=4, box=(2, 2)).check().status == "not_unique"
assert len(brute.solutions([E], 4, (2, 2), limit=2)) == 2

# Random 4x4 king-step line sets: both checks give the same status, and the
# same answer when it is unique.
rng = random.Random(39)
cells = [(r, c) for r in range(4) for c in range(4)]


def random_line():
    path = [rng.choice(cells)]
    for _ in range(rng.randint(2, 4)):
        steps = [
            (path[-1][0] + dr, path[-1][1] + dc)
            for dr in (-1, 0, 1)
            for dc in (-1, 0, 1)
            if (dr, dc) != (0, 0)
        ]
        steps = [s for s in steps if s in cells and s not in path]
        if not steps:
            break
        path.append(rng.choice(steps))
    if len(path) < 3:
        return random_line()
    return Line(path[0], tuple(path[1:-1]), path[-1])


statuses = set()
for _ in range(150):
    lines = [random_line() for _ in range(rng.randint(1, 3))]
    expected = rules.RuleModel(lines, n=4, box=(2, 2)).check()
    status, found = brute_status(lines, 4, (2, 2))
    assert status == expected.status, (lines, status, expected.status)
    if status == "unique":
        assert as_solution(found[0]) == expected.first, lines
    statuses.add(status)
assert statuses == {"infeasible", "unique", "not_unique"}, statuses

# Chris's 9x9 board: more than one solution, found well inside the gate's time.
board = rules.load_lines(Path(__file__).resolve().parent / "board.json")
started = time.monotonic()
found = brute.solutions(board, 9, (3, 3), limit=2)
assert len(found) == 2, found
for f in found:
    assert all(rules.line_holds(as_solution(f), ln) for ln in board)
assert time.monotonic() - started < 30, time.monotonic() - started

print("ok")
