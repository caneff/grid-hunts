"""Counting-shaded shape enumeration on an N x N sudoku with any box shape.

    uv run finders/counting_shaded/gridenum.py --n 6 --box-rows 2 --box-cols 3 --size 12 --symmetry --out DIR

The 9x9 tools (`shapeenum.py`, the C counter) are hardwired to 81 cells. This
is the same shape-only native enumeration for a small grid: counts 1..N on
shaded cells (a shaded cell's digit is its shaded king-neighbour count, so a
count above N kills the shape), distinct within every row, column and box,
orthogonal connectivity by exact BFS distance from the lowest shaded cell,
pins, and at least N-1 distinct counts on the shape (a sudoku whose givens
omit two digits is never unique; Chris: "just 5 distinct" on a 6x6). Each
shape is judged by a bitmask DFS counter at cap 2: 0 grids complete it, 1
(unique), or 2+.

Symmetry breaking keeps the lexicographically smallest image under the
dihedral maps that preserve the box tiling: all 8 for square boxes, 4 for
rectangular ones (identity, half turn, the two axis flips). Never with pins.
"""

import argparse
import json
import time
from pathlib import Path

from joint import _lex_leq
from ortools.sat.python import cp_model

N = 6
BR, BC = 2, 3
LATIN = False  # rows and columns only, no boxes; set by --latin
SELF = False  # a shaded cell counts itself too (digit = neighbours + 1); --self
CELLS = NEIGH = ORTH = BOX = None


