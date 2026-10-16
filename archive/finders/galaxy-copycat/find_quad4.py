"""Find four (2,2) 4-cell lines whose 2+2 pairing is deducible and whose grid
is unique.

Usage: uv run find_quad4.py board.json pairs.jsonl out.jsonl [--seed forced.json]
         [--shard i/n] [--shape 2,2]
  pairs.jsonl: feasible pairs from find_pair4 (its .lines.jsonl must sit beside it)
Candidates: two cell-disjoint feasible pairs; the 4-set is keyed once and the
number of catalogue-feasible matchings (1..3) recorded.  Per 4-set a CP-SAT
model with a matching variable (AB|CD, AC|BD, AD|BC, exactly one) and the pair
constraint enforced under it.  Reported per row:
  n          solutions over (digits, flags, matching), capped at 3
  matchings  matchings that admit a solution (list of "AB|CD" style keys)
  coincide   in the found solution, other matchings that also happen to hold
  values     the four lines' values in the first solution
Wanted rows: n == 1 and len(matchings) == 1 and coincide == [].
"""

import argparse
import json
import sys
import time
from itertools import combinations
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from copycat_rsl_solver import build, parse_cell
from ortools.sat.python import cp_model

ap = argparse.ArgumentParser()
ap.add_argument("board")
ap.add_argument("pairs")
ap.add_argument("out")
ap.add_argument("--seed")
ap.add_argument("--shape", default="2,2")
ap.add_argument("--shard", default="0/1")
args = ap.parse_args()
base = json.loads(Path(args.board).read_text())
SEED = json.loads(Path(args.seed).read_text()) if args.seed else {}
shape = tuple(int(x) for x in args.shape.split(","))
lines_file = Path(args.pairs.replace(".pairs.jsonl", ".lines.jsonl"))
STRUCT = {
    r["cells"]: tuple(r["struct"])
    for r in map(json.loads, lines_file.read_text().splitlines())
}
pairs = [
    json.loads(x)
    for x in Path(args.pairs).read_text().splitlines()
    if x.startswith("{")
]
pairs = [p for p in pairs if STRUCT[p["X"]] == shape and STRUCT[p["Y"]] == shape]
feas = {frozenset((p["X"], p["Y"])) for p in pairs}
si, sn = (int(x) for x in args.shard.split("/"))
OUT = Path(args.out if sn == 1 else args.out.replace(".jsonl", f".{si}.jsonl"))


def cells(n):
    return {parse_cell(x) for x in n.split("-")}


quads = {}
for a, b in combinations(pairs, 2):
    ls = [a["X"], a["Y"], b["X"], b["Y"]]
    cs = [cells(n) for n in ls]
    if any(cs[i] & cs[j] for i in range(4) for j in range(i + 1, 4)):
        continue
    quads.setdefault(frozenset(ls), 0)
quads = sorted(quads, key=sorted)
print(f"{len(pairs)} pairs, {len(quads)} 4-sets", flush=True)
MATCH = [((0, 1), (2, 3)), ((0, 2), (1, 3)), ((0, 3), (1, 2))]


def key(ls, k):
    return "|".join("".join("ABCD"[i] for i in pr) for pr in MATCH[k])


def solver(t):
    sv = cp_model.CpSolver()
    sv.parameters.num_search_workers = 1
    sv.parameters.max_time_in_seconds = t
    return sv


def model(ls):
    setup = {
        **SEED,
        "lines": dict(
            base["lines"], **{"ABCD"[i]: n.split("-") for i, n in enumerate(ls)}
        ),
        "pairs": base["pairs"],
    }
    m, digit, cc, _ = build(setup)
    val = [[m.NewIntVar(1, 9, "") for c in range(9)] for r in range(9)]
    isv = {}
    for r in range(9):
        for c in range(9):
            m.Add(val[r][c] == digit[r][c]).OnlyEnforceIf(cc[r][c].Not())
            m.Add(val[r][c] == digit[8 - r][8 - c]).OnlyEnforceIf(cc[r][c])
    lc = [[parse_cell(x) for x in n.split("-")] for n in ls]
    for i in range(4):
        for r, c in lc[i]:
            for v in range(1, 10):
                b = m.NewBoolVar("")
                m.Add(val[r][c] == v).OnlyEnforceIf(b)
                m.Add(val[r][c] != v).OnlyEnforceIf(b.Not())
                isv[r, c, v] = b
    mt = [m.NewBoolVar(f"mt{k}") for k in range(3)]
    m.AddExactlyOne(mt)
    for k, prs in enumerate(MATCH):
        for x, y in prs:
            for v in range(1, 10):
                m.Add(
                    sum(isv[r, c, v] for r, c in lc[x])
                    == sum(isv[r, c, v] for r, c in lc[y])
                ).OnlyEnforceIf(mt[k])
    return m, digit, cc, val, mt, lc


def holds(vals, x, y):
    return sorted(vals[x]) == sorted(vals[y])


for qi, q in enumerate(quads):
    if qi % sn != si:
        continue
    ls = sorted(q)
    cat = [
        k
        for k, prs in enumerate(MATCH)
        if all(frozenset((ls[x], ls[y])) in feas for x, y in prs)
    ]
    t = time.time()
    m, digit, cc, val, mt, lc = model(ls)
    sols = []
    first = None
    while len(sols) < 3:
        sv = solver(60)
        st = sv.Solve(m)
        if st not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            break
        d = [[sv.Value(digit[r][c]) for c in range(9)] for r in range(9)]
        k = [[sv.Value(cc[r][c]) for c in range(9)] for r in range(9)]
        mk = next(i for i in range(3) if sv.Value(mt[i]))
        sols.append(mk)
        if first is None:
            first = [[sv.Value(val[r][c]) for r, c in lc[i]] for i in range(4)]
        bs = []
        for r in range(9):
            for c in range(9):
                b = m.NewBoolVar("")
                m.Add(digit[r][c] != d[r][c]).OnlyEnforceIf(b)
                bs.append(b)
                bs.append(cc[r][c] if not k[r][c] else cc[r][c].Not())
        bs.append(mt[mk].Not())
        m.AddBoolOr(bs)
    if not sols:
        print(
            f"quad {qi + 1}/{len(quads)} infeasible {time.time() - t:.1f}s", flush=True
        )
        continue
    admits = set(sols)
    for k in range(3):
        if k in admits:
            continue
        m2, *_rest = model(ls)
        mt2 = _rest[3]
        m2.Add(mt2[k] == 1)
        if solver(60).Solve(m2) in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            admits.add(k)
    coincide = [
        key(ls, k)
        for k, prs in enumerate(MATCH)
        if k != sols[0] and all(holds(first, x, y) for x, y in prs)
    ]
    row = {
        "lines": ls,
        "n": len(sols),
        "matchings": [key(ls, k) for k in sorted(admits)],
        "catalogue": [key(ls, k) for k in cat],
        "coincide": coincide,
        "first": key(ls, sols[0]),
        "values": first,
        "t": round(time.time() - t, 1),
    }
    with OUT.open("a") as f:
        print(json.dumps(row), file=f, flush=True)
    print(
        f"quad {qi + 1}/{len(quads)} n={row['n']} m={row['matchings']} {row['t']}s",
        flush=True,
    )
with OUT.open("a") as f:
    print("DONE", file=f)
