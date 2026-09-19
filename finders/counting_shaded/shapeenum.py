"""Enumerate connected shapes of one size, shape-only, and let the counter judge.

    uv run finders/counting_shaded/shapeenum.py --size 21 [--force 72,73] [--ban 57] --out DIR

Faster than `pinharvest.py --enumerate` by leaving the digits out of the CP-SAT
model. The model holds only the shape: counts 1-8 on shaded cells, distinct
within every row, column and box, flow connectivity, pins, and all eight of
1-8 present. Every shape it returns is then classified by the C counter in
under a millisecond: 0 sudoku solutions (no grid completes it), 1 (unique), or
2+. Solve-then-forbid until INFEASIBLE, which exhausts the size.

The old lesson that a shape-only search "cannot see solvability" still holds;
it does not need to. The counter is the solvability check, and it is cheaper
than carrying 81 digit variables through every solve.
"""

import argparse
import json
import time
from pathlib import Path

import fastclimb
from fastclimb import count, pins
from joint import add_flow_connectivity, add_symmetry_breaking
from ortools.sat.python import cp_model
from shapes import BOX, CELLS, NEIGH, ORTH

LATIN = False  # rows and columns only; set by --latin, mirrored into the C counter


def same_house(i, j):
    return (
        CELLS[i][0] == CELLS[j][0]
        or CELLS[i][1] == CELLS[j][1]
        or (not LATIN and BOX[i] == BOX[j])
    )


def build(size, force=(), ban=(), all_digits=True):
    m = cp_model.CpModel()
    g = [m.new_bool_var(f"g{i}") for i in range(81)]
    n = [m.new_int_var(0, 8, f"n{i}") for i in range(81)]
    for i in range(81):
        m.add(n[i] == sum(g[j] for j in NEIGH[i]))
        m.add(n[i] >= 1).only_enforce_if(g[i])
        for j in range(i + 1, 81):
            if same_house(i, j):
                m.add(n[i] != n[j]).only_enforce_if([g[i], g[j]])
    for i in force:
        m.add(g[i] == 1)
    for i in ban:
        m.add(g[i] == 0)
    m.add(sum(g) == size)
    add_flow_connectivity(m, g, cap=size)
    if all_digits:
        for d in range(1, 9):
            shows = []
            for i in range(81):
                b = m.new_bool_var(f"d{d}_{i}")
                m.add_implication(b, g[i])
                m.add(n[i] == d).only_enforce_if(b)
                shows.append(b)
            m.add_bool_or(shows)
    return m, g


def _reify_eq(m, expr, value, name):
    """A boolean that is true exactly when expr == value."""
    b = m.new_bool_var(name)
    m.add(expr == value).only_enforce_if(b)
    m.add(expr != value).only_enforce_if(b.Not())
    return b


def build_determined(size, force=(), ban=(), all_digits=True, symmetry=False):
    """The same shape model, but every auxiliary variable is a function of the shape.

    Native enumeration (`enumerate_all_solutions`) walks distinct assignments of
    ALL variables, so a flow encoding would return one shape once per spanning
    flow. Here connectivity is exact breadth-first distance from the root, the
    root being the lowest-index shaded cell, and every reified boolean is
    two-sided. One assignment per shape.
    """
    m = cp_model.CpModel()
    g = [m.new_bool_var(f"g{i}") for i in range(81)]
    n = [m.new_int_var(0, 8, f"n{i}") for i in range(81)]
    for i in range(81):
        m.add(n[i] == sum(g[j] for j in NEIGH[i]))
        m.add(n[i] >= 1).only_enforce_if(g[i])
        for j in range(i + 1, 81):
            if same_house(i, j):
                m.add(n[i] != n[j]).only_enforce_if([g[i], g[j]])
    for i in force:
        m.add(g[i] == 1)
    for i in ban:
        m.add(g[i] == 0)
    m.add(sum(g) == size)

    # root = lowest-index shaded cell; pre[i] = some cell before i is shaded
    pre = [m.new_bool_var(f"pre{i}") for i in range(81)]
    m.add(pre[0] == 0)
    for i in range(1, 81):
        m.add_max_equality(pre[i], [pre[i - 1], g[i - 1]])
    root = [m.new_bool_var(f"root{i}") for i in range(81)]
    for i in range(81):
        m.add_min_equality(root[i], [g[i], pre[i].Not()])
    # d = BFS distance from the root over shaded orthogonal steps; 0 off the shape
    d = [m.new_int_var(0, size, f"d{i}") for i in range(81)]
    for i in range(81):
        m.add(d[i] == 0).only_enforce_if(g[i].Not())
        m.add(d[i] == 0).only_enforce_if(root[i])
        m.add(d[i] >= 1).only_enforce_if([g[i], root[i].Not()])
        steps = []
        for j in ORTH[i]:
            m.add(d[i] <= d[j] + 1).only_enforce_if([g[i], g[j]])
            e = _reify_eq(m, d[i] - d[j], 1, f"e{i}_{j}")
            q = m.new_bool_var(f"q{i}_{j}")
            m.add_min_equality(q, [g[i], g[j], e])
            steps.append(q)
        m.add_bool_or([*steps, g[i].Not(), root[i]])
    if all_digits:
        for v in range(1, 9):
            shows = []
            for i in range(81):
                e = _reify_eq(m, n[i], v, f"n{i}is{v}")
                b = m.new_bool_var(f"show{v}_{i}")
                m.add_min_equality(b, [g[i], e])
                shows.append(b)
            m.add_bool_or(shows)
    if symmetry:
        if force or ban:
            raise ValueError("symmetry breaking with pins forbids real shapes")
        add_symmetry_breaking(m, g)
    return m, g


