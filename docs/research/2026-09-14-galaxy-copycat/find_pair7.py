"""Find pairs of longer lines (default 7 cells, segments (3,4)) that can be
added, paired with each other, to a board with existing pairs, such that the
two lines can take DIFFERENT splits of the shared value multiset (the 3-cell
segments carry different values), i.e. the pairing does not match segment to
segment.

Usage: uv run find_pair7.py board.json out_prefix [--length 7] [--shape 3,4]
         [--seed forced.json] [--cap 150] [--shard i/n]
Stage 1: every orthogonal path of `length` cells off the existing lines whose
segment sizes are `shape` (either way round); per line, enumerate its
distinct value vectors exactly (a nogood per vector found, up to `cap`),
recording each (multiset, small-segment multiset).  -> out_prefix.lines.jsonl
With --shard i/n only every n-th line (offset i) is done and the output goes
to out_prefix.lines.i.jsonl; run without --shard afterwards to merge the
shard files and do stage 2.
Stage 2: every disjoint pair sharing a multiset for which the two lines were
seen with different small-segment values; exact check with the pair
constraint plus "small segments differ".  -> out_prefix.pairs.jsonl (FEASIBLE
rows: X, Y, the multiset/splits found, n solutions capped) ; DONE at the end.
Rank the survivors with rank_pair4.py (it is length-agnostic).
"""

import argparse
import json
import sys
import time
from collections import defaultdict
from itertools import combinations
from pathlib import Path

sys.path.insert(0, "docs/research/2026-09-14-galaxy-copycat")
from copycat_rsl_solver import build, parse_cell, segments, value_of
from ortools.sat.python import cp_model

ap = argparse.ArgumentParser()
ap.add_argument("board")
ap.add_argument("out")
ap.add_argument("--length", type=int, default=7)
ap.add_argument("--shape", default="3,4")
ap.add_argument("--seed")
ap.add_argument("--cap", type=int, default=150, help="max value vectors per line")
ap.add_argument("--shard", help="i/n: do lines i, i+n, ... and write .lines.i.jsonl")
args = ap.parse_args()
SHARD = tuple(int(x) for x in args.shard.split("/")) if args.shard else None
base = json.loads(Path(args.board).read_text())
SEED = json.loads(Path(args.seed).read_text()) if args.seed else {}
SHAPE = sorted(int(x) for x in args.shape.split(","))
used = {parse_cell(c) for cells in base["lines"].values() for c in cells}
LINES_OUT = Path(args.out + (f".lines.{SHARD[0]}.jsonl" if SHARD else ".lines.jsonl"))
PAIRS_OUT = Path(args.out + ".pairs.jsonl")


def name(rc):
    return f"r{rc[0] + 1}c{rc[1] + 1}"


paths = set()


def grow(p):
    if len(p) == args.length:
        paths.add(min(tuple(p), tuple(reversed(p))))
        return
    r, c = p[-1]
    for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        n = (r + dr, c + dc)
        if 0 <= n[0] < 9 and 0 <= n[1] < 9 and n not in used and n not in p:
            grow([*p, n])


for r in range(9):
    for c in range(9):
        if (r, c) not in used:
            grow([(r, c)])
cands = sorted(p for p in paths if sorted(len(s) for s in segments(list(p))) == SHAPE)
print(f"{len(paths)} paths, {len(cands)} with shape {SHAPE}", flush=True)


def small_seg(cells):
    return min(segments(list(cells)), key=len)


def add_values(m, digit, cc):
    val = [[m.NewIntVar(1, 9, f"val{r}{c}") for c in range(9)] for r in range(9)]
    for r in range(9):
        for c in range(9):
            m.Add(val[r][c] == digit[r][c]).OnlyEnforceIf(cc[r][c].Not())
            m.Add(val[r][c] == digit[8 - r][8 - c]).OnlyEnforceIf(cc[r][c])
    return val


def solver(t):
    sv = cp_model.CpSolver()
    sv.parameters.num_search_workers = 1
    sv.parameters.max_time_in_seconds = t
    return sv


def line_info(cells):
    """multiset -> set of small-segment multisets, from an exact enumeration of
    the line's value vectors (nogood per vector, capped)."""
    setup = {
        **SEED,
        "lines": dict(base["lines"], X=[name(c) for c in cells]),
        "pairs": base["pairs"],
    }
    seen = defaultdict(set)
    small = small_seg(cells)
    m, digit, cc, _ = build(setup)
    val = add_values(m, digit, cc)
    for _ in range(args.cap):
        sv = solver(20)
        if sv.Solve(m) not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            break
        vec = [sv.Value(val[r][c]) for r, c in cells]
        seen[tuple(sorted(vec))].add(
            tuple(sorted(sv.Value(val[r][c]) for r, c in small))
        )
        bs = []
        for (r, c), v in zip(cells, vec, strict=True):
            b = m.NewBoolVar("")
            m.Add(val[r][c] != v).OnlyEnforceIf(b)
            bs.append(b)
        m.AddBoolOr(bs)
    return seen


