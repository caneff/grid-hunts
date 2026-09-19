"""counting shaded, all visible and connected: solve for the grid and the shape together.

    uv run finders/counting_shaded/joint.py --seconds 600 [--min-shaded 20] [--maximize]

Why not fix the grid first: the obvious sampler (relabel a base grid, shuffle
rows within bands, swap bands and stacks, transpose) only walks one grid's
symmetry orbit, so it samples a single equivalence class out of the 5.47
billion and any ceiling it reports is an artefact. The grid has to be a
variable.

One model: a solved sudoku, shaded cell booleans, every shaded cell's digit equal to its
shaded-neighbour count (all visible), and flow connectivity. `--maximize` asks
for the largest connected shaded cell set that exists at all; `--min-shaded` asks for
a feasible one of at least that size, which is the question uniqueness needs
(uniqueness wants many givens).
"""

import argparse
import json
import time
from pathlib import Path

from harvest import SYMS
from ortools.sat.python import cp_model
from shapes import NEIGH, ORTH, count_solutions, givens


def images(shape):
    """The 8 dihedral images of a shape, as 81-bit indicator tuples."""
    out = []
    for f in SYMS:
        bits = [0] * 81
        for i in shape:
            nr, nc = f(*divmod(i, 9))
            bits[nr * 9 + nc] = 1
        out.append(tuple(bits))
    return out


def is_lex_min(shape):
    """Is this shape's indicator vector the smallest of its 8 images?

    Note this is lex order on the 81-bit INDICATOR, which is not the same
    ordering as harvest.canonical() (that one sorts cell indices). Either is a
    valid canonical form; they must not be mixed, and the model uses this one.
    """
    imgs = images(shape)
    return imgs[0] == min(imgs)


def add_flow_connectivity(m, g, cap=81):
    """One root shaded cell supplies a unit of flow to every other shaded cell.

    `cap` is the largest possible shaded cell count. Sizing the flow domains to it
    rather than to 81 matters: `joint.py --maximize` proves no connected
    all-visible shape exceeds 26 shaded cells, so 0..81 arcs hand the solver three
    times the range it can ever use.
    """
    root = [m.new_bool_var(f"r{i}") for i in range(81)]
    m.add_exactly_one(root)
    arcs = {}
    for i in range(81):
        m.add_implication(root[i], g[i])
        for j in ORTH[i]:
            f = m.new_int_var(0, cap, f"f{i}_{j}")
            m.add(f <= cap * g[i])
            m.add(f <= cap * g[j])
            arcs[i, j] = f
    for i in range(81):
        supply = m.new_int_var(0, cap, f"s{i}")
        m.add(supply <= cap * root[i])
        m.add(
            sum(arcs[j, i] for j in ORTH[i]) + supply
            == sum(arcs[i, j] for j in ORTH[i]) + g[i]
        )


def add_all_digits(m, v, g):
    """Every digit 1-8 appears on at least one shaded cell -- necessary for uniqueness.

    A sudoku whose givens omit two or more digits always has several solutions:
    take one, swap the two missing digits throughout, and relabelling gives
    another solution agreeing with every given. So a unique puzzle needs at
    least 8 distinct given digits. Here a shaded cell's digit is its neighbour count,
    so it lies in 1-8 and 9 can never appear -- which leaves no slack at all.
    All eight of 1-8 must be present.
    """
    for d in range(1, 9):
        shows_d = []
        for i in range(81):
            b = m.new_bool_var(f"d{i}_{d}")
            m.add_implication(b, g[i])
            m.add(v[i] == d).only_enforce_if(b)
            shows_d.append(b)
        m.add_bool_or(shows_d)


def _lex_leq(m, a, b, tag):
    """Post a <= b lexicographically, for equal-length lists of booleans."""
    eq = m.new_bool_var(f"eq{tag}_0")
    m.add(eq == 1)
    for k in range(len(a)):
        # while the prefixes agree, a[k] may not exceed b[k]
        m.add_bool_or([eq.Not(), a[k].Not(), b[k]])
        if k == len(a) - 1:
            break
        ne = m.new_bool_var(f"ne{tag}_{k}")
        m.add_bool_xor([a[k], b[k], ne.Not()])  # ne <=> a[k] != b[k]
        nxt = m.new_bool_var(f"eq{tag}_{k + 1}")
        m.add_implication(nxt, eq)
        m.add_implication(nxt, ne.Not())
        m.add_bool_or([nxt, eq.Not(), ne])  # eq and not ne => nxt
        eq = nxt


def add_symmetry_breaking(m, g):
    """Keep only the lexicographically smallest of each shape's 8 images.

    The symmetry group is the 8 dihedral images and nothing else: they preserve
    the sudoku houses AND both adjacencies -- king for counting, orthogonal for
    connectivity. Band and stack swaps preserve houses but scramble adjacency,
    and digit relabelling is not a symmetry here because digits are counts.

    NEVER combine this with pinned cells. Forcing a cell already picks an
    orientation, and demanding canonical form on top forbids real solutions.
    """
    for s, f in enumerate(SYMS[1:], start=1):
        image = [None] * 81
        for i in range(81):
            r, c = divmod(i, 9)
            nr, nc = f(r, c)
            image[nr * 9 + nc] = g[i]
        _lex_leq(m, g, image, f"s{s}")


