"""SCRATCH: what the 5-given puzzle's marks and givens force at the start.

Prints the disjoint marks per line, then, over all solutions of each condition
set (marks alone, then marks and givens), which cells are always or never
targets and each edge cell's possible digits. Every answer is a CP-SAT solve; a
timeout raises. One worker.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_link import GIVENS, GRID
from nr import build, marks
from sudoku_kit.cpsat import SOLVED, UNKNOWN, solver

LIMIT = 60.0


def feasible(mark_set, ring, literal):
    m, _, b, t = build(mark_set, ring)
    kind, key, want = literal
    var = t[key] if kind == "t" else b[(*key, want)]
    if kind == "t" and not want:
        m.Add(var == 0)
    else:
        m.Add(var == 1)
    status = solver(LIMIT).Solve(m)
    if status == UNKNOWN:
        raise TimeoutError(f"no verdict in {LIMIT}s on {literal}")
    return status in SOLVED


def name(cell):
    return f"r{cell[0] + 1}c{cell[1] + 1}"


def line_report(mark_set):
    for axis, label in ((0, "r"), (1, "c")):
        for i in range(9):
            spans = []
            for r, c in sorted(mark_set):
                near, far = (r, c) if axis == 0 else (c, r)
                if i in (near, near + 1):
                    spans.append(far)
            best, last = 0, -9
            for s in sorted(set(spans)):
                if s >= last + 2:
                    best, last = best + 1, s
            print(f"{label}{i + 1}: disjoint marks {best}, spans start {sorted(set(spans))}")


def report(title, mark_set, ring):
    print("==", title)
    always, never = [], []
    for r in range(9):
        for c in range(9):
            can_be = feasible(mark_set, ring, ("t", (r, c), True))
            can_not = feasible(mark_set, ring, ("t", (r, c), False))
            if not can_not:
                always.append(name((r, c)))
            if not can_be:
                never.append(name((r, c)))
    print("always a target:", always)
    print("never a target:", never)
    for r in range(9):
        row = []
        for c in range(9):
            options = [
                d
                for d in range(1, 10)
                if feasible(mark_set, ring, ("b", (r, c), d))
            ]
            row.append("".join(map(str, options)) if len(options) < 9 else ".")
        print(f"r{r + 1}", " ".join(f"{x:>9}" for x in row), flush=True)


def main():
    mark_set = marks(GRID)
    line_report(mark_set)
    report("marks alone", mark_set, None)
    report("marks and givens", mark_set, GIVENS)


if __name__ == "__main__":
    main()
