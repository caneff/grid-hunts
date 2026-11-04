"""SCRATCH: what kills the 490 r5 layouts? Each is re-solved with one rule dropped at a time. 12 processes.

usage: aqre_row_diagnose.py DIR LAYOUTS_FILE ROW

The model repeats `aqre_r5_fixed_regions.build` with each rule behind a flag. A drop that turns a layout
FEASIBLE shows that rule takes part in its failure. A drop that stays INFEASIBLE shows the layout fails
without that rule. Control: with every rule on, grid-8-r1's regions must be FEASIBLE and each layout must
be INFEASIBLE, as the fixed-region solve found. UNKNOWN at the cap proves nothing and is counted apart.
"""

import json
import multiprocessing
import sys
import time
from collections import Counter
from pathlib import Path

from aqre_jigsaw_feasible import neighbours
from connected import add_flow_connectivity
from ortools.sat.python import cp_model

CELLS = [(r, c) for r in range(9) for c in range(9)]
LIMIT = 20.0
WORKERS = 6
RULES = ("connect", "rows", "columns", "regions", "cross whispers", "all whispers", "lines", "all circles")


def build(region, row, n, off=(), circle_off=None):
    regions = [[cell for cell in CELLS if region[cell] == k] for k in range(9)]
    m = cp_model.CpModel()
    x = {cell: m.new_int_var(1, 9, "") for cell in CELLS}
    if "rows" not in off:
        for r in range(9):
            m.add_all_different([x[r, c] for c in range(9)])
    if "columns" not in off:
        for c in range(9):
            m.add_all_different([x[r, c] for r in range(9)])
    if "regions" not in off:
        for cells in regions:
            m.add_all_different([x[cell] for cell in cells])
    g = {cell: m.new_bool_var("") for cell in CELLS}
    even_low = m.new_bool_var("")
    m.add(x[row, n] == 9)
    whispers = "all whispers" not in off
    for k, cells in enumerate(regions):
        total = sum(g[cell] for cell in cells)
        m.add(total >= 1)
        m.add(total <= 8)
        if k != n and "all circles" not in off and k != circle_off:
            m.add(x[row, k] == total)
        if whispers:
            for colour in (0, 1):
                m.add(sum(g[r, c] for r, c in cells if (r + c) % 2 == colour) <= 4)
    for a in range(9):
        if whispers:
            for colour in (0, 1):
                m.add(sum(g[a, c] for c in range(9) if (a + c) % 2 == colour) <= 4)
                m.add(sum(g[r, a] for r in range(9) if (r + a) % 2 == colour) <= 4)
        if "lines" not in off:
            for b in range(6):
                for line in ([g[a, b + i] for i in range(4)], [g[b + i, a] for i in range(4)]):
                    m.add_bool_or(line)
                    m.add_bool_or([v.Not() for v in line])
    for r, c in CELLS:
        low = even_low if (r + c) % 2 == 0 else even_low.Not()
        s = g[r, c]
        if whispers:
            m.add(x[r, c] <= 4).only_enforce_if(s, low)
            m.add(x[r, c] >= 6).only_enforce_if(s, low.Not())
            for other in neighbours((r, c)):
                if (r, c) < other and ("cross whispers" not in off or region[r, c] == region[other]):
                    t = g[other]
                    m.add(x[other] - x[r, c] >= 5).only_enforce_if(s, t, low)
                    m.add(x[r, c] - x[other] >= 5).only_enforce_if(s, t, low.Not())
    if "connect" not in off:
        add_flow_connectivity(m, [g[cell] for cell in CELLS])
    return m


def status(region, row, n, off=(), circle_off=None):
    s = cp_model.CpSolver()
    s.parameters.num_workers = 1
    s.parameters.max_time_in_seconds = LIMIT
    return s.status_name(s.solve(build(region, row, n, off, circle_off)))


def one_layout(args):
    index, region, row, n = args
    begun = time.time()
    out = {"all rules": status(region, row, n)}
    for rule in RULES:
        out[rule] = status(region, row, n, (rule,))
    for c in range(9):
        if c != n:
            out[f"circle c{c + 1}"] = status(region, row, n, (), c)
    return index, out, time.time() - begun


def main():
    out = Path(sys.argv[1])
    row = int(sys.argv[3]) - 1
    known = json.loads((out / "grid-8-r1.json").read_text())
    control = {tuple(cell): k for k, cells in enumerate(known["regions"]) for cell in cells}
    print(f"control, grid-8-r1 regions, all rules: {status(control, 0, 4)}", flush=True)
    records = [json.loads(line) for line in Path(sys.argv[2]).read_text().splitlines()]
    jobs = [(i, {(r, q): x["region"][r][q] for r in range(9) for q in range(9)}, row, x["n"]) for i, x in enumerate(records)]
    tally = {}
    rescue = Counter()
    results = {}
    begun = time.time()
    saved = out / f"diagnose-r{row + 1}.jsonl"
    with multiprocessing.get_context("fork").Pool(WORKERS) as pool:
        for done, (index, result, spent) in enumerate(pool.imap_unordered(one_layout, jobs), 1):
            results[index] = result
            for rule, name in result.items():
                tally.setdefault(rule, Counter())[name] += 1
            drops = sorted(r for r, v in result.items() if v in ("OPTIMAL", "FEASIBLE") and r != "all rules")
            unknown = sum(v == "UNKNOWN" for v in result.values())
            rescue[tuple(drops)] += 1
            with saved.open("a") as f:
                f.write(json.dumps({"index": index, "result": result}) + "\n")
            print(f"{done} of {len(jobs)}: layout {index}, all rules {result['all rules']}, feasible when dropped {drops or 'none'}, {unknown} unknown, {spent:.0f}s; {time.time() - begun:.0f}s in", flush=True)
    for rule in ("all rules", *RULES, *[f"circle c{c + 1}" for c in range(9)]):
        if rule in tally:
            t = tally[rule]
            print(f"{rule}: feasible {t['FEASIBLE'] + t['OPTIMAL']}, infeasible {t['INFEASIBLE']}, unknown {t['UNKNOWN']}", flush=True)
    print("drops that make a layout feasible, by frequency:", flush=True)
    for drops, n in rescue.most_common(12):
        print(f"  {n}: {', '.join(drops) or 'none'}", flush=True)


if __name__ == "__main__":
    main()
