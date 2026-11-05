"""Which one-mark changes to a board let a line's two end clues match, negative rule on.

Two clues at both ends of a line are equal exactly when they read the same cell, which for a
row means its c1 and c9 digits sum to 10 and for a column its r1 and r9 digits do. For the
board and each variant with one mark removed or added: feasibility, the borders allowed
(enumerated to CAP), and each line where the ends sum to 10 in some border, with "always"
when they do in every border. Every such line is confirmed on the repo's full model, and the
witness grid is re-read by the reader. One worker; a timeout raises.

Usage: nr_pair_variants.py BOARD_JSON OUT
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from nr import WINDOWS, build, is_sudoku, marks, outside
from nr_full_targets_edges import BORDER, model
from ortools.sat.python import cp_model
from sudoku_kit.cpsat import SOLVED, UNKNOWN, solver

CAP = 3000
LINES = [("r", i) for i in range(9)] + [("c", i) for i in range(9)]


def nm(k):
    return f"r{k[0] + 1}c{k[1] + 1}"


def ends(line):
    kind, i = line
    return ((i, 0), (i, 8)) if kind == "r" else ((0, i), (8, i))


def lname(line):
    return f"{line[0]}{line[1] + 1}"


class Keep(cp_model.CpSolverSolutionCallback):
    def __init__(self, b):
        super().__init__()
        self.b, self.rows = b, []

    def on_solution_callback(self):
        self.rows.append({k: next(d for d in range(1, 10) if self.Value(self.b[k, d])) for k in BORDER})
        if len(self.rows) >= CAP:
            self.StopSearch()


def borders(board):
    m, b = model(board, True)
    s = solver(60.0)
    s.parameters.enumerate_all_solutions = True
    s.parameters.num_workers = 1
    keep = Keep(b)
    status = s.Solve(m, keep)
    complete = s.StatusName(status) == "OPTIMAL" and len(keep.rows) < CAP
    return keep.rows, complete


def confirm(board, line):
    m, x, _, _ = build(board, {})
    a, z = ends(line)
    m.Add(x[a] + x[z] == 10)
    s = solver(120.0)
    status = s.Solve(m)
    if status == UNKNOWN:
        raise TimeoutError(lname(line))
    if status not in SOLVED:
        return None
    grid = [[s.Value(x[r, c]) for c in range(9)] for r in range(9)]
    assert is_sudoku(grid) and marks(grid) == board
    ring = outside(grid)
    kind, i = line
    pair = (("L", i), ("R", i)) if kind == "r" else (("T", i), ("B", i))
    assert ring[pair[0]] == ring[pair[1]]
    return ring[pair[0]]


def main(path, out):
    data = json.loads(Path(path).read_text())
    base = frozenset((int(n[1]) - 1, int(n[3]) - 1) for n in data["marks"])
    variants = [("as is", base)]
    variants += [(f"remove {nm(k)}", base - {k}) for k in sorted(base)]
    variants += [(f"add {nm(k)}", base | {k}) for k in WINDOWS if k not in base]
    with open(out, "w") as log:
        for label, board in variants:
            rows, complete = borders(board)
            if not rows:
                continue
            found = {}
            for line in LINES:
                a, z = ends(line)
                hits = sum(r[a] + r[z] == 10 for r in rows)
                if hits:
                    found[line] = "always" if hits == len(rows) and complete else f"{hits} of {len(rows)}{'' if complete else '+'}"
            confirmed = {}
            for line, how in found.items():
                value = confirm(board, line)
                if value is not None:
                    confirmed[lname(line)] = (how, value)
            others = {k: v for k, v in confirmed.items() if k != "r9"}
            record = {"variant": label, "borders": len(rows), "complete": complete, "lines": confirmed}
            log.write(json.dumps(record) + "\n")
            log.flush()
            if others or label == "as is":
                print(label, "| borders", f"{len(rows)}{'' if complete else '+'}", "| lines", confirmed, flush=True)
    print("done", flush=True)


if __name__ == "__main__":
    main(*sys.argv[1:])
