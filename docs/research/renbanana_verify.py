"""Independent checker for Renbanana grids (#380).

Written from the six rules in `renbanana/FEASIBILITY.md`, not from the CP-SAT
encoding that produces candidates, so a bug in the encoding cannot hide behind
a checker that shares it. Nothing enters the candidate pool unchecked.

    uv run docs/research/renbanana_verify.py candidate.json

The rules:

1. Normal 9x9 sudoku.
2. A free binary shading, chocolate or banana, on every cell.
3. Every maximal orthogonally connected chocolate group is a rectangle.
4. Every maximal orthogonally connected banana group is not a rectangle.
5. German Chocolate: orthogonally adjacent chocolate digits differ by >= 5.
6. Renbanana: every banana group's digits are distinct and consecutive.

Plus the circle demand, when circles are supplied: a circled cell's digit
equals the size of its own group.
"""

import json
import sys
from pathlib import Path

N = 9


def cells():
    return [(r, c) for r in range(N) for c in range(N)]


def neighbours(r, c):
    return [
        (a, b)
        for a, b in ((r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1))
        if 0 <= a < N and 0 <= b < N
    ]


def components(is_choc, colour):
    """Maximal orthogonally connected groups of cells whose shading == colour."""
    seen = set()
    out = []
    for start in cells():
        if start in seen or is_choc[start] != colour:
            continue
        group = []
        stack = [start]
        seen.add(start)
        while stack:
            p = stack.pop()
            group.append(p)
            for q in neighbours(*p):
                if q not in seen and is_choc[q] == colour:
                    seen.add(q)
                    stack.append(q)
        out.append(sorted(group))
    return out


def is_rectangle(group):
    rows = [r for r, _ in group]
    cols = [c for _, c in group]
    height = max(rows) - min(rows) + 1
    width = max(cols) - min(cols) + 1
    return height * width == len(group)


def shape(group):
    """(height, width) of a rectangular group."""
    rows = [r for r, _ in group]
    cols = [c for _, c in group]
    return (max(rows) - min(rows) + 1, max(cols) - min(cols) + 1)


def check(grid, is_choc, circles=()):
    """Return a list of human-readable violations; empty means the grid is legal.

    `grid` maps (r, c) -> digit, `is_choc` maps (r, c) -> True for chocolate.
    """
    bad = []

    for i in range(N):
        row = sorted(grid[i, c] for c in range(N))
        col = sorted(grid[r, i] for r in range(N))
        if row != list(range(1, 10)):
            bad.append(f"rule 1: row {i + 1} is not 1-9: {row}")
        if col != list(range(1, 10)):
            bad.append(f"rule 1: column {i + 1} is not 1-9: {col}")
    for br in range(3):
        for bc in range(3):
            digits = sorted(
                grid[br * 3 + r, bc * 3 + c] for r in range(3) for c in range(3)
            )
            if digits != list(range(1, 10)):
                bad.append(
                    f"rule 1: box r{br * 3 + 1}c{bc * 3 + 1} is not 1-9: {digits}"
                )

    bad.extend(
        f"rule 3: chocolate group at {g[0]} is not a rectangle"
        for g in components(is_choc, True)
        if not is_rectangle(g)
    )
    bad.extend(
        f"rule 4: banana group at {g[0]} is a rectangle"
        for g in components(is_choc, False)
        if is_rectangle(g)
    )

    for r, c in cells():
        for a, b in ((r + 1, c), (r, c + 1)):
            if (
                a < N
                and b < N
                and is_choc[r, c]
                and is_choc[a, b]
                and abs(grid[r, c] - grid[a, b]) < 5
            ):
                bad.append(
                    f"rule 5: chocolate {grid[r, c]} at r{r + 1}c{c + 1} touches "
                    f"{grid[a, b]} at r{a + 1}c{b + 1}"
                )

    for group in components(is_choc, False):
        digits = [grid[p] for p in group]
        if len(set(digits)) != len(digits):
            bad.append(f"rule 6: banana group at {group[0]} repeats a digit: {digits}")
        elif max(digits) - min(digits) != len(digits) - 1:
            bad.append(
                f"rule 6: banana group at {group[0]} is not consecutive: {digits}"
            )

    if circles:
        size_of = {}
        for colour in (True, False):
            for group in components(is_choc, colour):
                for p in group:
                    size_of[p] = len(group)
        for p in circles:
            p = tuple(p)
            if grid[p] != size_of[p]:
                bad.append(
                    f"circle: r{p[0] + 1}c{p[1] + 1} holds {grid[p]} "
                    f"but its group has {size_of[p]} cells"
                )

    return bad


def load(path):
    """Read a candidate JSON: `grid` as 9 digit strings, `shading` as 9 strings
    of C (chocolate) and b (banana)."""
    d = json.loads(Path(path).read_text())
    grid = {(r, c): int(d["grid"][r][c]) for r, c in cells()}
    is_choc = {(r, c): d["shading"][r][c] == "C" for r, c in cells()}
    return grid, is_choc, [tuple(p) for p in d.get("circles", [])]


def main():
    grid, is_choc, circles = load(sys.argv[1])
    bad = check(grid, is_choc, circles)
    for line in bad:
        print(line)
    print("LEGAL" if not bad else f"{len(bad)} VIOLATIONS")
    sys.exit(0 if not bad else 1)


if __name__ == "__main__":
    main()
