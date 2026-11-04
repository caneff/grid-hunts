"""SCRATCH: only one r5 region can be the 8, and only one other can be the 7.

Chris, 2026-11-04. Each region is judged alone. Every 8-able region is also 7-able, so the
seven other circled regions hold one that can be a valid 7 (either shading) but not a valid 8,
and six that top out at 6. The ninth region has no rule. Exact cover, by solver, one worker,
for each place of r5's 9, up to symmetry on the 8 region. INFEASIBLE is a proof for that place,
on these catalogues.

`check DIR` first tests the catalogues on sampled layouts from fixed-r5.jsonl: all eight
circled regions of a layout with no straight region must appear in the lists, under the 8
list before symmetry is removed. It also tallies how many regions in a layout top out at 6.
"""

import json
import pickle
import sys
import time
from collections import Counter
from pathlib import Path

from aqre_r5_cover import FULL, ROW_MASK, allowed, components, mask_of
from aqre_r5_cover import flip, mirror
from aqre_r5_fixed_regions import can_match
from ortools.sat.python import cp_model

LIMIT = 900.0
CELLS = [(r, c) for r in range(9) for c in range(9)]


def raw(out):
    with (out / "cover-catalogue.pickle").open("rb") as f:
        return pickle.load(f)


def reps(table):
    kept = {c: list(table[c]["eight"]) for c in range(5)}
    for c in range(4):
        kept[c] = [m for m in kept[c] if m <= flip(m)]
    kept[4] = [m for m in kept[4] if m == min(m, flip(m), mirror(m), flip(mirror(m)))]
    return kept


def check(out):
    table = raw(out)
    sets = {
        c: {
            "eight": set(table[c]["eight"]),
            "seven": set(table[c]["seven"]),
            "either": set(table[c]["either"]),
            "low": {m for m, _ in table[c]["low"]},
        }
        for c in range(9)
    }
    rows = [json.loads(x) for x in (out / "fixed-r5.jsonl").read_text().splitlines()]
    missing = looked = 0
    tops = Counter()
    for row in rows:
        lows = 0
        for c in range(9):
            if c == row["n"]:
                continue
            mask = mask_of([cell for cell in CELLS if row["region"][cell[0]][cell[1]] == c])
            looked += 1
            hit = [k for k, s in sets[c].items() if mask in s]
            if len(hit) != 1:
                missing += 1
            elif hit[0] == "low":
                lows += 1
        tops[lows] += 1
    print(f"catalogue check: {looked} regions from {len(rows)} layouts, {missing} not in exactly one list", flush=True)
    print(f"regions topping out at 6, per sampled layout: {sorted(tops.items())}", flush=True)
    return missing == 0


def solve(table, eights_kept, n):
    m = cp_model.CpModel()
    by_cell = {i: [] for i in range(81)}
    columns = {c: [] for c in range(9) if c != n}
    eights, sevens = [], []
    info = []

    def add(c, mask, counts):
        v = m.new_bool_var("")
        info.append((v, mask, counts))
        columns[c].append(v)
        rest = mask
        while rest:
            b = rest & -rest
            rest ^= b
            by_cell[b.bit_length() - 1].append(v)
        return v

    for c in columns:
        if c <= 4:
            eights += [add(c, x, None) for x in eights_kept[c] if allowed(x, c, n)]
        for kind in ("seven", "either"):
            sevens += [add(c, x, None) for x in table[c][kind] if allowed(x, c, n)]
        for x, counts in table[c]["low"]:
            if allowed(x, c, n):
                add(c, x, counts)
    for options in columns.values():
        m.add_exactly_one(options)
    for options in by_cell.values():
        if options:
            m.add_at_most_one(options)
    m.add_exactly_one(eights)
    m.add_exactly_one(sevens)
    start = time.time()
    cuts = 0
    while True:
        s = cp_model.CpSolver()
        s.parameters.num_workers = 1
        s.parameters.max_time_in_seconds = max(1.0, LIMIT - (time.time() - start))
        status = s.solve(m)
        name = s.status_name(status)
        if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            return name, None, len(info), cuts, time.time() - start
        chosen = [e for e in info if s.value(e[0])]
        free = FULL
        for _, x, _ in chosen:
            free &= ~x
        counts = [e[2] for e in chosen if e[2]]
        if len(components(free)) == 1 and can_match(counts):
            return name, chosen, len(info), cuts, time.time() - start
        m.add_bool_or([e[0].Not() for e in chosen])
        cuts += 1


def run(out):
    table = raw(out)
    kept = reps(table)
    print("8 regions kept:", [len(kept[c]) for c in range(5)], flush=True)
    for n in (4, 3, 5, 2, 6, 1, 7, 0, 8):
        name, chosen, size, cuts, spent = solve(table, kept, n)
        print(f"9 in r5c{n + 1}: {name} in {spent:.1f}s, {size} candidates, cuts {cuts}", flush=True)
        if chosen:
            with (out / "one-each-layouts.jsonl").open("a") as f:
                f.write(json.dumps({"n": n, "masks": [str(x) for _, x, _ in chosen]}) + "\n")


if __name__ == "__main__":
    out_dir = Path(sys.argv[2])
    if sys.argv[1] == "check":
        sys.exit(0 if check(out_dir) else 1)
    run(out_dir)
