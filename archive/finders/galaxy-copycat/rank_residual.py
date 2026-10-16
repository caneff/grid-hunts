"""Exact re-check and ranking of line searches against a board's residual set.

Usage: uv run rank_residual.py residual.npz quads quad4.jsonl [quad4.jsonl ...] > out.jsonl
       uv run rank_residual.py residual.npz pairs pairs.jsonl > out.jsonl
quads: per 4-set, survivors under lines only (region sums, no pairing), per
  matching the survivors with the pairing, and per wrong matching how many
  lines-only survivors have equal pair sums (0 = the pairing is decided by
  sums alone).  Rows sorted so the hardest-to-pair unique 4-sets come first.
pairs: per pair, survivors with the pair constraint, distinct small-segment
  multisets of each line among them, and forced digit count.
"""

import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import residual
from copycat_rsl_solver import parse_cell, segments

MATCH = [((0, 1), (2, 3)), ((0, 2), (1, 3)), ((0, 3), (1, 2))]


def key(k):
    return "|".join("".join("ABCD"[i] for i in pr) for pr in MATCH[k])


def rows_of(paths):
    for p in paths:
        for ln in Path(p).read_text().splitlines():
            if ln.startswith("{"):
                yield json.loads(ln)


def line_sum(R, cells):
    cs = [parse_cell(c) for c in cells.split("-")]
    return R.values(segments(cs)[0]).sum(1)


def quads(R, paths):
    out = []
    for row in rows_of(paths):
        ls = row["lines"]
        lm = np.ones(R.n, dtype=bool)
        for n in ls:
            lm &= R.line_mask(n.split("-"))
        sums = [line_sum(R, n) for n in ls]
        per = {}
        for k, prs in enumerate(MATCH):
            pm = lm.copy()
            for x, y in prs:
                pm &= R.pair_mask(ls[x].split("-"), ls[y].split("-"))
            per[key(k)] = int(pm.sum())
        sumok = {}
        for k, prs in enumerate(MATCH):
            sm = lm.copy()
            for x, y in prs:
                sm &= sums[x] == sums[y]
            sumok[key(k)] = int(sm.sum())
        admits = [k for k in per if per[k]]
        r = {
            "lines": ls,
            "lines_only": int(lm.sum()),
            "per_matching": per,
            "sum_compatible": sumok,
            "unique": len(admits) == 1 and per[admits[0]] == 1,
            "wrong_but_sum_ok": sum(v for k, v in sumok.items() if k not in admits),
            "cp_sat": {"n": row["n"], "matchings": row["matchings"]},
        }
        r["agree"] = (min(row["n"], 3) == min(sum(per.values()), 3)) and sorted(
            row["matchings"]
        ) == sorted(admits)
        out.append(r)
    out.sort(key=lambda r: (not r["unique"], -r["wrong_but_sum_ok"], -r["lines_only"]))
    return out


def pairs(R, path):
    out = []
    for row in rows_of([path]):
        X, Y = row["X"].split("-"), row["Y"].split("-")
        m = R.line_mask(X) & R.line_mask(Y) & R.pair_mask(X, Y)
        n = int(m.sum())
        r = {"X": row["X"], "Y": row["Y"], "n": n}
        if n:
            xs, ys = [parse_cell(c) for c in X], [parse_cell(c) for c in Y]
            sx = segments(xs)
            sy = segments(ys)
            small_x = min(sx, key=len)
            small_y = min(sy, key=len)
            vx = np.sort(R.values(small_x)[m], axis=1)
            vy = np.sort(R.values(small_y)[m], axis=1)
            r["X_small"] = sorted({tuple(map(int, v)) for v in vx})
            r["Y_small"] = sorted({tuple(map(int, v)) for v in vy})
            r["shuffled_solutions"] = int((vx != vy).any(1).sum())
            f = R.forced(m)
            r["forced_digits"] = len(f["digits"])
        out.append(r)
    out.sort(key=lambda r: (r["n"] == 0, r["n"], -r.get("forced_digits", 0)))
    return out


def main():
    R = residual.load(sys.argv[1])
    cmd = sys.argv[2]
    rows = quads(R, sys.argv[3:]) if cmd == "quads" else pairs(R, sys.argv[3])
    for r in rows:
        print(json.dumps(r))


if __name__ == "__main__":
    main()