infos = {}


def load_lines(path):
    for row in map(json.loads, path.read_text().splitlines()):
        infos[tuple(parse_cell(c) for c in row["cells"].split("-"))] = {
            tuple(json.loads(k)): {tuple(s) for s in v} for k, v in row["seen"].items()
        }


for path in [
    LINES_OUT,
    *Path(args.out).parent.glob(Path(args.out).name + ".lines.*.jsonl"),
]:
    if path.exists():
        load_lines(path)
if infos:
    print(f"resumed {len(infos)} lines", flush=True)
todo = [
    p
    for i, p in enumerate(cands)
    if p not in infos and (not SHARD or i % SHARD[1] == SHARD[0])
]
for i, p in enumerate(todo):
    t = time.time()
    seen = line_info(p)
    infos[p] = seen
    with LINES_OUT.open("a") as f:
        print(
            json.dumps(
                {
                    "cells": "-".join(name(c) for c in p),
                    "seen": {
                        json.dumps(list(ms)): [list(s) for s in v]
                        for ms, v in seen.items()
                    },
                    "n": sum(len(v) for v in seen.values()),
                    "t": round(time.time() - t, 1),
                }
            ),
            file=f,
            flush=True,
        )
    print(
        f"line {i + 1}/{len(todo)} {len(seen)} multisets {time.time() - t:.1f}s",
        flush=True,
    )
if SHARD:
    print("shard done", flush=True)
    sys.exit(0)
missing = [p for p in cands if p not in infos]
if missing:
    raise SystemExit(f"{len(missing)} lines not yet enumerated; run the shards first")

pairs = []
for a, b in combinations(cands, 2):
    if set(a) & set(b):
        continue
    for ms in infos[a].keys() & infos[b].keys():
        if infos[a][ms] | infos[b][ms] and len(infos[a][ms] | infos[b][ms]) >= 2:
            pairs.append((a, b))
            break
print(
    f"{len(pairs)} candidate pairs with a shuffle-capable shared multiset", flush=True
)


def pair_check(a, b):
    setup = {
        **SEED,
        "lines": dict(base["lines"], X=[name(c) for c in a], Y=[name(c) for c in b]),
        "pairs": [*base["pairs"], ["X", "Y"]],
    }
    m, digit, cc, _ = build(setup)
    val = add_values(m, digit, cc)
    sa, sb = small_seg(a), small_seg(b)
    diffs = []
    for v in range(1, 10):
        ca, cb = [], []
        for seg, acc in ((sa, ca), (sb, cb)):
            for r, c in seg:
                x = m.NewBoolVar("")
                m.Add(val[r][c] == v).OnlyEnforceIf(x)
                m.Add(val[r][c] != v).OnlyEnforceIf(x.Not())
                acc.append(x)
        d = m.NewBoolVar("")
        m.Add(sum(ca) != sum(cb)).OnlyEnforceIf(d)
        m.Add(sum(ca) == sum(cb)).OnlyEnforceIf(d.Not())
        diffs.append(d)
    m.AddBoolOr(diffs)
    sv = solver(60)
    st = sv.Solve(m)
    if st not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return None
    d = [[sv.Value(digit[r][c]) for c in range(9)] for r in range(9)]
    k = [[bool(sv.Value(cc[r][c])) for c in range(9)] for r in range(9)]
    return {
        "multiset": sorted(value_of(d, k, r, c) for r, c in a),
        "X_small": sorted(value_of(d, k, r, c) for r, c in sa),
        "Y_small": sorted(value_of(d, k, r, c) for r, c in sb),
    }


for i, (a, b) in enumerate(pairs):
    t = time.time()
    res = pair_check(a, b)
    if res:
        with PAIRS_OUT.open("a") as f:
            print(
                json.dumps(
                    {
                        "X": "-".join(name(c) for c in a),
                        "Y": "-".join(name(c) for c in b),
                        **res,
                        "t": round(time.time() - t, 1),
                    }
                ),
                file=f,
                flush=True,
            )
    if (i + 1) % 100 == 0:
        print(f"pair {i + 1}/{len(pairs)}", flush=True)
with PAIRS_OUT.open("a") as f:
    print("DONE", file=f)
