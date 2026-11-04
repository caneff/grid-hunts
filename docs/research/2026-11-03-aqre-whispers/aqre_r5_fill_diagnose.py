"""SCRATCH: why do the logged r5 layouts fail the digit fill?

Rule pieces of a fill: each house's digits, each shaded cell's low/high sign, each
shaded adjacent pair's whisper, each r5 digit. For each logged layout: refill with one
family dropped, then delete pieces one by one, keeping a deletion only while the fill
stays infeasible. What is left is a minimal failing set, one of possibly several.
"""

import json
import sys
from pathlib import Path

from ortools.sat.python import cp_model

CELLS = [(r, c) for r in range(9) for c in range(9)]
DIGITS = range(1, 10)
ROW = 4


def pieces(layout):
    region, shade, n = layout["region"], layout["shaded"], layout["n"]
    out = []
    for i in range(9):
        out.append(("row", i))
        out.append(("col", i))
        out.append(("region", i))
    for r, c in CELLS:
        if shade[r][c]:
            out.append(("sign", (r, c)))
            for rr, cc in ((r, c + 1), (r + 1, c)):
                if rr < 9 and cc < 9 and shade[rr][cc]:
                    out.append(("whisper", (r, c), (rr, cc)))
    for c in range(9):
        count = 9 if c == n else sum(
            shade[a][b] for a, b in CELLS if region[a][b] == region[ROW][c]
        )
        out.append(("given", (ROW, c), count))
    return out


def house_cells(piece, region):
    kind, i = piece
    if kind == "row":
        return [(i, c) for c in range(9)]
    if kind == "col":
        return [(r, i) for r in range(9)]
    return [cell for cell in CELLS if region[cell[0]][cell[1]] == i]


def status(layout, chosen):
    m = cp_model.CpModel()
    d = {cell: {v: m.new_bool_var("") for v in DIGITS} for cell in CELLS}
    even_low = m.new_bool_var("even_low")
    for cell in CELLS:
        m.add_exactly_one(d[cell].values())
    for piece in chosen:
        if piece[0] in ("row", "col", "region"):
            cells = house_cells(piece, layout["region"])
            for v in DIGITS:
                m.add_exactly_one(d[cell][v] for cell in cells)
        elif piece[0] == "sign":
            r, c = piece[1]
            low = even_low if (r + c) % 2 == 0 else even_low.Not()
            m.add(d[r, c][5] == 0)
            for v in DIGITS:
                if v > 5:
                    m.add_bool_or(low.Not(), d[r, c][v].Not())
                if v < 5:
                    m.add_bool_or(low, d[r, c][v].Not())
        elif piece[0] == "whisper":
            for a in DIGITS:
                for b in DIGITS:
                    if abs(a - b) < 5:
                        m.add_bool_or(d[piece[1]][a].Not(), d[piece[2]][b].Not())
        else:
            m.add(d[piece[1]][piece[2]] == 1)
    s = cp_model.CpSolver()
    s.parameters.num_workers = 1
    s.parameters.max_time_in_seconds = 10.0
    return s.status_name(s.solve(m))


def main(path, limit):
    layouts = [json.loads(line) for line in Path(path).read_text().splitlines()][:limit]
    for i, layout in enumerate(layouts):
        every = pieces(layout)
        print(f"layout {i + 1}: 9 in r5c{layout['n'] + 1}")
        print("  all rules:", status(layout, every))
        for family in ("given", "whisper", "sign", "region"):
            print(f"  without {family}:", status(layout, [p for p in every if p[0] != family]))
        core = list(every)
        for piece in every:
            trial = [p for p in core if p != piece]
            if status(layout, trial) == "INFEASIBLE":
                core = trial
        print(f"  minimal failing set, {len(core)} pieces:")
        for piece in core:
            print("    ", piece)
        for r in range(9):
            print("    ", "".join("#" if layout["shaded"][r][c] else "." for c in range(9)),
                  "".join(str(layout["region"][r][c]) for c in range(9)))


if __name__ == "__main__":
    main(sys.argv[1], int(sys.argv[2]))
