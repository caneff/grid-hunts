"""The exact fewest outside digits that make a mark set unique, negative rule on.

Lists every grid of every border the marks allow, reads each outside cell's digit column
for them, merges clues that always agree, then tries every set of k clues for k = 1, 2,
... A set finishes a grid when that grid's digits on it occur once. Stops after the first k
with a hit and lists them to OUT. Exhaustive over the listed grids, so a miss at k is a
proof for k. Grids are re-read by the reader for a sample and every hit. One worker.

Usage: nr_min_outside.py BOARD_JSON MAX_K OUT
"""

import itertools
import json
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from nr import CLUES, clue_name, is_sudoku, line_cells, marks, outside
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


def main(path, max_k, out):
    max_k = int(max_k)
    data = json.loads(Path(path).read_text())
    board = frozenset((int(n[1]) - 1, int(n[3]) - 1) for n in data["marks"])
    m, b = model(board, True)
    s = solver(120.0)
    s.parameters.enumerate_all_solutions = True
    s.parameters.num_workers = 1
    keep = Keep(b)
    assert s.StatusName(s.Solve(m, keep)) == "OPTIMAL"
    print("borders", len(keep.rows), flush=True)
    chunks = []
    for text in keep.rows:
        grids = np.array(all_grids(text, []), dtype=np.uint8)
        print("  border", text, len(grids), flush=True)
        if len(grids):
            chunks.append(grids)
    grids = np.concatenate(chunks)
    print("grids", len(grids), flush=True)
    rng = np.random.default_rng(0)
    for i in rng.integers(0, len(grids), 200):
        g = grids[i].tolist()
        assert is_sudoku(g) and marks(g) == board
    columns = {}
    for clue in CLUES:
        cells = line_cells(clue)
        first = grids[:, cells[0][0], cells[0][1]]
        rows = np.arange(len(grids))
        targets = np.array(cells)[first.astype(int) - 1]
        columns[clue] = grids[rows, targets[:, 0], targets[:, 1]]
    for i in rng.integers(0, len(grids), 200):
        ring = outside(grids[i].tolist())
        assert all(ring[c] == columns[c][i] for c in CLUES)
    seen = {}
    for clue, col in columns.items():
        if len(np.unique(col)) > 1:
            seen.setdefault(col.tobytes(), []).append(clue)
    names = list(seen.values())
    cols = [columns[group[0]].astype(np.int64) for group in names]
    print("distinct informative clues", len(cols), [[clue_name(c) for c in g] for g in names], flush=True)
    with open(out, "w") as log:
        for k in range(1, max_k + 1):
            start = time.time()
            hits = 0
            sets = 0
            for combo in itertools.combinations(range(len(cols)), k):
                sets += 1
                key = np.zeros(len(grids), dtype=np.int64)
                for i in combo:
                    key = key * 10 + cols[i]
                counts = np.bincount(key, minlength=10**k)
                alone = np.flatnonzero(counts == 1)
                if len(alone):
                    hits += 1
                    log.write(
                        json.dumps({"k": k, "clues": [[clue_name(c) for c in names[i]] for i in combo], "keys": len(alone)}) + "\n"
                    )
                    log.flush()
                    if hits <= 20:
                        idx = int(np.flatnonzero(np.isin(key, alone[:1]))[0])
                        grid = grids[idx].tolist()
                        ring = outside(grid)
                        print(k, [f"{clue_name(names[i][0])}={ring[names[i][0]]}" for i in combo], "grids alone", len(alone),
                              " ".join("".join(map(str, r)) for r in grid), flush=True)
            print(f"k={k}: {sets} sets, {hits} leave some grid alone, {time.time() - start:.0f} s", flush=True)
            if hits:
                print("minimum", k, flush=True)
                return
    print("no hit up to", max_k, flush=True)


if __name__ == "__main__":
    main(*sys.argv[1:])
