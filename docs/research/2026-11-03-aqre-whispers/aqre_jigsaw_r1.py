"""SCRATCH: 8 circles in r1 of a jigsaw sudoku, with the solver choosing the regions.

Digits 1-9, Aqre shading, 5-whispers on shaded cells, a circle counting the shaded
cells in its region, every region with a shaded cell. Eight r1 cells are circled.
Those digits must be 1-8, since no region reaches a count of 9, so the ninth r1
cell, column `n`, is the 9, uncircled.

If all nine regions touch r1, every region is a straight column: a region touching
r1 and r9 needs all 9 cells for that, and r9's nine cells each need such a region.
A straight column has at most 7 shaded cells, so a count of 8 fails. Hence exactly
eight regions touch r1, and the 9 in r1 shares a region with a circled r1 cell. The
ninth region, index `n`, stays off r1. `n` runs over columns 5,4,3,2,1 only, since
the mirror image covers the rest.

Region k != n is rooted at r1 column k; region n has a free root. A level on each
cell keeps regions connected: a non-root cell has one parent, a neighbour in its
region, one level nearer.

Stage one drops shaded connectivity: an infeasible answer there settles it (under
the assumption), and its grid warm-starts stage two with flow connectivity.
"""

import json
import sys
from pathlib import Path

from aqre_jigsaw_feasible import connected, controls, draw, neighbours, violations
from connected import add_flow_connectivity
from ortools.sat.python import cp_model
from sudoku_kit.cpsat import solver

RELAX_LIMIT = 120.0
TIME_LIMIT = 300.0
CELLS = [(r, c) for r in range(9) for c in range(9)]
DIGITS = range(1, 10)


def build(connect, n):
    m = cp_model.CpModel()
    d = {cell: {v: m.new_bool_var(f"d{cell}{v}") for v in DIGITS} for cell in CELLS}
    y = {cell: [m.new_bool_var(f"y{cell}{k}") for k in range(9)] for cell in CELLS}
    g = [m.new_bool_var(f"g{i}") for i in range(81)]
    shaded = lambda r, c: g[r * 9 + c]
    for cell in CELLS:
        m.add_exactly_one(d[cell].values())
        m.add_exactly_one(y[cell])
    for i in range(9):
        for v in DIGITS:
            m.add_exactly_one(d[i, c][v] for c in range(9))
            m.add_exactly_one(d[r, i][v] for r in range(9))

    level = {cell: m.new_int_var(0, 8, f"l{cell}") for cell in CELLS}
    m.add(d[0, n][9] == 1)
    for c in range(9):
        m.add(y[0, c][n] == 0)
        if c != n:
            m.add(y[0, c][c] == 1)
            m.add(level[0, c] == 0)
    free_roots = []
    for cell in CELLS:
        if cell[0] == 0 and cell[1] != n:
            continue
        root = None
        parents = []
        if cell[0] != 0:
            root = m.new_bool_var(f"root{cell}")
            free_roots.append(root)
            m.add_implication(root, y[cell][n])
            m.add(level[cell] == 0).only_enforce_if(root)
            parents.append(root)
        for other in neighbours(cell):
            p = m.new_bool_var(f"p{cell}{other}")
            parents.append(p)
            m.add(level[cell] >= 1).only_enforce_if(p)
            m.add(level[cell] == level[other] + 1).only_enforce_if(p)
            for k in range(9):
                m.add_bool_or(p.Not(), y[cell][k].Not(), y[other][k])
        m.add_exactly_one(parents)
    m.add_exactly_one(free_roots)

    for k in range(9):
        m.add(sum(y[cell][k] for cell in CELLS) == 9)
        for v in DIGITS:
            both = []
            for cell in CELLS:
                z = m.new_bool_var(f"z{cell}{k}{v}")
                m.add_implication(z, y[cell][k])
                m.add_implication(z, d[cell][v])
                m.add_bool_or(z, y[cell][k].Not(), d[cell][v].Not())
                both.append(z)
            m.add_exactly_one(both)

    for k in range(9):
        terms = []
        for cell in CELLS:
            w = m.new_bool_var(f"w{cell}{k}")
            m.add_implication(w, y[cell][k])
            m.add_implication(w, shaded(*cell))
            m.add_bool_or(w, y[cell][k].Not(), shaded(*cell).Not())
            terms.append(w)
        count = sum(terms)
        m.add(count >= 1)
        m.add(count <= 8)  # a shaded 5 has no valid shaded neighbour
        if k != n:
            m.add(count == sum(v * d[0, k][v] for v in DIGITS))

    for a in range(9):
        for b in range(6):
            for line in (
                [shaded(a, b + k) for k in range(4)],
                [shaded(b + k, a) for k in range(4)],
            ):
                m.add_bool_or(line)
                m.add_bool_or([v.Not() for v in line])

    even_low = m.new_bool_var("even_low")
    for r, c in CELLS:
        low = even_low if (r + c) % 2 == 0 else even_low.Not()
        s = shaded(r, c)
        m.add_implication(s, d[r, c][5].Not())
        for v in DIGITS:
            if v > 5:
                m.add_bool_or(s.Not(), low.Not(), d[r, c][v].Not())
            if v < 5:
                m.add_bool_or(s.Not(), low, d[r, c][v].Not())
    for cell in CELLS:
        for other in neighbours(cell):
            if cell < other:
                for a in DIGITS:
                    for b in DIGITS:
                        if abs(a - b) < 5:
                            m.add_bool_or(
                                shaded(*cell).Not(), shaded(*other).Not(),
                                d[cell][a].Not(), d[other][b].Not(),
                            )
    if connect:
        add_flow_connectivity(m, g)
    return m, d, y, g


