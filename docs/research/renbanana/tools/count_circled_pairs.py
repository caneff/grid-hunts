"""How many ways can a circled 2x2 and a circled 2x3 coexist in one grid?

The pool has 78 verified grids in about 18 shading families and not one holds
two chocolate rectangles that both carry a circle. That could mean the
geometry is scarce, or that the digits refuse. This separates the two.

Layer B -- each rectangle judged against the #377 catalogue alone -- says the
geometry is not scarce: 28 of 64 placements of a 2x2 can carry a circle, 38 of
56 of a 2x3 (and of a 3x2), and after dropping pairs that overlap or touch,
1360 geometries survive. Touching is out because each rectangle has to be a
*maximal* chocolate group, so a shared border cell would be chocolate in one
and banana in the other.

Layer B judges the two rectangles independently, which is the gap this closes.
Two rectangles sharing a box, a row, or a column constrain each other, and a
circle demands a specific digit in each: 4 somewhere in the 2x2, 6 somewhere in
the 2x3. So for every surviving geometry this asks CP-SAT for a full solved
sudoku in which both rectangles are internally whisper-legal (every orthogonal
pair inside a chocolate rectangle differs by at least 5) and both circles land.

An INFEASIBLE here is a proof about the pair, and it is a proof no amount of
walking would have found.

    uv run --with ortools docs/research/renbanana/tools/count_circled_pairs.py \
        --procs 8 --out docs/research/renbanana/circled-pairs
"""

import argparse
import json
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from ortools.sat.python import cp_model as cp

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import renbanana_cpsat as rc
import renbanana_verify as rv

N = 9
CELLS = [(r, c) for r in range(N) for c in range(N)]


def circle_capable(a, b):
    """Placements of an `a` by `b` rectangle the catalogue lets carry a circle."""
    return [
        (r0, c0)
        for r0 in range(N - a + 1)
        for c0 in range(N - b + 1)
        if rc.fillings_at(a, b, r0 % 3, c0 % 3)
        and rc.circle_cells_at(a, b, r0 % 3, c0 % 3)
    ]


def cells_of(a, b, r0, c0):
    return {(r0 + i, c0 + j) for i in range(a) for j in range(b)}


# The catalogue allows a circle on exactly four shapes with both sides >= 2 --
# 2x2, 2x3, 2x4 and 3x3, plus the transposes. Every other living shape (2x5,
# 2x6, 2x7, 3x4, 3x5, 3x6, 4x4) can never hold its own size, so it is
# permanently uncircleable and no hunt should aim at one.
#
# Of the four, 2x4 and 3x3 are the easy ones: 2x4 can carry a circle at all
# nine box offsets and 3x3 at eight, against five for a 2x2. The hunt is for
# the hard pair, so the default is 2x2 and 2x3 only -- two 2x2s, two 2x3s, or
# one of each all count.
WANTED = ((2, 2), (2, 3), (3, 2))


def circleable_shapes(wanted=WANTED):
    """The wanted shapes, each with the placements the catalogue allows."""
    return [(a, b, circle_capable(a, b)) for a, b in wanted if circle_capable(a, b)]


def geometries(wanted=WANTED):
    """Every pair of circled rectangles that is disjoint and does not touch.

    Every ordered-once pair drawn from the wanted shapes, so two 2x2s and two
    2x3s are in scope alongside one of each. Touching is excluded because each
    rectangle must be a *maximal* chocolate group: a shared border cell would
    be chocolate in one and banana in the other.
    """
    places = [(a, b, r, c) for a, b, pl in circleable_shapes(wanted) for r, c in pl]
    out = []
    for i, first in enumerate(places):
        cf = cells_of(*first)
        halo = cf | {q for p in cf for q in rv.neighbours(*p)}
        out.extend(
            (first, second)
            for second in places[i + 1 :]
            if not (halo & cells_of(*second))
        )
    return out


def digits_exist(pair):
    """Is there a solved sudoku putting both circled rectangles on the board?"""
    m = cp.CpModel()
    d = {p: m.new_int_var(1, 9, f"d{p}") for p in CELLS}
    for i in range(N):
        m.add_all_different([d[i, c] for c in range(N)])
        m.add_all_different([d[r, i] for r in range(N)])
    for br in range(3):
        for bc in range(3):
            m.add_all_different(
                [d[br * 3 + r, bc * 3 + c] for r in range(3) for c in range(3)]
            )

    for a, b, r0, c0 in (pair[0], pair[1]):
        inside = sorted(cells_of(a, b, r0, c0))
        # Whisper: both cells of an orthogonal pair are chocolate here, so
        # every such pair inside the rectangle must differ by at least 5.
        for p in inside:
            for q in rv.neighbours(*p):
                if q in set(inside) and q > p:
                    far = m.new_bool_var(f"f{p}{q}")
                    m.add(d[p] - d[q] >= 5).only_enforce_if(far)
                    m.add(d[q] - d[p] >= 5).only_enforce_if(far.negated())
        # The circle: one cell of the rectangle holds the group's own size, and
        # only the cells the catalogue allows may be that cell.
        sites = [(r0 + i, c0 + j) for i, j in rc.circle_cells_at(a, b, r0 % 3, c0 % 3)]
        got = []
        for p in sites:
            v = m.new_bool_var(f"circ{p}")
            m.add(d[p] == a * b).only_enforce_if(v)
            got.append(v)
        m.add(sum(got) >= 1)

    s = cp.CpSolver()
    s.parameters.max_time_in_seconds = 30.0
    s.parameters.num_workers = 1
    status = s.solve(m)
    grid = (
        ["".join(str(s.value(d[r, c])) for c in range(N)) for r in range(N)]
        if status in (cp.OPTIMAL, cp.FEASIBLE)
        else None
    )
    return pair, s.status_name(status).lower(), grid


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--procs", type=int, default=8)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)

    geos = geometries()
    print(
        f"{len(geos)} geometries survive the catalogue; solving for digits", flush=True
    )

    tally = {"feasible": 0, "infeasible": 0, "unknown": 0}
    log = a.out / "pairs.jsonl"
    with ProcessPoolExecutor(max_workers=a.procs) as pool:
        for done, (pair, status, grid) in enumerate(
            pool.map(digits_exist, geos, chunksize=4), 1
        ):
            # CP-SAT says OPTIMAL for a satisfied satisfaction model, so a
            # tally keyed on "feasible" silently counts every success as a
            # timeout. Key it on whether a grid came back instead.
            if grid is not None:
                tally["feasible"] += 1
            elif status == "infeasible":
                tally["infeasible"] += 1
            else:
                tally["unknown"] += 1
            with log.open("a") as f:
                f.write(
                    json.dumps({"pair": pair, "status": status, "grid": grid}) + "\n"
                )
            if done % 100 == 0:
                print(f"  {done}/{len(geos)}: {tally}", flush=True)

    (a.out / "stats.json").write_text(json.dumps(tally, indent=1) + "\n")
    print(
        f"\n{tally['feasible']} of {len(geos)} geometries admit digits; "
        f"{tally['infeasible']} proved impossible, {tally['unknown']} timed out",
        flush=True,
    )


if __name__ == "__main__":
    main()
