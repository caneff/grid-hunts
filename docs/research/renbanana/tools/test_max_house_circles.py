"""The two stages must agree with the independent checker.

Stage A: pinning a verified pool shading leaves the model feasible, and the
group size it measures for every house cell equals the checker's. Pinning a
shading the checker rejects leaves it infeasible.

Stage B: on a pool shading, demanding a circle exactly where the checker says
one can sit returns a grid the checker calls LEGAL.
"""

import sys
from pathlib import Path

from ortools.sat.python import cp_model as cp

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import max_house_circles as mhc
import renbanana_verify as rv

POOL = sorted(Path(__file__).resolve().parents[1].glob("candidates*/cand_*.json"))
HOUSES = ("row5", "col3", "box9")


def sizes(is_choc):
    out = {}
    for colour in (True, False):
        for g in rv.components(is_choc, colour):
            for p in g:
                out[p] = len(g)
    return out


def pin_shading(house_name, is_choc):
    """Solve stage A with the shading pinned; return {cell: measured size}."""
    target = mhc.house(house_name)
    m, choc, size, _ = mhc.shading_model(target)
    for p in mhc.CELLS:
        m.add(choc[p] == (1 if is_choc[p] else 0))
    sol = cp.CpSolver()
    sol.parameters.num_search_workers = 4
    sol.parameters.max_time_in_seconds = 120
    if sol.solve(m) not in (cp.OPTIMAL, cp.FEASIBLE):
        return None
    return {p: sol.value(size[p]) for p in target}


def test_stage_a_measures_groups():
    for path in POOL[:4] + POOL[-3:]:
        grid, is_choc, _ = rv.load(path)
        assert not rv.check(grid, is_choc), path
        truth = sizes(is_choc)
        for name in HOUSES:
            got = pin_shading(name, is_choc)
            assert got is not None, f"{path} {name}: stage A rejected a legal shading"
            for p, n in got.items():
                assert n == truth[p], f"{path} {name} {p}: {n} != {truth[p]}"


def test_stage_a_rejects_illegal_shadings():
    _, is_choc, _ = rv.load(POOL[0])
    checked = 0
    for p in mhc.CELLS:
        broken = dict(is_choc)
        broken[p] = not broken[p]
        # Only shape violations; the checker also reports digit rules, which
        # stage A does not model.
        if any(
            v.startswith(("rule 3", "rule 4"))
            for v in rv.check(dict.fromkeys(mhc.CELLS, 1), broken)
        ):
            assert pin_shading("row5", broken) is None, (
                f"accepted a broken shading at {p}"
            )
            checked += 1
            if checked == 3:
                return
    raise AssertionError("did not find three shape-breaking flips")


def test_stage_b_reproduces_a_pool_circle():
    for path in POOL:
        grid, is_choc, _ = rv.load(path)
        truth = sizes(is_choc)
        for name in HOUSES:
            want = [p for p in mhc.house(name) if grid[p] == truth[p]]
            if len(want) < 3:
                continue
            got = mhc.digits_on(is_choc, mhc.house(name), len(want), 60, 4)
            assert got is not None, (
                f"{path} {name}: stage B refused a known circle level"
            )
            g2, circles = got
            assert len(circles) >= len(want), f"{path} {name}: too few circles"
            assert not rv.check(g2, is_choc, circles), (
                f"{path} {name}: stage B grid illegal"
            )
            return
    raise AssertionError("no pool house carried three circles")


if __name__ == "__main__":
    test_stage_a_measures_groups()
    test_stage_a_rejects_illegal_shadings()
    test_stage_b_reproduces_a_pool_circle()
    print("OK")
