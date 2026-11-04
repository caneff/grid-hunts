"""SCRATCH: a second uniqueness proof on PySAT, sharing no code with nr.py.

The target and window rules are clauses written here from the rule text, and the
grid's marks and outside digits are recomputed here. Usage: nr_verify_sat.py
GRID GIVENS, with GRID nine strings joined by "/" and GIVENS like "L5=1,T4=6".
Prints the grid's marks and the verdict. Exit 0 only when the grid is unique.
"""

import sys

from pysat.solvers import Cadical153


def var(r, c, d):
    return r * 81 + c * 9 + d


def tvar(r, c):
    return 729 + r * 9 + c + 1


def line(side, i):
    cells = {
        "L": [(i, k) for k in range(9)],
        "R": [(i, 8 - k) for k in range(9)],
        "T": [(k, i) for k in range(9)],
        "B": [(8 - k, i) for k in range(9)],
    }
    return cells[side]


def houses():
    for i in range(9):
        yield [(i, k) for k in range(9)]
        yield [(k, i) for k in range(9)]
    for br in (0, 3, 6):
        for bc in (0, 3, 6):
            yield [(br + r, bc + c) for r in range(3) for c in range(3)]


def clauses(window_marks, givens):
    out = []
    for r in range(9):
        for c in range(9):
            out.append([var(r, c, d) for d in range(1, 10)])
            for d in range(1, 10):
                for e in range(d + 1, 10):
                    out.append([-var(r, c, d), -var(r, c, e)])
    for house in houses():
        for d in range(1, 10):
            for i, a in enumerate(house):
                for b in house[i + 1 :]:
                    out.append([-var(*a, d), -var(*b, d)])
    support = {(r, c): [] for r in range(9) for c in range(9)}
    for side in "LRTB":
        for i in range(9):
            cells = line(side, i)
            for k, cell in enumerate(cells):
                pointer = var(*cells[0], k + 1)
                support[cell].append(pointer)
                out.append([-pointer, tvar(*cell)])
    for cell, lits in support.items():
        out.append([-tvar(*cell), *lits])
    for r in range(8):
        for c in range(8):
            a, f = tvar(r, c), tvar(r, c + 1)
            d, e = tvar(r + 1, c), tvar(r + 1, c + 1)
            if (r, c) in window_marks:
                out += [[-a, e], [a, -e], [-f, d], [f, -d], [a, f], [-a, -f]]
            else:
                out += [[-a, f, d, -e], [a, -f, -d, e]]
    for (side, i), v in givens.items():
        cells = line(side, i)
        for k, cell in enumerate(cells):
            out.append([-var(*cells[0], k + 1), var(*cell, v)])
    return out


def read_marks(grid):
    hit = set()
    for side in "LRTB":
        for i in range(9):
            cells = line(side, i)
            r, c = cells[0]
            hit.add(cells[grid[r][c] - 1])
    return {
        (r, c)
        for r in range(8)
        for c in range(8)
        if ((r, c) in hit) == ((r + 1, c + 1) in hit)
        and ((r, c + 1) in hit) == ((r + 1, c) in hit)
        and ((r, c) in hit) != ((r, c + 1) in hit)
    }


def main(text, given_text):
    grid = [[int(d) for d in row] for row in text.split("/")]
    givens = {}
    for part in filter(None, given_text.split(",")):
        name, v = part.split("=")
        givens[name[0], int(name[1:]) - 1] = int(v)
    window_marks = read_marks(grid)
    print("marks", len(window_marks), sorted(window_marks))
    with Cadical153(bootstrap_with=clauses(window_marks, givens)) as s:
        assert s.solve(), "the grid's own conditions have no solution"
        s.add_clause([-var(r, c, grid[r][c]) for r in range(9) for c in range(9)])
        second = s.solve()
    print("second grid exists" if second else "unique")
    return 1 if second else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], sys.argv[2]))
