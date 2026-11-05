"""Finishing clues a solver could not have used before a given position, negative rule on.

A clue is "late" when its first cell is unsolved in the position (option 1), and "ahead"
when it reads a cell unsolved in the position (option 2). Lists every grid of the board's
given clues, then tries clue sets: first late clues only, then late and ahead clues with as
many late ones as possible. A set counts when it leaves exactly one grid of the board's
clues, and that grid agrees with every digit of the position. Exhaustive up to MAX_K.

With AVOID, such as 5,6, instead searches clues that sit on none of those rows and read no
cell in them, first any such clue, then only those that also read unsolved cells.

Usage: nr_late_clues.py BOARD_JSON POSITION_JSON MAX_K [AVOID]
"""

import itertools
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from nr import CLUES, clue_name, line_cells, outside
from nr_full_targets_edges import BORDER, model
from nr_outside_finish import all_grids
from ortools.sat.python import cp_model
from sudoku_kit.cpsat import solver


class Keep(cp_model.CpSolverSolutionCallback):
    def __init__(self, b):
        super().__init__()
        self.b, self.rows = b, []

    def on_solution_callback(self):
        self.rows.append("".join(str(next(d for d in range(1, 10) if self.Value(self.b[k, d]))) for k in BORDER))


def cell(name):
    return int(name[1]) - 1, int(name[3]) - 1


def main(board_path, position_path, max_k, avoid=""):
    max_k = int(max_k)
    data = json.loads(Path(board_path).read_text())
    known = {cell(k): v for k, v in json.loads(Path(position_path).read_text())["digits"].items()}
    board = frozenset(cell(n) for n in data["marks"])
    m, b = model(board, True)
    s = solver(120.0)
    s.parameters.enumerate_all_solutions = True
    s.parameters.num_workers = 1
    keep = Keep(b)
    assert s.StatusName(s.Solve(m, keep)) == "OPTIMAL"
    grids = np.concatenate([np.array(all_grids(t, []), dtype=np.uint8) for t in keep.rows])
    cols = {}
    hit = {}
    for clue in CLUES:
        cells = line_cells(clue)
        first = grids[:, cells[0][0], cells[0][1]].astype(int)
        where = np.array(cells)[first - 1]
        hit[clue] = where
        cols[clue] = grids[np.arange(len(grids)), where[:, 0], where[:, 1]]
    keep_rows = np.ones(len(grids), bool)
    for name, value in data.get("outside", {}).items():
        keep_rows &= cols[(name[0], int(name[1:]) - 1)] == value
    grids = grids[keep_rows]
    cols = {c: v[keep_rows] for c, v in cols.items()}
    hit = {c: v[keep_rows] for c, v in hit.items()}
    agree = np.ones(len(grids), bool)
    for (r, c), v in known.items():
        agree &= grids[:, r, c] == v
    print("grids of the given clues", len(grids), "agreeing with the position", int(agree.sum()), flush=True)
    given = {(k[0], int(k[1:]) - 1) for k in data.get("outside", {})}
    late = [c for c in CLUES if c not in given and line_cells(c)[0] not in known and len(np.unique(cols[c])) > 1]
    ahead = []
    for c in CLUES:
        if c in given or c in late or len(np.unique(cols[c])) < 2:
            continue
        rows = np.flatnonzero(agree)
        if all((int(hit[c][i][0]), int(hit[c][i][1])) not in known for i in rows):
            ahead.append(c)
    print("late clues", [clue_name(c) for c in late])
    print("ahead clues", [clue_name(c) for c in ahead], flush=True)

    def finish(combo):
        key = np.zeros(len(grids), dtype=np.int64)
        for c in combo:
            key = key * 10 + cols[c].astype(np.int64)
        values, inverse, counts = np.unique(key, return_inverse=True, return_counts=True)
        alone = counts[inverse] == 1
        return [int(i) for i in np.flatnonzero(alone & agree)]

    for k in range(1, max_k + 1):
        hits = [(combo, finish(combo)) for combo in itertools.combinations(late, k)]
        hits = [(combo, f) for combo, f in hits if f]
        print(f"option 1, {k} late clues:", len(hits), "sets", flush=True)
        for combo, found in hits:
            for i in found:
                print("  ", [f"{clue_name(c)}={cols[c][i]}" for c in combo], " ".join("".join(map(str, r)) for r in grids[i]))
    if avoid:
        rows_out = {int(r) - 1 for r in avoid.split(",")}
        agreeing = np.flatnonzero(agree)

        def clear(c):
            on_line = c[0] in "LR" and c[1] in rows_out
            return not on_line and all(int(hit[c][i][0]) not in rows_out for i in agreeing)

        free = [c for c in CLUES if c not in given and len(np.unique(cols[c])) > 1 and clear(c)]
        print("clues clear of rows", avoid, [clue_name(c) for c in free], flush=True)
        for label, pool in (("any such clue", free), ("also reading unsolved cells", [c for c in free if c in ahead])):
            for k in range(1, max_k + 1):
                found_sets = [(combo, finish(combo)) for combo in itertools.combinations(pool, k)]
                found_sets = [(combo, f) for combo, f in found_sets if f]
                if found_sets:
                    print(f"{label}: fewest {k}, {len(found_sets)} sets", flush=True)
                    for combo, found in found_sets[:20]:
                        for i in found:
                            print("  ", [f"{clue_name(c)}={cols[c][i]}" for c in combo], " ".join("".join(map(str, r)) for r in grids[i]))
                    break
                print(f"{label}: none with {k}", flush=True)
        return
    pool = late + ahead
    for k in range(1, max_k + 1):
        best = []
        for combo in itertools.combinations(pool, k):
            found = finish(combo)
            if found:
                best.append((sum(c in late for c in combo), combo, found))
        if best:
            most = max(n for n, _, _ in best)
            print(f"option 2 with 1, {k} clues: {len(best)} sets, most late clues in one set {most}", flush=True)
            for n, combo, found in sorted(best, key=lambda x: -x[0])[:15]:
                for i in found:
                    print("  ", n, "late", [f"{clue_name(c)}={cols[c][i]}" for c in combo], " ".join("".join(map(str, r)) for r in grids[i]))
            return
        print(f"option 2 with 1, {k} clues: none", flush=True)


if __name__ == "__main__":
    main(*sys.argv[1:])
