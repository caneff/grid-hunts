"""Find pairs of 4-cell lines (each with 2+ segments) that can be added, paired
with each other, to a board whose existing pairs are given.

Usage: uv run find_pair4.py board.json out_prefix
  board.json: {"lines": {...}, "pairs": [[..],[..]]}
Stage 1: every orthogonal 4-cell path off the existing lines; per line, the
exact feasible sums (unpaired) and, per sum, the value multisets it can carry
(a 300-solution sample, then an exact probe of every multiset the segment
model allows that the sample missed).  -> out_prefix.lines.jsonl
Stage 2: every pair of lines with disjoint cells sharing a multiset, checked
exactly with the pair constraint; feasible pairs get a capped solution count.
  -> out_prefix.pairs.jsonl (FEASIBLE rows only) ; DONE at the end.
"""

import json
import sys
import time
from collections import Counter
from itertools import combinations
from pathlib import Path

sys.path.insert(0, "docs/research/2026-09-14-galaxy-copycat")
from copycat_rsl_solver import Collector, build, parse_cell, segments, value_of
from ortools.sat.python import cp_model
from segment_openers import line_multisets

BASE, OUT = sys.argv[1], sys.argv[2]
base = json.loads(Path(BASE).read_text())
used = {parse_cell(c) for cells in base["lines"].values() for c in cells}
LINES_OUT, PAIRS_OUT = Path(OUT + ".lines.jsonl"), Path(OUT + ".pairs.jsonl")


def name(rc):
    return f"r{rc[0] + 1}c{rc[1] + 1}"


paths = set()


def grow(p):
    if len(p) == 4:
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
cands = sorted(p for p in paths if len(segments(list(p))) >= 2)
print(f"{len(paths)} paths, {len(cands)} with 2+ segments", flush=True)


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
    """feasible sums -> set of multisets, for one line added unpaired."""
    setup = {
        "lines": dict(base["lines"], X=[name(c) for c in cells]),
        "pairs": base["pairs"],
    }
    struct = tuple(len(s) for s in segments(list(cells)))
    out = {}
    for s in range(3, 31):
        m, digit, cc, _ = build(dict(setup, sums={"X": s}))
        sv = solver(30)
        sv.parameters.enumerate_all_solutions = True
        col = Collector(digit, cc, 300)
        st = sv.Solve(m, col)
        if not col.solutions:
            continue
        seen = Counter()
        for d, k in col.solutions:
            seen[tuple(sorted(value_of(d, k, r, c) for r, c in cells))] += 1
        msets = set(seen)
        if len(col.solutions) >= 300 or st == cp_model.UNKNOWN:
            for ms in line_multisets(struct, s):
                if ms in msets:
                    continue
                m2, d2, k2, _ = build(dict(setup, sums={"X": s}))
                val = add_values(m2, d2, k2)
                cnt = Counter(ms)
                for v in range(1, 10):
                    b = []
                    for r, c in cells:
                        x = m2.NewBoolVar("")
                        m2.Add(val[r][c] == v).OnlyEnforceIf(x)
                        m2.Add(val[r][c] != v).OnlyEnforceIf(x.Not())
                        b.append(x)
                    m2.Add(sum(b) == cnt[v])
                if solver(30).Solve(m2) in (cp_model.OPTIMAL, cp_model.FEASIBLE):
                    msets.add(ms)
        out[s] = sorted(msets)
    return struct, out


infos = {}
for i, p in enumerate(cands):
    t = time.time()
    struct, info = line_info(p)
    infos[p] = info
    with LINES_OUT.open("a") as f:
        print(
            json.dumps(
                {
                    "cells": "-".join(name(c) for c in p),
                    "struct": struct,
                    "sums": {str(s): [list(ms) for ms in v] for s, v in info.items()},
                    "t": round(time.time() - t, 1),
                }
            ),
            file=f,
            flush=True,
        )
    print(
        f"line {i + 1}/{len(cands)} {struct} sums {sorted(info)} {time.time() - t:.1f}s",
        flush=True,
    )

live = [p for p in cands if infos[p]]
pairs = []
for a, b in combinations(live, 2):
    if set(a) & set(b):
        continue
    ma = {ms for v in infos[a].values() for ms in v}
    mb = {ms for v in infos[b].values() for ms in v}
    if ma & mb:
        pairs.append((a, b))
print(f"{len(live)} live lines, {len(pairs)} candidate pairs", flush=True)
for i, (a, b) in enumerate(pairs):
    setup = {
        "lines": dict(base["lines"], X=[name(c) for c in a], Y=[name(c) for c in b]),
        "pairs": [*base["pairs"], ["X", "Y"]],
    }
    m, digit, cc, _ = build(setup)
    sv = solver(60)
    sv.parameters.enumerate_all_solutions = True
    col = Collector(digit, cc, 200)
    t = time.time()
    st = sv.Solve(m, col)
    if col.solutions:
        sums = Counter()
        for d, k in col.solutions:
            sums[sum(value_of(d, k, r, c) for r, c in segments(list(a))[0])] += 1
        with PAIRS_OUT.open("a") as f:
            print(
                json.dumps(
                    {
                        "X": "-".join(name(c) for c in a),
                        "Y": "-".join(name(c) for c in b),
                        "n": len(col.solutions),
                        "X_sums": sorted(sums),
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
