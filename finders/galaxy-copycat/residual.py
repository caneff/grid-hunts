"""Residual solution set of a board: every (digit grid, copycat placement) that
satisfies it, stored once so later questions are numpy filters.

Usage: uv run residual.py build board.json grids.txt out.npz [--seed forced.json]
  grids.txt: one 81-digit grid per line (from a digit-only nogood enumeration)
  For each grid, a DFS over copycat placements (one per box, one per row and
  column, nine different copycat digits, seed flags honoured) keeps those
  satisfying the board's lines and pairs.  -> out.npz with
    grid  (G,81) uint8   digit grids
    gi    (N,)   uint32  grid index per solution
    cc    (N,9)  uint8   copycat cell index (r*9+c) per box
Library (import residual): load(npz) -> R; R.values(cells) -> (N,k) uint8;
R.line_mask(cells); R.pair_mask(a, b); R.forced(mask) -> dict cell->digit
over the surviving solutions, plus which cells' flags are constant.
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from copycat_rsl_solver import parse_cell, segments


def idx(rc):
    return rc[0] * 9 + rc[1]


def box(i):
    return (i // 9) // 3 * 3 + (i % 9) // 3


class R:
    def __init__(self, grid, gi, cc):
        self.grid, self.gi, self.cc = grid, gi, cc
        self.n = len(gi)
        flags = np.zeros((self.n, 81), dtype=bool)
        flags[np.arange(self.n)[:, None], cc] = True
        self.flags = flags
        self.digits = grid[gi]  # (N,81) view by fancy index, materialised

    def values(self, cells):
        ii = np.array(
            [idx(parse_cell(c)) if isinstance(c, str) else idx(c) for c in cells]
        )
        d = self.digits[:, ii]
        o = self.digits[:, 80 - ii]
        return np.where(self.flags[:, ii], o, d)

    def line_mask(self, cells):
        cells = [parse_cell(c) if isinstance(c, str) else c for c in cells]
        segs = segments(cells)
        v = self.values(cells)
        pos = {c: i for i, c in enumerate(cells)}
        s0 = v[:, [pos[c] for c in segs[0]]].sum(1)
        m = np.ones(self.n, dtype=bool)
        for seg in segs[1:]:
            m &= v[:, [pos[c] for c in seg]].sum(1) == s0
        return m

    def pair_mask(self, a, b):
        va = np.sort(self.values(a), axis=1)
        vb = np.sort(self.values(b), axis=1)
        return (va == vb).all(1)

    def forced(self, mask):
        d = self.digits[mask]
        f = self.flags[mask]
        const_d = (d == d[0]).all(0)
        const_f = (f == f[0]).all(0)
        return {
            "n": int(mask.sum()),
            "digits": {i: int(d[0, i]) for i in np.flatnonzero(const_d)},
            "copycats": [int(i) for i in np.flatnonzero(const_f & f[0])],
            "not_copycats": [int(i) for i in np.flatnonzero(const_f & ~f[0])],
        }


def load(path):
    z = np.load(path)
    return R(z["grid"], z["gi"], z["cc"])


def placements(g, seed, lines, pairs):
    """all copycat placements for digit grid g (list of 81 ints)."""
    forced = {idx(parse_cell(c)) for c in seed.get("copycats", [])}
    banned = {idx(parse_cell(c)) for c in seed.get("not_copycats", [])}
    opts = []
    for b in range(9):
        cells = [i for i in range(81) if box(i) == b and i not in banned]
        fb = [i for i in cells if i in forced]
        opts.append(fb if fb else cells)
    lcells = {n: [idx(parse_cell(c)) for c in cs] for n, cs in lines.items()}
    lsegs = {
        n: [[idx(c) for c in s] for s in segments([parse_cell(c) for c in cs])]
        for n, cs in lines.items()
    }
    out = []

    def val(i, flags):
        return g[80 - i] if i in flags else g[i]

    def ok(flags):
        for segs in lsegs.values():
            s = [sum(val(i, flags) for i in seg) for seg in segs]
            if len(set(s)) != 1:
                return False
        for a, b in pairs:
            if sorted(val(i, flags) for i in lcells[a]) != sorted(
                val(i, flags) for i in lcells[b]
            ):
                return False
        return True

    def rec(b, chosen, rows, cols, digs):
        if b == 9:
            fl = set(chosen)
            if ok(fl):
                out.append(list(chosen))
            return
        for i in opts[b]:
            r, c, d = i // 9, i % 9, g[i]
            if r in rows or c in cols or d in digs:
                continue
            rec(b + 1, [*chosen, i], rows | {r}, cols | {c}, digs | {d})

    rec(0, [], frozenset(), frozenset(), frozenset())
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["build"])
    ap.add_argument("board")
    ap.add_argument("grids")
    ap.add_argument("out")
    ap.add_argument("--seed")
    a = ap.parse_args()
    base = json.loads(Path(a.board).read_text())
    seed = json.loads(Path(a.seed).read_text()) if a.seed else {}
    grids = [
        [int(ch) for ch in ln.strip()]
        for ln in Path(a.grids).read_text().splitlines()
        if ln.strip()
    ]
    gi, cc = [], []
    for k, g in enumerate(grids):
        ps = placements(g, seed, base["lines"], base.get("pairs", []))
        gi.extend([k] * len(ps))
        cc.extend(ps)
        if (k + 1) % 200 == 0:
            print(f"grid {k + 1}/{len(grids)} solutions {len(gi)}", flush=True)
    np.savez_compressed(
        a.out,
        grid=np.array(grids, dtype=np.uint8),
        gi=np.array(gi, dtype=np.uint32),
        cc=np.array(cc, dtype=np.uint8),
    )
    print(f"{len(grids)} grids, {len(gi)} solutions -> {a.out}")


if __name__ == "__main__":
    main()
