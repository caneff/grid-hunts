"""Ghosts: hunt minimal clue sets whose digit solution is unique.

    uv run finders/ghosts/minimal.py --grids 20 --seed 1 --out DIR

Per grid: a random solution + ghost set with a visible ghost holding 8. Clues
are visible ghosts (circle, no digit) and given digits, weighted equally. The
8-ghost is always visible. Greedy removal to a minimal set: no single clue can
go without a second digit solution appearing. Hidden ghosts stay free.

One CP-SAT model per grid serves every uniqueness check: each potential clue
is an assumption literal, the model forbids the known digit solution, and an
INFEASIBLE answer returns an unsat core — every clue outside the core is
dropped at once.
"""

import argparse
import json
import random
import time
from pathlib import Path

from ortools.sat.python import cp_model

N = 9
CELLS = [(r, c) for r in range(N) for c in range(N)]


def neighbours(r, c):
    return [
        (r + a, c + b)
        for a in (-1, 0, 1)
        for b in (-1, 0, 1)
        if (a or b) and 0 <= r + a < N and 0 <= c + b < N
    ]


def base_model():
    m = cp_model.CpModel()
    x = {
        (r, c): [m.new_bool_var(f"x{r}{c}{d}") for d in range(1, 10)] for r, c in CELLS
    }
    g = {(r, c): m.new_bool_var(f"g{r}{c}") for r, c in CELLS}
    for cell in CELLS:
        m.add_exactly_one(x[cell])
    for d in range(9):
        for i in range(N):
            m.add_exactly_one(x[i, c][d] for c in range(N))
            m.add_exactly_one(x[r, i][d] for r in range(N))
        for br in (0, 3, 6):
            for bc in (0, 3, 6):
                m.add_exactly_one(
                    x[br + a, bc + b][d] for a in range(3) for b in range(3)
                )
    for r, c in CELLS:
        digit = sum((d + 1) * x[r, c][d] for d in range(9))
        m.add(sum(g[n] for n in neighbours(r, c)) == digit).only_enforce_if(g[r, c])
        m.add_bool_or([x[r, c][d].Not() for d in (8,)]).only_enforce_if(
            g[r, c]
        )  # no 9 on a ghost
    return m, x, g


def solver(seed, limit):
    s = cp_model.CpSolver()
    s.parameters.num_workers = 1
    s.parameters.random_seed = seed
    s.parameters.max_time_in_seconds = limit
    return s


def random_grid(rng, min_ghosts):
    m, x, g = base_model()
    eight = rng.choice(
        [
            cell
            for cell in CELLS
            if 0 < cell[0] < 8
            and 0 < cell[1] < 8
            and not (cell[0] % 3 == 1 and cell[1] % 3 == 1)
        ]
    )
    m.add(g[eight] == 1)
    m.add(x[eight][7] == 1)
    m.add(sum(g.values()) >= min_ghosts)
    for cell in CELLS:
        m.add_hint(x[cell][rng.randrange(9)], 1)
        m.add_hint(g[cell], rng.random() < 0.4)
    s = solver(rng.randrange(1 << 30), 60)
    s.parameters.randomize_search = True
    if s.solve(m) not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return None
    digits = {
        cell: next(d + 1 for d in range(9) if s.value(x[cell][d])) for cell in CELLS
    }
    ghosts = {cell for cell in CELLS if s.value(g[cell])}
    return digits, ghosts, eight


