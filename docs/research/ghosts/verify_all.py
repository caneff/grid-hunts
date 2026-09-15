"""Merge, deduplicate and independently verify all-visible ghost examples.

    uv run docs/research/ghosts/verify_all.py OUT.jsonl IN.jsonl [IN.jsonl ...]

Each input line needs a "shape" (cell indices 0-80). The check shares no code
with the finders: givens are recomputed as ghost-neighbour counts, must be
1-8 and include an 8, and a CP-SAT all-different sudoku with those givens
must have exactly one solution. Shapes are deduplicated up to the 8 square
symmetries (keeping the first seen). OUT gets one verified example per line:
ghosts, shape, givens, solution. A failing shape is reported and dropped.
"""

import json
import sys

from ortools.sat.python import cp_model


def sym_images(cells):
    maps = [lambda r, c: (r, c), lambda r, c: (c, 8 - r), lambda r, c: (8 - r, 8 - c), lambda r, c: (8 - c, r),
            lambda r, c: (r, 8 - c), lambda r, c: (8 - r, c), lambda r, c: (c, r), lambda r, c: (8 - c, 8 - r)]
    return [tuple(sorted(f(r, c) for r, c in cells)) for f in maps]


def check(cells):
    ghosts = set(cells)
    given = {}
    for r, c in ghosts:
        given[r, c] = sum((r + a, c + b) in ghosts for a in (-1, 0, 1) for b in (-1, 0, 1) if a or b)
    if not all(1 <= n <= 8 for n in given.values()) or 8 not in given.values():
        return None, given
    m = cp_model.CpModel()
    x = {(r, c): m.new_int_var(1, 9, "") for r in range(9) for c in range(9)}
    for i in range(9):
        m.add_all_different([x[i, c] for c in range(9)])
        m.add_all_different([x[r, i] for r in range(9)])
    for br in (0, 3, 6):
        for bc in (0, 3, 6):
            m.add_all_different([x[br + a, bc + b] for a in range(3) for b in range(3)])
    for cell, n in given.items():
        m.add(x[cell] == n)
    s = cp_model.CpSolver()
    s.parameters.num_workers = 1
    if s.solve(m) not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return None, given
    sol = {cell: s.value(v) for cell, v in x.items()}
    m.add_bool_or([_neq(m, x[cell], sol[cell]) for cell in x])
    if s.solve(m) != cp_model.INFEASIBLE:
        return None, given
    return [[sol[r, c] for c in range(9)] for r in range(9)], given


def _neq(m, var, value):
    b = m.new_bool_var("")
    m.add(var != value).only_enforce_if(b)
    return b


def main():
    out_path, inputs = sys.argv[1], sys.argv[2:]
    seen = set()
    kept = dupes = failed = 0
    with open(out_path, "w") as out:
        for path in inputs:
            for line in open(path):
                shape = json.loads(line)["shape"]
                cells = [divmod(i, 9) for i in shape]
                key = min(sym_images(cells))
                if key in seen:
                    dupes += 1
                    continue
                seen.add(key)
                sol, given = check(cells)
                if sol is None:
                    failed += 1
                    print("FAILED", path, sorted(shape))
                    continue
                kept += 1
                out.write(json.dumps({"ghosts": len(shape), "shape": sorted(shape),
                                      "givens": {f"r{r + 1}c{c + 1}": n for (r, c), n in sorted(given.items())},
                                      "solution": sol}) + "\n")
    print(f"verified {kept}, duplicates {dupes}, failed {failed}")


if __name__ == "__main__":
    main()
