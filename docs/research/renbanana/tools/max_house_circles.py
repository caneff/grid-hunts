"""How many circles can one row, column or box carry at once?

A circle sits on a cell whose digit equals the size of its own maximal group,
chocolate or banana alike. This asks, for one named house, for the most circles
a legal grid can put in it, and for a ceiling that is a proof rather than a
sampling result.

The split is the repo's usual one, and it is the right one here because
**group size is a pure shading fact**: which cells are circle-*able* is decided
before a digit is placed.

Stage A -- shading only. Exact for rule 3 (no 2x2 window holds three chocolate
cells) and, unlike `Shadings`, exact for rule 4 as well: one clause per
rectangle placement forbidding "inside all banana, whole border chocolate", so
no cuts and no relaxation there. It measures each house cell's group size, and
counts a cell as circleable only when

  * its size is 1..9 -- a digit has to equal it;
  * the circled sizes in the house are pairwise distinct, since the house's
    digits are;
  * for a chocolate cell, the #377 catalogue allows a circle on that cell of
    that rectangle at that box offset (`circle_cells_at`). That kills the
    chocolate 5 and every uncircleable shape without a digit solve.

Every one of those is a necessary condition, so **stage A's optimum is an upper
bound on the answer**, and its INFEASIBLE at a level is a proof.

Stage B -- digits on a fixed shading: sudoku, the whisper, renban per banana
group, catalogue domains per rectangle, and `digit == group size` on the cells
stage A picked. A shading that survives it is a witness, re-checked by
`renbanana_verify`.

    uv run --with ortools docs/research/renbanana/tools/max_house_circles.py \
        --house row5 --seconds 900 --workers 6
"""

import argparse
import json
import sys
import time
from pathlib import Path

from ortools.sat.python import cp_model as cp

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import renbanana_cpsat as rc
import renbanana_verify as rv

N = 9
CELLS = rc.CELLS
IDX = rc.IDX
ADJACENT = rc.ADJACENT
MAX_BANANA = 9
PLACEMENTS = [
    (h, w, r0, c0)
    for h in range(1, N + 1)
    for w in range(1, N + 1)
    for r0 in range(N - h + 1)
    for c0 in range(N - w + 1)
]


def house(name):
    """Parse row3 / col7 / box1 (boxes in reading order, all 1-9) into cells."""
    kind, num = name[:3], int(name[3:]) - 1
    if kind == "row":
        return [(num, c) for c in range(N)]
    if kind == "col":
        return [(r, num) for r in range(N)]
    if kind == "box":
        br, bc = divmod(num, 3)
        return [(br * 3 + r, bc * 3 + c) for r in range(3) for c in range(3)]
    raise SystemExit(f"unknown house {name!r}")


def inside_of(h, w, r0, c0):
    return [(r0 + i, c0 + j) for i in range(h) for j in range(w)]


def border_of(h, w, r0, c0):
    inside = set(inside_of(h, w, r0, c0))
    return sorted({q for p in inside for q in rv.neighbours(*p) if q not in inside})


# ---------------------------------------------------------------- stage A


