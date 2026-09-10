"""How many sets of circled 2x2 / 2x3 rectangles a real sudoku can carry.

Geometry alone allows 422,438 non-empty sets of circled 2x2 and 2x3 placements
on a 9x9 -- disjoint, non-touching (each is a maximal chocolate group, so a
shared border cell would be chocolate in one and banana in the other), and
sitting at a box offset the #377 catalogue permits a circle at. That count
ignores digits, and digits are most of the answer: 826 of the 3,308 two-
rectangle sets admit no solved sudoku at all.

This counts the sets a sudoku can actually hold. For each set it asks for a
solved grid in which every rectangle is internally whisper-legal (every
orthogonal pair inside differs by at least 5, because every cell of a chocolate
rectangle is chocolate) and every rectangle holds its own size on a cell the
catalogue allows -- 4 in a 2x2, 6 in a 2x3.

Levels are built in order and pruned: a set containing an infeasible subset is
infeasible, because it carries all of that subset's constraints and more. So
only feasible sets are ever extended, and most of the 422,438 are never solved.

    uv run --with ortools docs/research/renbanana/tools/count_circled_sets.py \
        --procs 16 --out docs/research/renbanana/circled-sets
"""

import argparse
import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from ortools.sat.python import cp_model as cp

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import count_circled_pairs as ccp
import renbanana_cpsat as rc
import renbanana_verify as rv

N = 9
CELLS = [(r, c) for r in range(N) for c in range(N)]
PLACES = [(a, b, r, c) for a, b, pl in ccp.circleable_shapes() for r, c in pl]


def digits_exist(indices):
    """Is there a solved sudoku carrying every rectangle in this set?"""
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
    for idx in indices:
        a, b, r0, c0 = PLACES[idx]
        inside = ccp.cells_of(a, b, r0, c0)
        for p in sorted(inside):
            for q in rv.neighbours(*p):
                if q in inside and q > p:
                    far = m.new_bool_var(f"f{p}{q}")
                    m.add(d[p] - d[q] >= 5).only_enforce_if(far)
                    m.add(d[q] - d[p] >= 5).only_enforce_if(far.negated())
        sites = [(r0 + i, c0 + j) for i, j in rc.circle_cells_at(a, b, r0 % 3, c0 % 3)]
        got = []
        for p in sites:
            v = m.new_bool_var(f"c{idx}{p}")
            m.add(d[p] == a * b).only_enforce_if(v)
            got.append(v)
        m.add(sum(got) >= 1)
    s = cp.CpSolver()
    s.parameters.max_time_in_seconds = 60.0
    s.parameters.num_workers = 1
    status = s.solve(m)
    ok = status in (cp.OPTIMAL, cp.FEASIBLE)
    grid = (
        ["".join(str(s.value(d[r, c])) for c in range(N)) for r in range(N)]
        if ok
        else None
    )
    return indices, ok, s.status_name(status).lower(), grid


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--procs", type=int, default=16)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)

    n = len(PLACES)
    cellset = [ccp.cells_of(*p) for p in PLACES]
    halos = [c | {q for x in c for q in rv.neighbours(*x)} for c in cellset]
    compat = [
        {j for j in range(i + 1, n) if not (halos[i] & cellset[j])} for i in range(n)
    ]

    level = [()]
    counts, unknown = {}, {}
    began = time.monotonic()
    best = None
    for size in range(1, n + 1):
        # Only feasible sets are extended, so an infeasible subset prunes every
        # superset of itself without either being built.
        cand = []
        seen = set()
        for base in level:
            allowed = (
                set(range(n))
                if not base
                else set.intersection(*(compat[i] for i in base))
            )
            for j in sorted(allowed):
                if not base or j > base[-1]:
                    nxt = (*base, j)
                    if nxt not in seen:
                        seen.add(nxt)
                        cand.append(nxt)
        if not cand:
            break
        good, bad, unk = [], 0, 0
        with ProcessPoolExecutor(max_workers=a.procs) as pool:
            for indices, ok, status, grid in pool.map(digits_exist, cand, chunksize=8):
                if ok:
                    good.append(indices)
                    best = (indices, grid)
                elif status == "unknown":
                    unk += 1
                else:
                    bad += 1
        counts[size] = len(good)
        unknown[size] = unk
        print(
            f"size {size}: {len(cand):,} candidates -> {len(good):,} a sudoku can "
            f"carry, {bad:,} impossible, {unk:,} unknown "
            f"({time.monotonic() - began:.0f}s)",
            flush=True,
        )
        level = good
        if not good:
            break

    total = sum(counts.values())
    (a.out / "stats.json").write_text(
        json.dumps(
            {
                "feasible_by_size": counts,
                "unknown_by_size": unknown,
                "total_feasible_sets": total,
                "largest": len(best[0]) if best else 0,
                "largest_example": [PLACES[i] for i in best[0]] if best else [],
                "largest_grid": best[1] if best else None,
            },
            indent=1,
        )
        + "\n"
    )
    print(f"\nTOTAL sets a sudoku can carry: {total:,}")
    if best:
        print(f"largest: {len(best[0])} rectangles -> {[PLACES[i] for i in best[0]]}")


if __name__ == "__main__":
    main()