def main(out_dir):
    for n in (4, 3, 2, 1, 0):
        if attempt(n, out_dir):
            return 0
    return 0


def attempt(n, out_dir):
    print(f"9 in r1c{n + 1}", flush=True)
    rm, rd, ry, rg = build(False, n)
    rs = solver(RELAX_LIMIT)
    rstatus = rs.solve(rm)
    print(f"no shaded connectivity: status {rs.status_name(rstatus)} in {rs.wall_time:.1f}s", flush=True)
    if rstatus == cp_model.INFEASIBLE:
        return False
    if rstatus in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        out = Path(out_dir)
        out.mkdir(parents=True, exist_ok=True)
        (out / f"relaxed-r1c{n + 1}.json").write_text(json.dumps({
            "digits": [[next(v for v in DIGITS if rs.value(rd[r, c][v])) for c in range(9)] for r in range(9)],
            "shaded": [[bool(rs.value(rg[r * 9 + c])) for c in range(9)] for r in range(9)],
            "region": [[next(k for k in range(9) if rs.value(ry[r, c][k])) for c in range(9)] for r in range(9)],
        }))
    m, d, y, g = build(True, n)
    if rstatus in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        for cell in CELLS:
            for v in DIGITS:
                m.add_hint(d[cell][v], rs.value(rd[cell][v]))
            for k in range(9):
                m.add_hint(y[cell][k], rs.value(ry[cell][k]))
            m.add_hint(g[cell[0] * 9 + cell[1]], rs.value(rg[cell[0] * 9 + cell[1]]))
    s = solver(TIME_LIMIT)
    status = s.solve(m)
    print(f"full: status {s.status_name(status)} in {s.wall_time:.1f}s", flush=True)
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return False
    digits = [[next(v for v in DIGITS if s.value(d[r, c][v])) for c in range(9)] for r in range(9)]
    shade = [[bool(s.value(g[r * 9 + c])) for c in range(9)] for r in range(9)]
    region = {cell: next(k for k in range(9) if s.value(y[cell][k])) for cell in CELLS}
    regions = [[cell for cell in CELLS if region[cell] == k] for k in range(9)]
    controls(digits, shade, regions)
    broken = violations(digits, shade, regions)
    broken += [f"region {k} split" for k, cells in enumerate(regions) if not connected(cells) or len(cells) != 9]
    counts = [sum(shade[r][c] for r, c in cells) for cells in regions]
    circled = [c for c in range(9) if c != n]
    if digits[0][n] != 9:
        broken.append("r1's uncircled cell is not the 9")
    broken += [f"r1c{c + 1} digit {digits[0][c]}, region count {counts[c]}" for c in circled if digits[0][c] != counts[c]]
    if len(circled) != 8:
        broken.append(f"{len(circled)} circles in r1")
    print(f"reader violations {broken or 'none'} (controls fired)", flush=True)
    print("regions:")
    print("\n".join("".join(str(region[r, c]) for c in range(9)) for r in range(9)), flush=True)
    print("\n".join(
        " ".join(("#" if shade[i][j] else ".") + str(digits[i][j]) for j in range(9))
        for i in range(9)
    ), flush=True)
    print(f"region counts by r1 column {counts}, shaded total {sum(counts)}", flush=True)
    spots = [(0, c) for c in circled]
    ninth = next((cell for cell in regions[n] if digits[cell[0]][cell[1]] == counts[n]), None)
    if ninth:
        spots.append(ninth)
    print(f"ninth region circle {ninth}", flush=True)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "grid-8-r1.json").write_text(json.dumps({
        "digits": digits, "shaded": shade, "regions": regions, "counts": counts,
    }))
    draw(digits, shade, region, spots, out / "grid-8-r1.png")
    print("picture", out / "grid-8-r1.png", flush=True)
    return True


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