def geometry(n, br, bc):
    global N, BR, BC, CELLS, NEIGH, ORTH, BOX
    N, BR, BC = n, br, bc
    assert br * bc == n, "box must hold N cells"
    CELLS = [divmod(i, n) for i in range(n * n)]
    BOX = [(r // br) * (n // bc) + c // bc for r, c in CELLS]
    NEIGH, ORTH = [], []
    for r, c in CELLS:
        king, orth = [], []
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                if (dr or dc) and 0 <= r + dr < n and 0 <= c + dc < n:
                    king.append((r + dr) * n + c + dc)
                    if dr == 0 or dc == 0:
                        orth.append((r + dr) * n + c + dc)
        NEIGH.append(king)
        ORTH.append(orth)


def same_house(i, j):
    return (
        CELLS[i][0] == CELLS[j][0]
        or CELLS[i][1] == CELLS[j][1]
        or (not LATIN and BOX[i] == BOX[j])
    )


def symmetries():
    n = N
    maps = [
        lambda r, c: (n - 1 - r, n - 1 - c),
        lambda r, c: (n - 1 - r, c),
        lambda r, c: (r, n - 1 - c),
    ]
    if LATIN or BR == BC:
        maps += [
            lambda r, c: (c, r),
            lambda r, c: (n - 1 - c, n - 1 - r),
            lambda r, c: (c, n - 1 - r),
            lambda r, c: (n - 1 - c, r),
        ]
    return maps


def _reify_eq(m, expr, value, name):
    b = m.new_bool_var(name)
    m.add(expr == value).only_enforce_if(b)
    m.add(expr != value).only_enforce_if(b.Not())
    return b


def add_connectivity(m, g, size, tag):
    """g's true cells are orthogonally connected: exact BFS distance from the
    lowest true cell, so every helper is a function of g."""
    nn = N * N
    pre = [m.new_bool_var(f"{tag}pre{i}") for i in range(nn)]
    m.add(pre[0] == 0)
    for i in range(1, nn):
        m.add_max_equality(pre[i], [pre[i - 1], g[i - 1]])
    root = [m.new_bool_var(f"{tag}root{i}") for i in range(nn)]
    for i in range(nn):
        m.add_min_equality(root[i], [g[i], pre[i].Not()])
    d = [m.new_int_var(0, size, f"{tag}d{i}") for i in range(nn)]
    for i in range(nn):
        m.add(d[i] == 0).only_enforce_if(g[i].Not())
        m.add(d[i] == 0).only_enforce_if(root[i])
        m.add(d[i] >= 1).only_enforce_if([g[i], root[i].Not()])
        steps = []
        for j in ORTH[i]:
            m.add(d[i] <= d[j] + 1).only_enforce_if([g[i], g[j]])
            e = _reify_eq(m, d[i] - d[j], 1, f"{tag}e{i}_{j}")
            q = m.new_bool_var(f"{tag}q{i}_{j}")
            m.add_min_equality(q, [g[i], g[j], e])
            steps.append(q)
        m.add_bool_or([*steps, g[i].Not(), root[i]])


def build(
    size,
    force=(),
    ban=(),
    symmetry=False,
    unshaded_connected=False,
    no_2x2=False,
    min_distinct=None,
):
    """Every auxiliary variable is a function of the shape: one assignment per shape."""
    nn = N * N
    m = cp_model.CpModel()
    g = [m.new_bool_var(f"g{i}") for i in range(nn)]
    n = [m.new_int_var(0, 9, f"n{i}") for i in range(nn)]
    for i in range(nn):
        m.add(n[i] == sum(g[j] for j in NEIGH[i]) + (g[i] if SELF else 0))
        m.add(n[i] >= 1).only_enforce_if(g[i])
        m.add(n[i] <= N).only_enforce_if(g[i])
        for j in range(i + 1, nn):
            if same_house(i, j):
                m.add(n[i] != n[j]).only_enforce_if([g[i], g[j]])
    for i in force:
        m.add(g[i] == 1)
    for i in ban:
        m.add(g[i] == 0)
    m.add(sum(g) == size)

    add_connectivity(m, g, size, "s")
    if unshaded_connected:
        add_connectivity(m, [x.Not() for x in g], nn - size, "u")
    if no_2x2:
        for r in range(N - 1):
            for c in range(N - 1):
                block = [
                    g[r * N + c],
                    g[r * N + c + 1],
                    g[(r + 1) * N + c],
                    g[(r + 1) * N + c + 1],
                ]
                m.add_bool_or([x.Not() for x in block])
                m.add_bool_or(block)

    # at least N-1 distinct counts on the shape (Chris: "just 5 distinct" on a 6x6)
    present = []
    for v in range(1, N + 1):
        shows = []
        for i in range(nn):
            e = _reify_eq(m, n[i], v, f"n{i}is{v}")
            b = m.new_bool_var(f"show{v}_{i}")
            m.add_min_equality(b, [g[i], e])
            shows.append(b)
        p = m.new_bool_var(f"present{v}")
        m.add_max_equality(p, shows)
        present.append(p)
    m.add(sum(present) >= (N - 1 if min_distinct is None else min_distinct))

    if symmetry:
        if force or ban:
            raise ValueError("symmetry breaking with pins forbids real shapes")
        for s, f in enumerate(symmetries(), start=1):
            image = [None] * nn
            for i in range(nn):
                r, c = CELLS[i]
                nr, nc = f(r, c)
                image[nr * N + nc] = g[i]
            _lex_leq(m, g, image, f"s{s}")
    return m, g, n


def count(givens, cap=2):
    """Number of N x N sudoku grids agreeing with givens {cell: digit}, up to cap."""
    nn = N * N
    full = (1 << N) - 1
    rowm = [0] * N
    colm = [0] * N
    boxm = [0] * (N)
    grid = [0] * nn
    for i, v in givens.items():
        b = 1 << (v - 1)
        r, c = CELLS[i]
        bx = BOX[i]
        if rowm[r] & b or colm[c] & b or boxm[bx] & b:
            return 0
        rowm[r] |= b
        colm[c] |= b
        if not LATIN:
            boxm[bx] |= b
        grid[i] = v
    empty = [i for i in range(nn) if not grid[i]]
    found = 0

    def rec():
        nonlocal found
        best, bi = 99, -1
        for i in empty:
            if grid[i]:
                continue
            r, c = CELLS[i]
            cand = full & ~(rowm[r] | colm[c] | boxm[BOX[i]])
            k = bin(cand).count("1")
            if k < best:
                best, bi = k, i
                if k <= 1:
                    break
        if bi < 0:
            found += 1
            return
        if best == 0:
            return
        r, c = CELLS[bi]
        cand = full & ~(rowm[r] | colm[c] | boxm[BOX[bi]])
        while cand and found < cap:
            b = cand & -cand
            cand ^= b
            rowm[r] |= b
            colm[c] |= b
            if not LATIN:
                boxm[BOX[bi]] |= b
            grid[bi] = 1
            rec()
            grid[bi] = 0
            rowm[r] ^= b
            colm[c] ^= b
            if not LATIN:
                boxm[BOX[bi]] ^= b

    rec()
    return found


class _Collector(cp_model.CpSolverSolutionCallback):
    def __init__(self, g, n, size, out, log, t0):
        super().__init__()
        self.g, self.n, self.size, self.out, self.log, self.t0 = (
            g,
            n,
            size,
            out,
            log,
            t0,
        )
        self.shapes = self.solvable = self.unique = 0
        self.seen = set()

    def on_solution_callback(self):
        nn = N * N
        shape = frozenset(i for i in range(nn) if self.value(self.g[i]))
        if shape in self.seen:
            self.log(f"DUPLICATE shape returned by native enumeration: {sorted(shape)}")
            return
        self.seen.add(shape)
        self.shapes += 1
        givens = {i: self.value(self.n[i]) for i in shape}
        k = count(givens, 2)
        if k >= 1:
            self.solvable += 1
            with (self.out / "solvable.jsonl").open("a") as fh:
                fh.write(
                    json.dumps(
                        {
                            "n": N,
                            "box": [BR, BC],
                            "shaded": self.size,
                            "shape": sorted(shape),
                            "digits": [givens[i] for i in sorted(shape)],
                            "solutions": k,
                        }
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
    size,
    force,
    ban,
    seconds,
    out,
    log,
    symmetry,
    unshaded_connected=False,
    no_2x2=False,
):
    m, g, n = build(size, force, ban, symmetry, unshaded_connected, no_2x2)
    s = cp_model.CpSolver()
    s.parameters.num_workers = 1
    s.parameters.enumerate_all_solutions = True
    s.parameters.max_time_in_seconds = seconds
    t0 = time.monotonic()
    cb = _Collector(g, n, size, out, log, t0)
    st = s.solve(m, cb)
    status = "exhausted" if st in (cp_model.OPTIMAL, cp_model.INFEASIBLE) else "timeout"
    word = (
        "EXHAUSTED" if status == "exhausted" else f"{s.status_name(st)}: NOT exhausted"
    )
    log(
        f"{word} size {size} ({N}x{N} box {BR}x{BC}{', symmetry' if symmetry else ''}): "
        f"{cb.shapes} shapes, {cb.solvable} solvable, {cb.unique} unique "
        f"({time.monotonic() - t0:.0f}s)"
    )
    return status, cb.shapes, cb.solvable, cb.unique


def parse_cells(text):
    return tuple(int(x) for x in text.split(",")) if text else ()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=6)
    ap.add_argument("--box-rows", type=int, default=2)
    ap.add_argument("--box-cols", type=int, default=3)
    ap.add_argument("--size", type=int, required=True)
    ap.add_argument("--force", default="")
    ap.add_argument("--ban", default="")
    ap.add_argument("--symmetry", action="store_true")
    ap.add_argument("--latin", action="store_true", help="no boxes: Latin square")
    ap.add_argument(
        "--self", action="store_true", help="shaded digit counts itself too"
    )
    ap.add_argument(
        "--unshaded-connected", action="store_true", help="unshaded cells connected too"
    )
    ap.add_argument(
        "--no-2x2", action="store_true", help="no 2x2 block all shaded or all unshaded"
    )
    ap.add_argument("--seconds", type=float, default=3600)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    geometry(a.n, a.box_rows, a.box_cols)
    global LATIN, SELF
    LATIN = a.latin
    SELF = a.self
    a.out.mkdir(parents=True, exist_ok=True)
    force, ban = parse_cells(a.force), parse_cells(a.ban)
    progress = a.out / "progress.log"

    def log(msg):
        line = f"{time.strftime('%H:%M:%S')} {msg}"
        print(line, flush=True)
        with progress.open("a") as fh:
            fh.write(line + "\n")

    log(
        f"enumerate {a.n}x{a.n} box {a.box_rows}x{a.box_cols} size {a.size} "
        f"force={force} ban={ban} symmetry={a.symmetry} "
        f"unshaded_connected={a.unshaded_connected} no_2x2={a.no_2x2} latin={a.latin} self={a.self}"
    )
    enumerate_native(
        a.size,
        force,
        ban,
        a.seconds,
        a.out,
        log,
        a.symmetry,
        a.unshaded_connected,
        a.no_2x2,
    )


if __name__ == "__main__":
    main()
