"""SCRATCH: print the chain that rules out a fact on one of Chris's boards.

Uses nr_t36_next's simple rules on a board JSON. Corner sets are applied as a limit on
the digit in those lines. Prints the steps of each try, or says propagation alone does
not refute it, and then tries one more level of case split.

Usage: nr_why.py BOARD_JSON FACT [FACT ...]   where FACT is r9c9=2 or r5c1=not or r5c1=yes
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import nr_t36_next as N


def start(data):
    N.BOARD = frozenset(N.cell(n) for n in data["marks"])
    cand = {k: set(range(1, 10)) for k in N.BORDER}
    for name, text in data.get("pencils", {}).items():
        if N.cell(name) in cand:
            cand[N.cell(name)] = {int(d) for d in text}
    for name, d in data.get("digits", {}).items():
        cand[N.cell(name)] = {d}
    for group in data.get("corners", []):
        cells = {N.cell(n) for n in group["cells"]}
        for unit in N.UNITS:
            if cells & set(unit):
                for k in unit:
                    if k not in cells:
                        cand[k].discard(group["digit"])
    status = dict.fromkeys(N.CELLS)
    for n in data.get("pink", []):
        status[N.cell(n)] = 1
    for n in data.get("green", []):
        status[N.cell(n)] = 0
    return cand, status


def apply(cand, status, fact):
    name, value = fact.split("=")
    k = N.cell(name)
    if value == "not":
        status[k] = 0
    elif value == "yes":
        status[k] = 1
    else:
        cand[k] = {int(value)}


def main(path, facts):
    data = json.loads(Path(path).read_text())
    cand, status = start(data)
    N.propagate(cand, status, [])
    for fact in facts:
        a, b = N.copy(cand, status)
        apply(a, b, fact)
        steps = []
        try:
            N.propagate(a, b, steps)
            print(fact, "survives simple rules, then splits:")
            for k in N.BORDER:
                if 1 < len(a[k]) <= 3:
                    results = []
                    for d in sorted(a[k]):
                        c, e = N.copy(a, b)
                        c[k] = {d}
                        sub = []
                        try:
                            N.propagate(c, e, sub)
                            results.append(None)
                        except N.Fail as err:
                            results.append((d, len(sub), str(err), sub))
                    if all(results):
                        print("  case split on", N.nm(k), "closes:")
                        for d, n, why, sub in results:
                            print(f"    {d}: {n} steps, {why}")
                            print("      ", " | ".join(sub[:25]))
                        break
            else:
                print("  no 3-way split closes it")
        except N.Fail as err:
            print(fact, f"fails in {len(steps)} steps: {err}")
            for line in steps:
                print("  ", line)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2:])