def shading_model(target):
    """The shading layer: legal shadings, sized house cells, circleable flags."""
    m = cp.CpModel()
    choc = {p: m.new_bool_var(f"c{p}") for p in CELLS}

    # Rule 3: every maximal chocolate group is a rectangle.
    for r in range(N - 1):
        for c in range(N - 1):
            m.add(
                choc[r, c] + choc[r, c + 1] + choc[r + 1, c] + choc[r + 1, c + 1] != 3
            )

    # Rule 4: no maximal banana group is a rectangle.
    for h, w, r0, c0 in PLACEMENTS:
        m.add_bool_or(
            [choc[p] for p in inside_of(h, w, r0, c0)]
            + [choc[q].negated() for q in border_of(h, w, r0, c0)]
        )

    # `rect[P]` <=> P is exactly a maximal chocolate group. Used for the
    # catalogue's circle-cell veto, and to rule out placements no grid can fill.
    rect = {}
    for P in PLACEMENTS:
        h, w, r0, c0 = P
        lits = [choc[p] for p in inside_of(h, w, r0, c0)] + [
            choc[q].negated() for q in border_of(h, w, r0, c0)
        ]
        v = m.new_bool_var(f"R{P}")
        for lit in lits:
            m.add_implication(v, lit)
        m.add_bool_or([v] + [lit.negated() for lit in lits])
        rect[P] = v
        if rc.fillings_at(h, w, r0 % 3, c0 % 3) == 0:
            m.add(v == 0)  # the catalogue proves no grid holds it there

    same = {}
    for p, q in ADJACENT:
        v = m.new_bool_var(f"s{p}{q}")
        m.add(choc[p] == choc[q]).only_enforce_if(v)
        m.add(choc[p] != choc[q]).only_enforce_if(v.negated())
        same[p, q] = same[q, p] = v

    size, circ, sel = {}, {}, {}
    for p in target:
        # Chocolate: the group is a rectangle, so its size is its placement's
        # area and the label machinery is not needed at all.
        choc_size = sum(
            h * w * rect[h, w, r0, c0]
            for h, w, r0, c0 in PLACEMENTS
            if p in inside_of(h, w, r0, c0)
        )

        # Banana: `mem` is p's group -- closed under same-colour adjacency, so
        # it holds the whole component, and walkable down to p by strictly
        # decreasing rank, so it holds nothing else. Rule 6 caps a banana group
        # at 9 cells, so the group lies inside p's Manhattan-8 disc and eight
        # ranks are enough.
        disc = [
            q for q in CELLS if abs(q[0] - p[0]) + abs(q[1] - p[1]) <= MAX_BANANA - 1
        ]
        mem = {q: m.new_bool_var(f"m{p}_{q}") for q in disc}
        rank = {q: m.new_int_var(0, MAX_BANANA - 1, f"k{p}_{q}") for q in disc}
        m.add(mem[p] + choc[p] == 1)
        m.add(rank[p] == 0)
        for q in disc:
            m.add_implication(mem[q], choc[p].negated())
            if q == p:
                continue
            m.add_implication(mem[q], choc[q].negated())
            steps = []
            for t in rv.neighbours(*q):
                if t not in mem:
                    continue
                z = m.new_bool_var(f"z{p}_{q}_{t}")
                m.add_implication(z, mem[t])
                m.add(rank[t] < rank[q]).only_enforce_if(z)
                steps.append(z)
            m.add_bool_or([mem[q].negated(), *steps])
        for q in disc:
            for t in rv.neighbours(*q):
                if t in mem:
                    m.add_bool_or([same[q, t].negated(), mem[q].negated(), mem[t]])
                else:
                    # Closure would leave the disc: only a group over 9 cells
                    # can do that, and rule 6 forbids one.
                    m.add_bool_or([same[q, t].negated(), mem[q].negated(), choc[q]])

        size[p] = m.new_int_var(1, len(CELLS), f"size{p}")
        m.add(size[p] == choc_size).only_enforce_if(choc[p])
        m.add(size[p] == sum(mem.values())).only_enforce_if(choc[p].negated())

        circ[p] = m.new_bool_var(f"circ{p}")
        picks = []
        for v in range(1, N + 1):
            b = m.new_bool_var(f"sel{p}_{v}")
            m.add(size[p] == v).only_enforce_if(b)
            picks.append(b)
            sel[p, v] = b
        m.add_bool_or([circ[p].negated(), *picks])
        for b in picks:
            m.add_implication(b, circ[p])

        # The catalogue's veto: on chocolate, a circle only sits where some
        # legal filling of that rectangle at that box offset puts its own area.
        for P in PLACEMENTS:
            h, w, r0, c0 = P
            if p not in inside_of(h, w, r0, c0):
                continue
            if (p[0] - r0, p[1] - c0) not in rc.circle_cells_at(h, w, r0 % 3, c0 % 3):
                m.add_bool_or([rect[P].negated(), choc[p].negated(), circ[p].negated()])

    # Redundant, and worth stating: two circled cells that touch would share a
    # group and so a size, and a house's circled sizes are distinct.
    for p in target:
        for q in target:
            if IDX[q] > IDX[p] and q in rv.neighbours(*p):
                m.add_bool_or(
                    [circ[p].negated(), circ[q].negated(), same[p, q].negated()]
                )

    # A house's digits are distinct, so its circled sizes are too.
    for v in range(1, N + 1):
        m.add(sum(sel[p, v] for p in target) <= 1)

    m.maximize(sum(circ.values()))
    return m, choc, size, circ


# ---------------------------------------------------------------- stage B


