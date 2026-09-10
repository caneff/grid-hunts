"""Is a given *circle pattern* realisable? (brainstorm probe)

A circle marks a cell whose digit equals the size of its own maximal monochrome
group -- chocolate or banana, the colour is not given. This asks the joint
question the two-stage pipeline cannot: does *some* shading plus digit fill
satisfy all six Renbanana rules with every named cell circled?

Everything here is exact -- no lazy cuts -- so an INFEASIBLE is a proof.

- chocolate rectangles: the 2x2 window lemma (no window holds exactly 3).
- banana non-rectangle: every rectangle placement is forbidden outright as
  "all inside banana and the whole border chocolate" (2025 clauses).
- banana renban: component labels made *canonical* (a label's owner cell must
  itself carry that label), which is what the FEASIBILITY.md warning is about.
- circle sizes: per circled cell, a closure+rank encoding of its own component.

    uv run --with ortools probe_circle_pattern.py --cells r1c1,r1c3,... [--seconds N]
"""

import argparse
import json
import sys
from pathlib import Path

from ortools.sat.python import cp_model as cp

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import renbanana_verify as rv  # noqa: E402

N = 9
CELLS = [(r, c) for r in range(N) for c in range(N)]
IDX = {p: i for i, p in enumerate(CELLS)}
MAX_BANANA = 9


def neighbours(r, c):
    return [
        (a, b)
        for a, b in ((r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1))
        if 0 <= a < N and 0 <= b < N
    ]


ADJACENT = [(p, q) for p in CELLS for q in neighbours(*p) if IDX[q] > IDX[p]]


def parse_cells(text):
    out = []
    for tok in text.replace(" ", "").split(","):
        if not tok:
            continue
        r, c = tok.lower().lstrip("r").split("c")
        out.append((int(r) - 1, int(c) - 1))
    return out