def minimise(rng, digits, ghosts, eight, stats):
    m, x, g = base_model()
    clue_lit = {}
    for cell in CELLS:
        lit = m.new_bool_var(f"given{cell}")
        m.add_implication(lit, x[cell][digits[cell] - 1])
        clue_lit[("digit", cell)] = lit
    for cell in ghosts:
        lit = m.new_bool_var(f"vis{cell}")
        m.add_implication(lit, g[cell])
        clue_lit[("ghost", cell)] = lit
    m.add(g[eight] == 1)  # the 8-ghost is visible: fixed, not removable
    m.add_bool_or(
        [x[cell][digits[cell] - 1].Not() for cell in CELLS]
    )  # a second solution
    lit_clue = {lit.index: key for key, lit in clue_lit.items()}

    def unique(active):
        m.clear_assumptions()
        m.add_assumptions([clue_lit[k] for k in active])
        s = solver(rng.randrange(1 << 30), 120)
        t = time.monotonic()
        st = s.solve(m)
        stats["checks"] += 1
        stats["check_s"] += time.monotonic() - t
        if st == cp_model.INFEASIBLE:
            return {lit_clue[i] for i in s.sufficient_assumptions_for_infeasibility()}
        if st == cp_model.UNKNOWN:
            raise RuntimeError("uniqueness check timed out")
        return None

    active = set(clue_lit)
    core = unique(active)
    assert core is not None, "full clue set must be unique"
    active = core
    necessary = set()
    order = list(active)
    rng.shuffle(order)
    for key in order:
        if key not in active or key in necessary:
            continue
        core = unique(active - {key})
        if core is None:
            necessary.add(key)
        else:
            active = core | necessary
    return sorted(active)


def verify(digits, eight, clues):
    """Fresh model, no assumptions: count digit solutions up to 2."""
    m, x, g = base_model()
    m.add(g[eight] == 1)
    for kind, cell in clues:
        if kind == "digit":
            m.add(x[cell][digits[cell] - 1] == 1)
        else:
            m.add(g[cell] == 1)
    s = solver(0, 300)
    assert s.solve(m) in (cp_model.OPTIMAL, cp_model.FEASIBLE)
    found = {
        cell: next(d + 1 for d in range(9) if s.value(x[cell][d])) for cell in CELLS
    }
    m.add_bool_or([x[cell][found[cell] - 1].Not() for cell in CELLS])
    return found == digits and s.solve(m) == cp_model.INFEASIBLE


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--grids", type=int, default=10)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--min-ghosts", type=int, default=9)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    rng = random.Random(a.seed)
    best = None
    for i in range(a.grids):
        t0 = time.monotonic()
        grid = random_grid(rng, a.min_ghosts)
        if grid is None:
            print(f"grid {i}: generation failed", flush=True)
            continue
        digits, ghosts, eight = grid
        stats = {"checks": 0, "check_s": 0.0}
        clues = minimise(rng, digits, ghosts, eight, stats)
        ok = verify(digits, eight, clues)
        n_digit = sum(k == "digit" for k, _ in clues)
        n_ghost = len(clues) - n_digit + 1  # + the fixed 8-ghost
        total = n_digit + n_ghost
        rec = {
            "grid": i,
            "seed": a.seed,
            "total": total,
            "digits_given": n_digit,
            "ghosts_visible": n_ghost,
            "ghosts_in_solution": len(ghosts),
            "eight": eight,
            "verified": ok,
            "checks": stats["checks"],
            "check_s": round(stats["check_s"], 2),
            "wall_s": round(time.monotonic() - t0, 2),
            "solution": [[digits[r, c] for c in range(N)] for r in range(N)],
            "ghosts": sorted(ghosts),
            "clues": [[k, list(cell)] for k, cell in clues] + [["ghost", list(eight)]],
        }
        with (a.out / "progress.jsonl").open("a") as f:
            f.write(json.dumps(rec) + "\n")
        print(
            f"grid {i}: total {total} (digits {n_digit}, ghosts {n_ghost}/{len(ghosts)}) "
            f"verified={ok} checks={stats['checks']} wall={rec['wall_s']}s",
            flush=True,
        )
        if ok and (best is None or total < best["total"]):
            best = rec
            (a.out / "best.json").write_text(json.dumps(rec, indent=1))
    print("best", best and best["total"])


if __name__ == "__main__":
    main()
