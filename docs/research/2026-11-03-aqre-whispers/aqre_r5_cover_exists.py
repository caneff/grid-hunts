"""SCRATCH: does any strict r5 layout exist? Exact cover over the catalogues, by solver.

Random probes through aqre_r5_cover never placed more than 3 regions, which proves nothing.
This asks the question directly, for each place `n` of r5's 9. One boolean per candidate
region, at most one region per cell, each circled column one region, exactly one from the
8 list (one per symmetry group) and one from the forced-7 list, the rest from the low list.

The ninth region's connectivity and the 1-6 matching are checked after a solve, with a cut
on failure. INFEASIBLE is a proof for that `n`, on these catalogues, up to symmetry and
assuming the 9's region rules in the catalogues. `control` swaps the low list for all three
lists, which must allow a layout. Region rules are judged on each region alone.
"""

import json
import sys
import time
from pathlib import Path

from aqre_r5_cover import ROW_MASK, allowed, components, FULL, load
from aqre_r5_fixed_regions import can_match
from ortools.sat.python import cp_model

ROW = 4
LIMIT = 900.0


def solve(table, n, widen):
    m = cp_model.CpModel()
    by_cell = {i: [] for i in range(81)}
    columns = {c: [] for c in range(9) if c != n}
    eights, sevens = [], []
    info = {}

    def add(c, mask, kind, counts):
        v = m.new_bool_var("")
        info[v.index] = (v, c, mask, kind, counts)
        columns[c].append(v)
        low = mask
        while low:
            b = low & -low
            low ^= b
            by_cell[b.bit_length() - 1].append(v)
        return v

    for c in columns:
        if c <= 4:
            for mask in table[c]["eight"]:
                if allowed(mask, c, n):
                    eights.append(add(c, mask, "eight", ()))
        for mask in table[c]["seven"]:
            if allowed(mask, c, n):
                sevens.append(add(c, mask, "seven", ()))
        for mask, counts in table[c]["low"]:
            if allowed(mask, c, n):
                add(c, mask, "low", counts)
        if widen:
            for kind in ("eight", "seven"):
                for mask in table[c][kind]:
                    if allowed(mask, c, n):
                        add(c, mask, "low", (1, 2, 3, 4, 5, 6))
    print(f"  {len(info)} candidate regions", flush=True)
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
            return name, None, time.time() - start, cuts
        chosen = [info[i] for i in info if s.value(info[i][0])]
        free = FULL
        for _, _, mask, _, _ in chosen:
            free &= ~mask
        counts = [e[4] for e in chosen if e[3] == "low"]
        if len(components(free)) == 1 and can_match(counts):
            return name, chosen, time.time() - start, cuts
        m.add_bool_or([e[0].Not() for e in chosen])
        cuts += 1


def main(out, mode):
    table = load(out)
    if mode == "control":
        for n in (4,):
            name, chosen, spent, cuts = solve(table, n, True)
            print(f"control, 9 in r5c{n + 1}, low list widened: {name} in {spent:.1f}s, cuts {cuts}", flush=True)
        return
    for n in (4, 3, 5, 2, 6, 1, 7, 0, 8):
        print(f"9 in r5c{n + 1}", flush=True)
        name, chosen, spent, cuts = solve(table, n, False)
        print(f"  {name} in {spent:.1f}s, cuts {cuts}", flush=True)
        if chosen:
            with (out / "cover-exists.jsonl").open("a") as f:
                f.write(json.dumps({
                    "n": n,
                    "regions": [{"column": c, "mask": str(mask), "kind": kind} for _, c, mask, kind, _ in chosen],
                }) + "\n")


if __name__ == "__main__":
    main(Path(sys.argv[2]), sys.argv[1])