def build(circled, choc_cells=(), ban_cells=(), givens=()):
    m = cp.CpModel()
    choc = {p: m.new_bool_var(f"c{p}") for p in CELLS}
    d = {p: m.new_int_var(1, 9, f"d{p}") for p in CELLS}
    eq = {(p, v): m.new_bool_var(f"e{p}_{v}") for p in CELLS for v in range(1, 10)}
    for p in CELLS:
        m.add_exactly_one(eq[p, v] for v in range(1, 10))
        for v in range(1, 10):
            m.add(d[p] == v).only_enforce_if(eq[p, v])
            m.add(d[p] != v).only_enforce_if(eq[p, v].negated())

    for i in range(N):
        m.add_all_different([d[i, c] for c in range(N)])
        m.add_all_different([d[r, i] for r in range(N)])
    for br in range(3):
        for bc in range(3):
            m.add_all_different(
                [d[br * 3 + r, bc * 3 + c] for r in range(3) for c in range(3)]
            )

    # Rule 3: chocolate components are rectangles.
    for r in range(N - 1):
        for c in range(N - 1):
            m.add(
                choc[r, c] + choc[r, c + 1] + choc[r + 1, c] + choc[r + 1, c + 1] != 3
            )

    # Rule 5: German Chocolate on chocolate adjacencies.
    for p, q in ADJACENT:
        both = m.new_bool_var("")
        m.add_bool_or([choc[p].negated(), choc[q].negated(), both])
        m.add_implication(both, choc[p])
        m.add_implication(both, choc[q])
        gap = m.new_int_var(-8, 8, "")
        m.add(gap == d[p] - d[q])
        ab = m.new_int_var(0, 8, "")
        m.add_abs_equality(ab, gap)
        m.add(ab >= 5).only_enforce_if(both)

    # Rule 4: no banana component is a rectangle. Forbid every placement of
    # "inside all banana, whole border chocolate" -- that pattern is exactly a
    # maximal banana rectangle.
    for r0 in range(N):
        for c0 in range(N):
            for h in range(1, N - r0 + 1):
                for w in range(1, N - c0 + 1):
                    lits = [choc[r0 + i, c0 + j] for i in range(h) for j in range(w)]
                    border = set()
                    for i in range(h):
                        border |= {(r0 + i, c0 - 1), (r0 + i, c0 + w)}
                    for j in range(w):
                        border |= {(r0 - 1, c0 + j), (r0 + h, c0 + j)}
                    lits += [
                        choc[p].negated()
                        for p in border
                        if 0 <= p[0] < N and 0 <= p[1] < N
                    ]
                    m.add_bool_or(lits)

    # Canonical banana component labels: a label's owner must carry it, so a
    # label is exactly one component (the unsoundness FEASIBILITY.md warns of).
    lab = {
        (p, e): m.new_bool_var(f"l{p}_{e}") for p in CELLS for e in range(IDX[p] + 1)
    }
    for p in CELLS:
        m.add(sum(lab[p, e] for e in range(IDX[p] + 1)) == 1 - choc[p])
        for e in range(IDX[p] + 1):
            owner = CELLS[e]
            m.add_implication(lab[p, e], lab[owner, e])
    for p, q in ADJACENT:
        lo, hi = (p, q) if IDX[p] < IDX[q] else (q, p)
        for e in range(IDX[lo] + 1):
            m.add_bool_or([choc[p], choc[q], lab[lo, e].negated(), lab[hi, e]])
        for e in range(IDX[lo] + 1, IDX[hi] + 1):
            m.add_bool_or([choc[p], choc[q], lab[hi, e].negated()])
    for e in range(len(CELLS)):
        m.add(sum(lab[p, e] for p in CELLS if IDX[p] >= e) <= MAX_BANANA)

    # Labels alone are NOT canonical: two disjoint components can both claim a
    # label whose owner sits in only one of them, which lets rule 6 leak. Pin
    # it with a rank chain -- every banana cell must reach its label's owner
    # through banana neighbours, so a label is exactly one component.
    brank = {p: m.new_int_var(0, MAX_BANANA - 1, f"br{p}") for p in CELLS}
    for p in CELLS:
        own = lab[p, IDX[p]]
        m.add(brank[p] == 0).only_enforce_if(own)
        picks = []
        for q in neighbours(*p):
            b = m.new_bool_var("")
            m.add_implication(b, choc[q].negated())
            m.add(brank[q] + 1 == brank[p]).only_enforce_if(b)
            picks.append(b)
        m.add_bool_or([choc[p], own, *picks])

    # Rule 6: renban per banana component, stated on the canonical labels.
    for e in range(len(CELLS)):
        members = [p for p in CELLS if IDX[p] >= e]
        has = {}
        for v in range(1, 10):
            hits = []
            for p in members:
                b = m.new_bool_var("")
                m.add_implication(b, lab[p, e])
                m.add_implication(b, eq[p, v])
                m.add_bool_or([lab[p, e].negated(), eq[p, v].negated(), b])
                hits.append(b)
            m.add(sum(hits) <= 1)  # distinct within the group
            hv = m.new_bool_var("")
            m.add_bool_or([hv.negated(), *hits])
            for b in hits:
                m.add_implication(b, hv)
            has[v] = hv
        for lo in range(1, 10):
            for hi in range(lo + 2, 10):
                for mid in range(lo + 1, hi):
                    m.add_bool_or(
                        [has[lo].negated(), has[hi].negated(), has[mid]]
                    )  # contiguous

    # The circles: digit == size of that cell's own component.
    for X in circled:
        same = {}
        for p in CELLS:
            s = m.new_bool_var("")
            m.add(choc[p] == choc[X]).only_enforce_if(s)
            m.add(choc[p] != choc[X]).only_enforce_if(s.negated())
            same[p] = s
        inn = {p: m.new_bool_var("") for p in CELLS}
        rank = {p: m.new_int_var(0, 8, "") for p in CELLS}
        m.add(inn[X] == 1)
        m.add(rank[X] == 0)
        for p in CELLS:
            m.add_implication(inn[p], same[p])
            for q in neighbours(*p):
                # closure: an in-cell drags in every same-coloured neighbour
                m.add_bool_or([inn[p].negated(), same[q].negated(), inn[q]])
            if p == X:
                continue
            picks = []
            for q in neighbours(*p):
                b = m.new_bool_var("")
                m.add_implication(b, inn[q])
                m.add(rank[q] + 1 == rank[p]).only_enforce_if(b)
                picks.append(b)
            m.add_bool_or([inn[p].negated(), *picks])  # rank: connected back to X
        m.add(d[X] == sum(inn.values()))
    for p_ in choc_cells:
        m.add(choc[p_] == 1)
    for p_ in ban_cells:
        m.add(choc[p_] == 0)
    for p_, v in givens:
        m.add(d[p_] == v)
    return m, choc, d