def digits_on(is_choc, target, level, seconds, workers):
    """Digits for a fixed shading carrying at least `level` circles in the
    house `target`. Stage A chose one circle set; the shading may prefer
    another, so the choice is left open here. Returns (grid, circles) or None.
    """
    m = cp.CpModel()
    d = {p: m.new_int_var(1, N, f"d{p}") for p in CELLS}
    for i in range(N):
        m.add_all_different([d[i, c] for c in range(N)])
        m.add_all_different([d[r, i] for r in range(N)])
    for br in range(3):
        for bc in range(3):
            m.add_all_different(
                [d[br * 3 + r, bc * 3 + c] for r in range(3) for c in range(3)]
            )
    for p, q in ADJACENT:
        if is_choc[p] and is_choc[q]:
            gap = m.new_int_var(-8, 8, f"g{p}{q}")
            m.add(gap == d[p] - d[q])
            a = m.new_int_var(0, 8, f"a{p}{q}")
            m.add_abs_equality(a, gap)
            m.add(a >= 5)
    size_of = {}
    for group in rv.components(is_choc, True):
        rows, cols = rv.shape(group)
        r0, c0 = min(group)
        sup = rc.support_at(rows, cols, r0 % 3, c0 % 3)
        if sup is None:
            return None
        for i in range(rows):
            for j in range(cols):
                m.add_allowed_assignments(
                    [d[r0 + i, c0 + j]], [(v,) for v in sup[i][j]]
                )
        for p in group:
            size_of[p] = len(group)
    for group in rv.components(is_choc, False):
        m.add_all_different([d[p] for p in group])
        lo = m.new_int_var(1, N, "lo")
        hi = m.new_int_var(1, N, "hi")
        m.add_min_equality(lo, [d[p] for p in group])
        m.add_max_equality(hi, [d[p] for p in group])
        m.add(hi - lo == len(group) - 1)
        for p in group:
            size_of[p] = len(group)

    hits = []
    for p in target:
        if size_of[p] > N:
            continue
        h = m.new_bool_var(f"h{p}")
        m.add(d[p] == size_of[p]).only_enforce_if(h)
        m.add(d[p] != size_of[p]).only_enforce_if(h.negated())
        hits.append((p, h))
    if len(hits) < level:
        return None
    m.add(sum(h for _, h in hits) >= level)

    sol = cp.CpSolver()
    sol.parameters.max_time_in_seconds = seconds
    sol.parameters.num_search_workers = workers
    if sol.solve(m) not in (cp.OPTIMAL, cp.FEASIBLE):
        return None
    grid = {p: sol.value(d[p]) for p in CELLS}
    return grid, sorted(p for p, h in hits if sol.value(h))


# ---------------------------------------------------------------- hunt


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--house", required=True)
    ap.add_argument(
        "--level",
        type=int,
        required=True,
        help="ask for this many circles in the house; UNSAT at stage A is a proof",
    )
    ap.add_argument("--seconds", type=float, default=900.0, help="stage A budget")
    ap.add_argument("--digit-seconds", type=float, default=60.0)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--tries", type=int, default=400, help="shadings to try")
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--progress", type=Path, default=None)
    args = ap.parse_args()

    target = house(args.house)
    tag = f"{args.house} k={args.level}"
    t0 = time.time()

    def say(text):
        print(text, flush=True)
        if args.progress:
            with args.progress.open("a") as fh:
                fh.write(text + "\n")

    m, choc, _size, circ = shading_model(target)
    m.add(sum(circ.values()) >= args.level)

    tried = 0
    while tried < args.tries:
        sol = cp.CpSolver()
        sol.parameters.max_time_in_seconds = max(1.0, args.seconds - (time.time() - t0))
        sol.parameters.num_search_workers = args.workers
        sol.parameters.randomize_search = True
        sol.parameters.random_seed = tried * 7919 + 13
        st = sol.solve(m)
        name = sol.status_name(st)
        if st not in (cp.OPTIMAL, cp.FEASIBLE):
            verdict = "IMPOSSIBLE (stage A proof)" if name == "INFEASIBLE" else name
            say(f"{tag}: {verdict} after {tried} shadings, {time.time() - t0:.0f}s")
            return
        tried += 1
        is_choc = {p: bool(sol.value(choc[p])) for p in CELLS}
        found = digits_on(is_choc, target, args.level, args.digit_seconds, args.workers)
        if found is not None:
            grid, want = found
            bad = rv.check(grid, is_choc, want)
            say(
                f"{tag}: WITNESS {len(want)} circles, shading {tried}, "
                f"{time.time() - t0:.0f}s, verify="
                f"{'LEGAL' if not bad else str(len(bad)) + ' VIOLATIONS'}"
            )
            if args.out:
                args.out.write_text(
                    json.dumps(
                        {
                            "house": args.house,
                            "circles_in_house": len(want),
                            "grid": [
                                "".join(str(grid[r, c]) for c in range(N))
                                for r in range(N)
                            ],
                            "shading": [
                                "".join("C" if is_choc[r, c] else "b" for c in range(N))
                                for r in range(N)
                            ],
                            "circles": [list(p) for p in want],
                            "violations": bad,
                        },
                        indent=1,
                    )
                    + "\n"
                )
            return
        # Digits refused this shading: forbid it and keep looking at this level.
        m.add_bool_or([choc[p].negated() if is_choc[p] else choc[p] for p in CELLS])
        if tried % 25 == 0:
            say(f"{tag}: {tried} shadings refused by digits, {time.time() - t0:.0f}s")
    say(f"{tag}: no witness in {tried} shadings, {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
