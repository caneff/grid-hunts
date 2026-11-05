"""SCRATCH: can outside digits alone finish a board, and with how few more?

Negative on. Takes the fixed border and the pinned inner cells of a board whose target set
is fixed, lists every grid, and groups grids by their 36 outside digits. A grid alone in
its group is fixed by outside digits. For those, an exact minimum hitting set over the
other grids gives the fewest extra clues. The best is proven on the repo's full model
with no second grid. One worker.

Usage: nr_outside_finish.py BOARD_JSON BORDER PINS   e.g. board21.json 3642... 625,276
"""

import collections
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from nr import CLUES, clue_name, is_sudoku, marks, outside, targets
from nr_check import Board
from nr_full_targets_edges import BORDER
from ortools.sat.python import cp_model
from sudoku_kit.cpsat import solver


def all_grids(border, pins):
    grid = [[0] * 9 for _ in range(9)]
    rows, cols, boxes = [0] * 9, [0] * 9, [0] * 9

    def put(r, c, d):
        grid[r][c] = d
        bit = 1 << d
        rows[r] |= bit
        cols[c] |= bit
        boxes[r // 3 * 3 + c // 3] |= bit

    for (r, c), d in zip(BORDER, border, strict=True):
        put(r, c, int(d))
    for r, c, d in pins:
        put(r, c, d)
    empty = [(r, c) for r in range(9) for c in range(9) if not grid[r][c]]
    found = []

    def search(todo):
        if not todo:
            found.append([row[:] for row in grid])
            return
        best, best_n, best_mask = -1, 10, 0
        for i, (r, c) in enumerate(todo):
            mask = 0b1111111110 & ~(rows[r] | cols[c] | boxes[r // 3 * 3 + c // 3])
            n = mask.bit_count()
            if n < best_n:
                best, best_n, best_mask = i, n, mask
                if n <= 1:
                    break
        if best_n == 0:
            return
        r, c = todo[best]
        rest = todo[:best] + todo[best + 1 :]
        b = r // 3 * 3 + c // 3
        for d in range(1, 10):
            if best_mask >> d & 1:
                bit = 1 << d
                grid[r][c] = d
                rows[r] |= bit
                cols[c] |= bit
                boxes[b] |= bit
                search(rest)
                rows[r] ^= bit
                cols[c] ^= bit
                boxes[b] ^= bit
                grid[r][c] = 0

    search(empty)
    return found


def fewest(index, rings, given):
    """Fewest extra outside cells that separate rings[index] from every other grid."""
    m = cp_model.CpModel()
    pick = {clue: m.NewBoolVar("pick") for clue in CLUES}
    me = rings[index]
    for i, ring in enumerate(rings):
        if i != index:
            m.AddBoolOr([pick[clue] for clue in CLUES if ring[clue] != me[clue]])
    for clue in given:
        m.Add(pick[clue] == 1)
    m.Minimize(sum(pick.values()))
    s = solver(30.0)
    status = s.StatusName(s.Solve(m))
    return status, [clue for clue in CLUES if s.Value(pick[clue])]


def main(path, border, pin_text):
    data = json.loads(Path(path).read_text())
    board = frozenset((int(n[1]) - 1, int(n[3]) - 1) for n in data["marks"])
    pins = [(int(p[0]) - 1, int(p[1]) - 1, int(p[2])) for p in pin_text.split(",")]
    grids = all_grids(border, pins)
    print("grids", len(grids), flush=True)
    assert all(is_sudoku(g) for g in grids)
    assert all(marks(g) == board for g in grids)
    assert len({frozenset(targets(g)) for g in grids}) == 1
    given = {(k[0], int(k[1:]) - 1): v for k, v in data["outside"].items()}
    rings = [outside(g) for g in grids]
    assert all(all(r[k] == v for k, v in given.items()) for r in rings)
    groups = collections.Counter(tuple(r[c] for c in CLUES) for r in rings)
    alone = [i for i, r in enumerate(rings) if groups[tuple(r[c] for c in CLUES)] == 1]
    print("groups", len(groups), "grids fixed by all 36", len(alone), "largest group", max(groups.values()), flush=True)
    inner = sorted({c for c in targets(grids[0]) if 0 < c[0] < 8 and 0 < c[1] < 8})
    print("inner target cells", len(inner), [f"r{r + 1}c{c + 1}" for r, c in inner])
    if not alone:
        return
    tally = collections.Counter()
    best = None
    for i in alone:
        status, chosen = fewest(i, rings, given)
        assert status == "OPTIMAL", status
        extra = len(chosen) - len(given)
        tally[extra] += 1
        if best is None or extra < best[0]:
            best = (extra, i, chosen)
            print("  best so far", extra, flush=True)
    print("extra clues needed, per grid fixed:", sorted(tally.items()), flush=True)
    extra, i, chosen = best
    grid = grids[i]
    print("best extra", extra, "grid", " ".join("".join(map(str, row)) for row in grid))
    names = {clue_name(c): rings[i][c] for c in chosen}
    print("clues", names)
    full = Board({"marks": data["marks"], "outside": names}, True)
    first = full.solve([])
    assert first == grid

    def block(m, x, b, t):
        m.AddBoolOr([b[r, c, grid[r][c]].Not() for r in range(9) for c in range(9)])

    print("second grid on the full model:", bool(full.solve([], block)), flush=True)


if __name__ == "__main__":
    main(*sys.argv[1:])