def render(grid, is_choc):
    return [
        " ".join(
            (f"[{grid[r, c]}]" if is_choc[r, c] else f" {grid[r, c]} ")
            for c in range(N)
        )
        for r in range(N)
    ]


def load_known(path):
    """Solutions already in hand, so a re-run never re-finds them.

    Takes a streamed solutions file (the format `--out` writes), a directory of
    `cand_*.json` pool candidates, or one such candidate file -- the shapes a
    previous run leaves behind. Returns (grid, is_choc) pairs.
    """
    src = Path(path)
    out = []
    if src.is_file() and src.suffix == ".json":
        # An --out file may also be named .json, so what says a file is a
        # candidate is that it parses as JSON carrying `grid` -- not the
        # suffix. Anything else falls through to the streamed parser below.
        try:
            candidate = "grid" in json.loads(src.read_text())
        except json.JSONDecodeError:
            candidate = False
        if candidate:
            grid, is_choc, _ = rv.load(src)
            return [(grid, is_choc)]
    if src.is_dir():
        for f in sorted(src.glob("cand_*.json")):
            dd = json.loads(f.read_text())
            out.append(
                (
                    {
                        (r, c): int(ch)
                        for r, row in enumerate(dd["grid"])
                        for c, ch in enumerate(row)
                    },
                    {
                        (r, c): ch == "C"
                        for r, row in enumerate(dd["shading"])
                        for c, ch in enumerate(row)
                    },
                )
            )
        return out
    for blk in src.read_text().split("--- ")[1:]:
        rows = [ln for ln in blk.split("\n")[1:] if ln.strip()][:N]
        if len(rows) != N:
            continue
        grid, is_choc = {}, {}
        for r, ln in enumerate(rows):
            for c in range(N):
                f = ln[c * 4 : c * 4 + 3]
                if len(f) < 3 or not f.strip("[] ").isdigit():
                    grid = {}
                    break
                grid[r, c] = int(f.strip("[] "))
                is_choc[r, c] = "[" in f
            if not grid:
                break
        if len(grid) == N * N:
            out.append((grid, is_choc))
    return out


def block(m, choc, d, grid, is_choc):
    """Forbid exactly this (digit grid, shading) pair, nothing else."""
    lits = [choc[p].negated() if is_choc[p] else choc[p] for p in CELLS]
    for p in CELLS:
        t = m.new_bool_var("")
        m.add(d[p] != grid[p]).only_enforce_if(t)
        m.add(d[p] == grid[p]).only_enforce_if(t.negated())
        lits.append(t)
    m.add_bool_or(lits)


def flag_complaint(a):
    """Why this flag combination cannot give an honest verdict, or None.

    Both cases would otherwise pass silently: `--known` blocks its pool out of
    the very model `--unique` proves on, so a real second solution sitting in
    that pool comes back INFEASIBLE and prints UNIQUE; `--known-solution` is
    read only under `--unique`, so elsewhere it is a no-op the operator paid a
    full budget for.
    """
    if a.unique and a.known:
        return (
            "--known blocks solutions out of the model, so --unique would call "
            "a blocked second solution a proof; use --known-solution instead"
        )
    if a.known_solution and not a.unique:
        return "--known-solution only means anything with --unique"
    if a.unique and a.enumerate:
        return "--unique and --enumerate are different runs; pick one"
    if a.unique and a.out:
        return "--unique writes no solutions file; --out belongs to --enumerate"
    return None


def clue_complaints(known, circled, choc_cells, ban_cells, givens):
    """Why this (grid, shading) is not a solution of *this* clue set.

    A solution the solver found satisfies the clues by construction; one read
    off disk does not. Blocking a point the model never contained leaves the
    second search INFEASIBLE for the wrong reason, and that prints a false
    UNIQUE -- so a mismatch has to stop the run, not narrow it.
    """
    grid, is_choc = known
    bad = list(rv.check(grid, is_choc, list(circled)))
    for p in choc_cells:
        if not is_choc[p]:
            bad.append(f"--choc r{p[0] + 1}c{p[1] + 1} is banana in the solution")
    for p in ban_cells:
        if is_choc[p]:
            bad.append(f"--ban r{p[0] + 1}c{p[1] + 1} is chocolate in the solution")
    for p, v in givens:
        if grid[p] != v:
            bad.append(
                f"--givens r{p[0] + 1}c{p[1] + 1}={v} but the solution has {grid[p]}"
            )
    return bad


