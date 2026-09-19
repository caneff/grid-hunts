"""Second opinion on the 26-cell ceiling, sharing no encoding with joint.py.

    uv run finders/counting_shaded/recheck_ceiling.py --seconds 300
    uv run finders/counting_shaded/recheck_ceiling.py --exactly 27   # expect INFEASIBLE

`joint.py` says the largest connected all-visible shaded cell set is 26, OPTIMAL.
That is a proof about one model, so this rebuilds the question three different
ways and checks the answers meet:

* sudoku as one-hot booleans with exactly-one per cell and per house digit,
  not integer variables under add_all_different;
* the all-visible link as `cnt[i] == d` enforced on the pair (shaded cell, digit d),
  not as an equality between a digit variable and a sum;
* connectivity as a rooted spanning tree with level labels -- every shaded cell is
  the root or has exactly one orthogonal parent one level below it -- not as
  single-commodity flow.

`--check-connectivity` tests the tree encoding against flood fill directly, the
way the flow encoding was tested, so a disagreement shows up as itself rather
than as a wrong ceiling.
"""

import argparse
import random
import time

from ortools.sat.python import cp_model
from shapes import BOX, NEIGH, ORTH, connected


def add_tree_connectivity(m, g):
    """Rooted spanning tree: one root, every other shaded cell has a parent below it."""
    lvl = [m.new_int_var(0, 80, f"l{i}") for i in range(81)]
    root = [m.new_bool_var(f"rt{i}") for i in range(81)]
    m.add_exactly_one(root)
    for i in range(81):
        m.add_implication(root[i], g[i])
        m.add(lvl[i] == 0).only_enforce_if(root[i])
        parents = []
        for j in ORTH[i]:
            p = m.new_bool_var(f"p{i}_{j}")
            m.add_implication(p, g[j])
            m.add_implication(p, g[i])
            m.add(lvl[i] == lvl[j] + 1).only_enforce_if(p)
            parents.append(p)
        # every shaded cell is the root or has exactly one parent; a unshaded neither
        m.add(sum(parents) + root[i] == g[i])


def build(connect=True, exactly=None):
    m = cp_model.CpModel()
    x = [[m.new_bool_var(f"x{i}_{d}") for d in range(10)] for i in range(81)]
    for i in range(81):
        m.add(x[i][0] == 0)
        m.add_exactly_one(x[i][1:])
    for d in range(1, 10):
        for r in range(9):
            m.add_exactly_one([x[r * 9 + c][d] for c in range(9)])
            m.add_exactly_one([x[c * 9 + r][d] for c in range(9)])
        for b in range(9):
            m.add_exactly_one([x[i][d] for i in range(81) if BOX[i] == b])
    g = [m.new_bool_var(f"g{i}") for i in range(81)]
    cnt = [m.new_int_var(0, 8, f"c{i}") for i in range(81)]
    for i in range(81):
        m.add(cnt[i] == sum(g[j] for j in NEIGH[i]))
        for d in range(1, 10):
            m.add(cnt[i] == d).only_enforce_if([g[i], x[i][d]])
    if connect:
        add_tree_connectivity(m, g)
    if exactly is not None:
        m.add(sum(g) == exactly)
    return m, x, g


def check_connectivity(trials, seconds):
    """Tree encoding vs flood fill on random shapes."""
    rng = random.Random(5)
    bad = nc = 0
    for _ in range(trials):
        n = rng.randint(2, 30)
        if rng.random() < 0.5:
            sh = {rng.randrange(81)}
            while len(sh) < n:
                cands = [j for i in sh for j in ORTH[i] if j not in sh]
                if not cands:
                    break
                sh.add(rng.choice(cands))
        else:
            sh = set(rng.sample(range(81), n))
        m = cp_model.CpModel()
        g = [m.new_bool_var(f"g{i}") for i in range(81)]
        for i in range(81):
            m.add(g[i] == (1 if i in sh else 0))
        add_tree_connectivity(m, g)
        s = cp_model.CpSolver()
        s.parameters.num_workers = 1
        s.parameters.max_time_in_seconds = seconds
        got = s.solve(m) in (cp_model.OPTIMAL, cp_model.FEASIBLE)
        truth = connected(sh)
        nc += truth
        if got != truth:
            bad += 1
            print(f"MISMATCH {sorted(sh)}: flood fill {truth}, tree {got}")
    print(
        f"tree connectivity vs flood fill: {trials - bad}/{trials} agree ({nc} connected)"
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seconds", type=float, default=300)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--exactly", type=int)
    ap.add_argument("--no-connect", action="store_true")
    ap.add_argument("--check-connectivity", type=int, default=0)
    a = ap.parse_args()
    if a.check_connectivity:
        check_connectivity(a.check_connectivity, 10)
        return
    m, x, g = build(connect=not a.no_connect, exactly=a.exactly)
    if a.exactly is None:
        m.maximize(sum(g))
    s = cp_model.CpSolver()
    s.parameters.num_workers = a.workers
    s.parameters.max_time_in_seconds = a.seconds
    t = time.monotonic()
    st = s.solve(m)
    el = time.monotonic() - t
    label = f"exactly {a.exactly}" if a.exactly else "maximize"
    conn = "tree connectivity" if not a.no_connect else "NO connectivity"
    print(f"{label}, {conn}: {s.status_name(st)} in {el:.1f}s")
    if st not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return
    shape = {i for i in range(81) if s.value(g[i])}
    grid = [next(d for d in range(1, 10) if s.value(x[i][d])) for i in range(81)]
    print(f"  shaded cells {len(shape)}  flood-fill connected: {connected(shape)}")
    ok = all(grid[i] == sum(j in shape for j in NEIGH[i]) for i in shape)
    print(f"  every shaded cell digit equals its neighbour count: {ok}")
    for r in range(9):
        print(
            "  "
            + " ".join(
                f"({grid[r * 9 + c]})" if r * 9 + c in shape else f" {grid[r * 9 + c]} "
                for c in range(9)
            )
        )
    assert all(len({grid[r * 9 + c] for c in range(9)}) == 9 for r in range(9))
    assert all(len({grid[r * 9 + c] for r in range(9)}) == 9 for c in range(9))
    assert all(
        len({grid[i] for i in range(81) if BOX[i] == b}) == 9 for b in range(9)
    ), "box"
    print("  grid re-verified as a valid sudoku independently of the solver")


if __name__ == "__main__":
    main()
