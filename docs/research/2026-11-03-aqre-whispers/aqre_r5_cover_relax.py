"""SCRATCH: how far is the strict cover from fitting? One worker.

The strict cover is infeasible for every place of the 9. Here the 8 and the forced 7 stay,
and the six lower regions may also come from the forced-7 list, a subset of the regions
that cannot be a valid 8. The solver maximises how many of the six top out at 6. Capped
runs: a value reached is real, and a value not reached is not ruled out unless OPTIMAL.
The ninth region's connectivity is checked after and reported, not forced.
"""

import sys
from pathlib import Path

from aqre_r5_cover import FULL, allowed, components, load
from ortools.sat.python import cp_model

LIMIT = 120.0


def solve(table, n):
    m = cp_model.CpModel()
    by_cell = {i: [] for i in range(81)}
    columns = {c: [] for c in range(9) if c != n}
    eights, sevens, lows = [], [], []
    info = []

    def add(c, mask, kind):
        v = m.new_bool_var("")
        info.append((v, c, mask, kind))
        columns[c].append(v)
        rest = mask
        while rest:
            b = rest & -rest
            rest ^= b
            by_cell[b.bit_length() - 1].append(v)
        return v

    for c in columns:
        if c <= 4:
            for mask in table[c]["eight"]:
                if allowed(mask, c, n):
                    eights.append(add(c, mask, "eight"))
        for mask in table[c]["seven"]:
            if allowed(mask, c, n):
                sevens.append(add(c, mask, "seven"))
                add(c, mask, "lower")
        for mask, _ in table[c]["low"]:
            if allowed(mask, c, n):
                lows.append(add(c, mask, "low"))
    for options in columns.values():
        m.add_exactly_one(options)
    for options in by_cell.values():
        if options:
            m.add_at_most_one(options)
    m.add_exactly_one(eights)
    m.add_exactly_one(sevens)
    m.maximize(sum(lows))
    s = cp_model.CpSolver()
    s.parameters.num_workers = 1
    s.parameters.max_time_in_seconds = LIMIT
    status = s.solve(m)
    name = s.status_name(status)
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return name, None, None, None
    chosen = [e for e in info if s.value(e[0])]
    free = FULL
    for _, _, mask, _ in chosen:
        free &= ~mask
    return name, int(s.objective_value), s.best_objective_bound, len(components(free))


def main(out):
    table = load(out)
    for n in (4, 3, 2, 1, 0, 5, 6, 7, 8):
        name, best, bound, parts = solve(table, n)
        print(f"9 in r5c{n + 1}: {name}, lows {best} of 6, bound {bound}, leftover pieces {parts}", flush=True)


if __name__ == "__main__":
    main(Path(sys.argv[1]))