def prove_unique(m, choc, d, circled, a, known=None):
    """Verdict on the clue set: one solution, more than one, or not proved.

    `known` is a (grid, is_choc) pair already on disk. Supplied, the first
    solve is skipped entirely -- it only ever rediscovers what we handed in --
    and the whole budget goes to the second-solution search, which is the part
    that actually proves anything.

    A timeout counts as NOT PROVED, never as unique -- anything that strips
    clues on the back of this must stay sound rather than lean, which is the
    stance `zombo_brainanas_cpsat.unique` takes for the same reason.

    The model is exact (no lazy cuts), so an INFEASIBLE second-solution search
    really is a proof that the first solution is the only one.

    Returns the verdict word, for a caller that wants it without the printout.
    """
    s = cp.CpSolver()
    s.parameters.num_workers = a.workers
    if known is None:
        s.parameters.max_time_in_seconds = a.seconds / 2
        st = s.solve(m)
        if st == cp.INFEASIBLE:
            print("verdict: NO SOLUTION -- the clue set is contradictory")
            return "NO SOLUTION"
        if st not in (cp.OPTIMAL, cp.FEASIBLE):
            print(
                f"verdict: NOT PROVED -- no first solution within {a.seconds / 2:.0f}s"
            )
            return "NOT PROVED"
        grid = {p: s.value(d[p]) for p in CELLS}
        is_choc = {p: bool(s.value(choc[p])) for p in CELLS}
        spent = s.wall_time
        print("first solution:")
    else:
        grid, is_choc = known
        spent = 0.0
        print("first solution (supplied -- first solve skipped):")
    bad = rv.check(grid, is_choc, circled)
    assert not bad, bad
    print("\n".join(render(grid, is_choc)))

    block(m, choc, d, grid, is_choc)
    s.parameters.max_time_in_seconds = a.seconds - spent
    st2 = s.solve(m)
    if st2 == cp.INFEASIBLE:
        print("verdict: UNIQUE (proved -- no second solution exists)")
        return "UNIQUE"
    if st2 in (cp.OPTIMAL, cp.FEASIBLE):
        g2 = {p: s.value(d[p]) for p in CELLS}
        c2 = {p: bool(s.value(choc[p])) for p in CELLS}
        bad = rv.check(g2, c2, circled)
        assert not bad, bad
        same_digits = all(g2[p] == grid[p] for p in CELLS)
        print(
            "verdict: NOT UNIQUE -- second solution found"
            + ("  (same digits, different shading)" if same_digits else "")
        )
        print("\n".join(render(g2, c2)))
        return "NOT UNIQUE"
    print(
        "verdict: NOT PROVED -- second-solution search returned "
        f"{s.status_name(st2)}"
    )
    return "NOT PROVED"