class _Collector(cp_model.CpSolverSolutionCallback):
    def __init__(self, g, size, out, log, t0):
        super().__init__()
        self.g, self.size, self.out, self.log, self.t0 = g, size, out, log, t0
        self.shapes = self.solvable = self.unique = 0
        self.seen = set()

    def on_solution_callback(self):
        shape = frozenset(i for i in range(81) if self.value(self.g[i]))
        if shape in self.seen:
            self.log(f"DUPLICATE shape returned by native enumeration: {sorted(shape)}")
            return
        self.seen.add(shape)
        self.shapes += 1
        k = count(set(shape), 2)
        if k >= 1:
            self.solvable += 1
            with (self.out / "solvable.jsonl").open("a") as fh:
                fh.write(
                    json.dumps(
                        {"shaded": self.size, "shape": sorted(shape), "solutions": k}
                    )
                    + "\n"
                )
        if k == 1:
            self.unique += 1
            self.log(f"UNIQUE {self.size}: {sorted(shape)}")
        if self.shapes % 100 == 0:
            self.log(
                f"size {self.size}: {self.shapes} shapes, {self.solvable} solvable, "
                f"{self.unique} unique ({time.monotonic() - self.t0:.0f}s)"
            )


def enumerate_native(
    size, force, ban, seconds, out, log, all_digits=True, symmetry=False
):
    """One continuous search, single worker. Returns (status, shapes, solvable, unique)."""
    m, g = build_determined(size, force, ban, all_digits, symmetry)
    s = cp_model.CpSolver()
    s.parameters.num_workers = 1
    s.parameters.enumerate_all_solutions = True
    s.parameters.max_time_in_seconds = seconds
    t0 = time.monotonic()
    cb = _Collector(g, size, out, log, t0)
    st = s.solve(m, cb)
    status = "exhausted" if st in (cp_model.OPTIMAL, cp_model.INFEASIBLE) else "timeout"
    word = (
        "EXHAUSTED" if status == "exhausted" else f"{s.status_name(st)}: NOT exhausted"
    )
    log(
        f"{word} size {size} (native{', symmetry' if symmetry else ''}): {cb.shapes} shapes, "
        f"{cb.solvable} solvable, {cb.unique} unique ({time.monotonic() - t0:.0f}s)"
    )
    return status, cb.shapes, cb.solvable, cb.unique


def enumerate_size(size, force, ban, seconds, workers, out, log, all_digits=True):
    """Returns (status, shapes, solvable, unique)."""
    m, g = build(size, force, ban, all_digits)
    s = cp_model.CpSolver()
    s.parameters.num_workers = workers
    t0 = time.monotonic()
    shapes = solvable = unique = 0
    while True:
        left = seconds - (time.monotonic() - t0)
        if left <= 1:
            log(
                f"time up: size {size} NOT exhausted; {shapes} shapes, {solvable} solvable, {unique} unique"
            )
            return "timeout", shapes, solvable, unique
        s.parameters.max_time_in_seconds = left
        st = s.solve(m)
        if st == cp_model.INFEASIBLE:
            log(
                f"EXHAUSTED size {size}: {shapes} shapes, {solvable} solvable, "
                f"{unique} unique ({time.monotonic() - t0:.0f}s)"
            )
            return "exhausted", shapes, solvable, unique
        if st not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            log(f"{s.status_name(st)}: size {size} NOT exhausted after {shapes} shapes")
            return "timeout", shapes, solvable, unique
        shape = {i for i in range(81) if s.value(g[i])}
        shapes += 1
        k = count(shape, 2)
        if k >= 1:
            solvable += 1
            with (out / "solvable.jsonl").open("a") as fh:
                fh.write(
                    json.dumps({"shaded": size, "shape": sorted(shape), "solutions": k})
                    + "\n"
                )
        if k == 1:
            unique += 1
            log(f"UNIQUE {size}: {sorted(shape)}")
        m.add_bool_or(
            [g[i].Not() for i in shape] + [g[i] for i in range(81) if i not in shape]
        )
        if shapes % 100 == 0:
            log(
                f"size {size}: {shapes} shapes, {solvable} solvable, {unique} unique ({time.monotonic() - t0:.0f}s)"
            )


def parse_cells(text):
    return tuple(int(x) for x in text.split(",")) if text else ()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--size", type=int, required=True)
    ap.add_argument("--force", default="")
    ap.add_argument("--ban", default="")
    ap.add_argument("--no-all-digits", action="store_true")
    ap.add_argument(
        "--mode",
        choices=["forbid", "native"],
        default="native",
        help="native: one continuous single-worker enumeration; forbid: solve-then-forbid",
    )
    ap.add_argument(
        "--symmetry", action="store_true", help="keep one of 8 images (no pins)"
    )
    ap.add_argument(
        "--latin", action="store_true", help="Latin square: no box constraint"
    )
    ap.add_argument("--seconds", type=float, default=600)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    force, ban = parse_cells(a.force), parse_cells(a.ban)
    pins(force, ban)
    global LATIN
    LATIN = a.latin
    fastclimb.latin(a.latin)
    progress = a.out / "progress.log"

    def log(msg):
        line = f"{time.strftime('%H:%M:%S')} {msg}"
        print(line, flush=True)
        with progress.open("a") as fh:
            fh.write(line + "\n")

    log(
        f"shape-only enumerate size {a.size} force={force} ban={ban} mode={a.mode} "
        f"symmetry={a.symmetry} latin={a.latin} workers={a.workers}"
    )
    if a.mode == "native":
        enumerate_native(
            a.size, force, ban, a.seconds, a.out, log, not a.no_all_digits, a.symmetry
        )
    else:
        enumerate_size(
            a.size, force, ban, a.seconds, a.workers, a.out, log, not a.no_all_digits
        )


if __name__ == "__main__":
    main()