def build(
    min_shaded,
    max_shaded,
    maximize,
    weights=None,
    connect=True,
    all_digits=False,
    force=(),
    ban=(),
    break_symmetry=False,
    latin=False,
):
    """`latin=True` drops the box constraint: the grid is a Latin square."""
    m = cp_model.CpModel()
    v = [m.new_int_var(1, 9, f"v{i}") for i in range(81)]
    for r in range(9):
        m.add_all_different([v[r * 9 + c] for c in range(9)])
        m.add_all_different([v[c * 9 + r] for c in range(9)])
    for br in range(3):
        for bc in range(3):
            if latin:
                break
            m.add_all_different(
                [v[(br * 3 + r) * 9 + bc * 3 + c] for r in range(3) for c in range(3)]
            )
    g = [m.new_bool_var(f"g{i}") for i in range(81)]
    for i in range(81):
        m.add(v[i] == sum(g[j] for j in NEIGH[i])).only_enforce_if(g[i])
    for i in force:
        m.add(g[i] == 1)
    for i in ban:
        m.add(g[i] == 0)
    m.add(sum(g) >= min_shaded)
    m.add(sum(g) <= max_shaded)
    if connect:
        add_flow_connectivity(m, g, cap=max_shaded)
    if all_digits:
        add_all_digits(m, v, g)
    if break_symmetry:
        if force or ban:
            raise ValueError(
                "symmetry breaking with pinned cells would forbid real solutions: "
                "a pin already fixes the orientation"
            )
        add_symmetry_breaking(m, g)
    if maximize:
        m.maximize(sum(g))
    elif weights is not None:
        # Random weights per solve, the diversity trick renbanana and
        # zombo_brainanas both landed on: solve-then-forbid moves one point at
        # a time and returns near-identical shapes, while a fresh random
        # objective lands somewhere else in the feasible set every time.
        m.maximize(sum(w * x for w, x in zip(weights, g, strict=True)))
    return m, v, g


def check_symmetry(trials):
    """The symmetry-breaking encoding vs an explicit enumeration of the 8 images.

    Also checks the property that makes it safe: exactly one shape per orbit is
    accepted, so no solution is lost -- only duplicates.
    """
    import random

    rng = random.Random(17)
    bad = kept = 0
    for _ in range(trials):
        n = rng.randint(1, 30)
        shape = set(rng.sample(range(81), n))
        m = cp_model.CpModel()
        g = [m.new_bool_var(f"g{i}") for i in range(81)]
        for i in range(81):
            m.add(g[i] == (1 if i in shape else 0))
        add_symmetry_breaking(m, g)
        s = cp_model.CpSolver()
        s.parameters.num_workers = 1
        s.parameters.max_time_in_seconds = 10
        got = s.solve(m) in (cp_model.OPTIMAL, cp_model.FEASIBLE)
        want = is_lex_min(shape)
        kept += got
        if got != want:
            bad += 1
            print(f"MISMATCH {sorted(shape)}: enumeration {want}, model {got}")
    print(f"symmetry breaking vs enumeration: {trials - bad}/{trials} agree")
    print(f"  {kept} of {trials} random shapes are canonical")

    # every orbit keeps exactly one representative
    orbits = 0
    for _ in range(200):
        shape = set(rng.sample(range(81), rng.randint(1, 20)))
        reps = sum(
            is_lex_min({p // 9 * 9 + p % 9 for p, b in enumerate(img) if b})
            for img in set(images(shape))
        )
        if reps != 1:
            print(f"ORBIT ERROR {sorted(shape)}: {reps} representatives, want 1")
            orbits += 1
    print(f"  orbit check: {200 - orbits}/200 orbits keep exactly one shape")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seconds", type=float, default=600)
    ap.add_argument("--min-shaded", type=int, default=1)
    ap.add_argument("--max-shaded", type=int, default=81)
    ap.add_argument("--maximize", action="store_true")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--out", type=Path)
    ap.add_argument("--check-symmetry", type=int, default=0)
    a = ap.parse_args()
    if a.check_symmetry:
        check_symmetry(a.check_symmetry)
        return
    t0 = time.monotonic()
    m, v, g = build(a.min_shaded, a.max_shaded, a.maximize)
    s = cp_model.CpSolver()
    s.parameters.num_workers = a.workers
    s.parameters.max_time_in_seconds = a.seconds
    s.parameters.log_search_progress = False
    st = s.solve(m)
    el = time.monotonic() - t0
    print(f"{s.status_name(st)} in {el:.1f}s (min {a.min_shaded}, max {a.max_shaded})")
    if st not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return
    shape = {i for i in range(81) if s.value(g[i])}
    grid = [s.value(x) for x in v]
    print(
        f"shaded cells {len(shape)}",
        "optimal" if st == cp_model.OPTIMAL else "feasible",
    )
    print("shape", sorted(shape))
    gv = givens(shape)
    print("admissible:", gv is not None)
    if gv is not None:
        print("sudoku solutions (cap 2):", count_solutions(gv, 2))
    for r in range(9):
        print(
            " ".join(
                f"({grid[r * 9 + c]})" if r * 9 + c in shape else f" {grid[r * 9 + c]} "
                for c in range(9)
            )
        )
    if a.out:
        with a.out.open("a") as fh:
            fh.write(json.dumps({"shape": sorted(shape), "grid": grid}) + "\n")


if __name__ == "__main__":
    main()