def enumerate_all(m, choc, d, circled, a):
    """Distinct (digit grid, shading) pairs, by blocking each one as it is
    found. `enumerate_all_solutions` cannot be used: it also enumerates the
    model's auxiliary variables, so one real solution comes back thousands of
    times."""
    s = cp.CpSolver()
    s.parameters.num_workers = a.workers
    sols, spent = [], 0.0
    # Stream, never buffer: a long enumeration must leave its results on disk
    # as it goes, so a kill or a timeout still hands back everything found.
    sink = open(a.out, "w", buffering=1) if a.out else None
    while len(sols) < a.enumerate and spent < a.seconds:
        s.parameters.max_time_in_seconds = a.seconds - spent
        st = s.solve(m)
        spent += s.wall_time
        if st not in (cp.OPTIMAL, cp.FEASIBLE):
            break
        grid = {p: s.value(d[p]) for p in CELLS}
        is_choc = {p: bool(s.value(choc[p])) for p in CELLS}
        bad = rv.check(grid, is_choc, circled)
        assert not bad, bad
        extra = [
            p
            for colour in (True, False)
            for g in rv.components(is_choc, colour)
            for p in g
            if grid[p] == len(g) and p not in set(circled)
        ]
        sols.append((grid, is_choc, sorted(extra)))
        head = f"--- solution {len(sols)}   after {spent:.0f}s" + (
            "" if not extra else "   extra size-reading cells: "
            + ",".join(f"r{q[0] + 1}c{q[1] + 1}" for q in sorted(extra))
        )
        body = "\n".join([head, *render(grid, is_choc)])
        if sink:
            print(body, file=sink, flush=True)
        print(f"  solution {len(sols)} at {spent:.0f}s", flush=True)
        block(m, choc, d, grid, is_choc)
    exhausted = len(sols) < a.enumerate and spent < a.seconds
    print(
        f"distinct solutions: {len(sols)}"
        + ("  (search exhausted -- this is all of them)" if exhausted else
           "  (cap or time limit hit -- there may be more)")
    )
    strict = [x for x in sols if not x[2]]
    print(f"of those, strict (no uncircled cell reads its group size): {len(strict)}")
    if sink:
        print(
            f"# {len(sols)} distinct solutions"
            + (" -- exhaustive" if exhausted else " -- cap or time limit hit"),
            file=sink,
            flush=True,
        )
        sink.close()
        print(f"written: {a.out}")
    print(f"wall {spent:.1f}s")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cells", required=True)
    ap.add_argument("--seconds", type=float, default=300)
    ap.add_argument("--workers", type=int, default=1)
    ap.add_argument("--choc", default="")
    ap.add_argument("--ban", default="")
    ap.add_argument("--givens", default="", help="r1c9=2,r2c7=1")
    ap.add_argument("--enumerate", type=int, default=0, help="list up to N solutions")
    ap.add_argument(
        "--known",
        default=None,
        help="a previous --out file or pool dir; those solutions are blocked "
        "up front, so this run only reports ones you do not already have",
    )
    ap.add_argument(
        "--known-solution",
        default=None,
        help="a solution already in hand (a cand_*.json, an --out file, or a "
        "pool dir -- its first entry is used); with --unique the first solve "
        "is skipped and the whole budget goes to the second-solution search",
    )
    ap.add_argument(
        "--unique",
        action="store_true",
        help="prove whether the clue set has exactly one solution",
    )
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    refusal = flag_complaint(a)
    if refusal:
        sys.exit(refusal)
    circled = parse_cells(a.cells)
    givens = []
    for tok in a.givens.replace(" ", "").split(","):
        if tok:
            cell, val = tok.split("=")
            givens.append((parse_cells(cell)[0], int(val)))
    choc_cells, ban_cells = parse_cells(a.choc), parse_cells(a.ban)
    m, choc, d = build(circled, choc_cells, ban_cells, givens)
    if a.known:
        blocked = load_known(a.known)
        for grid, is_choc in blocked:
            block(m, choc, d, grid, is_choc)
        print(f"blocked {len(blocked)} already-known solutions from {a.known}")
    if a.unique:
        seed = None
        if a.known_solution:
            found = load_known(a.known_solution)
            if not found:
                sys.exit(f"no solution found in {a.known_solution}")
            seed = found[0]
            unmet = clue_complaints(seed, circled, choc_cells, ban_cells, givens)
            if unmet:
                sys.exit(
                    f"{a.known_solution} does not solve this clue set:\n  "
                    + "\n  ".join(unmet)
                )
        return prove_unique(m, choc, d, circled, a, known=seed)
    if a.enumerate:
        return enumerate_all(m, choc, d, circled, a)
    s = cp.CpSolver()
    s.parameters.max_time_in_seconds = a.seconds
    s.parameters.num_workers = a.workers
    s.parameters.log_search_progress = False
    st = s.solve(m)
    name = s.status_name(st)
    print(f"status: {name}")
    if st in (cp.OPTIMAL, cp.FEASIBLE):
        grid = {p: s.value(d[p]) for p in CELLS}
        is_choc = {p: bool(s.value(choc[p])) for p in CELLS}
        for r in range(N):
            print(
                " ".join(
                    (f"[{grid[r, c]}]" if is_choc[r, c] else f" {grid[r, c]} ")
                    for c in range(N)
                )
            )
        ok = rv.check(grid, is_choc, circled)
        print("verify:", ok)
        for X in circled:
            comp = [g for g in rv.components(is_choc, is_choc[X]) if X in g][0]
            print(
                f"  r{X[0]+1}c{X[1]+1} digit={grid[X]} size={len(comp)} "
                f"{'choc' if is_choc[X] else 'ban'}"
            )
    print(f"wall {s.wall_time:.1f}s")


if __name__ == "__main__":
    main()
