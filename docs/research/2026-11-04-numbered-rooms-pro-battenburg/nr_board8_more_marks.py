"""SCRATCH: can one or two more marks make the sixth board plus r3c4 unique?

Negative rule on, the four givens and 14 marks, his digits and colours NOT held, so
no deduction of his limits the answer. Walks every unmarked window and every pair of
them, and classes each as infeasible, unique or not unique. Then, because marks read
only the 32 edge cells, counts the completions of each edge the board allows, with
r6c5 = 9 held, by a solver-free count capped at CAP. One worker; a timeout raises.
"""

import collections
import itertools
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from nr import WINDOWS, build, is_sudoku, marks, outside
from nr_board7 import BOARD, RING
from sudoku_kit.cpsat import SOLVED, UNKNOWN, solver

START = frozenset(BOARD | {(2, 3)})
CAP = 2000
ALL = 0b1111111110


def grids(mark_set, want=2, exclude=()):
    found = list(exclude)
    while len(found) < want + len(exclude):
        m, x, b, _ = build(mark_set, RING)
        for g in found:
            m.AddBoolOr([b[r, c, g[r][c]].Not() for r in range(9) for c in range(9)])
        s = solver(120.0)
        status = s.Solve(m)
        if status == UNKNOWN:
            raise TimeoutError(str(sorted(mark_set)))
        if status not in SOLVED:
            break
        grid = [[s.Value(x[r, c]) for c in range(9)] for r in range(9)]
        assert is_sudoku(grid) and marks(grid) == mark_set
        ring = outside(grid)
        assert all(ring[k] == v for k, v in RING.items())
        found.append(grid)
    return found[len(exclude):]


def classify(mark_set):
    found = grids(mark_set)
    return {0: "infeasible", 1: "unique"}.get(len(found), "not_unique"), found


def edge_of(grid):
    return tuple(
        grid[r][c] for r in range(9) for c in range(9) if r in (0, 8) or c in (0, 8)
    )


def completions(grid):
    """Grids with this edge and r6c5 = 9, capped."""
    rows, cols, boxes = [ALL] * 9, [ALL] * 9, [ALL] * 9
    empty = []
    for r in range(9):
        for c in range(9):
            if r in (0, 8) or c in (0, 8) or (r, c) == (5, 4):
                bit = 1 << grid[r][c]
                rows[r] &= ~bit
                cols[c] &= ~bit
                boxes[r // 3 * 3 + c // 3] &= ~bit
            else:
                empty.append((r, c, r // 3 * 3 + c // 3))
    count = 0

    def search(todo):
        nonlocal count
        if not todo:
            count += 1
            return
        best_i, best_mask, best_n = -1, 0, 10
        for i, (r, c, b) in enumerate(todo):
            mask = rows[r] & cols[c] & boxes[b]
            n = mask.bit_count()
            if n < best_n:
                best_i, best_mask, best_n = i, mask, n
                if n <= 1:
                    break
        if best_n == 0:
            return
        r, c, b = todo[best_i]
        rest = todo[:best_i] + todo[best_i + 1 :]
        mask = best_mask
        while mask and count <= CAP:
            bit = mask & -mask
            mask ^= bit
            rows[r] ^= bit
            cols[c] ^= bit
            boxes[b] ^= bit
            search(rest)
            rows[r] ^= bit
            cols[c] ^= bit
            boxes[b] ^= bit

    search(empty)
    return min(count, CAP + 1)


def main():
    free = [k for k in WINDOWS if k not in START]
    print("unmarked windows:", len(free))
    verdict, _ = classify(START)
    print("no extra mark:", verdict)
    singles = {}
    for k in free:
        singles[k] = classify(START | {k})
    print("one extra:", collections.Counter(v for v, _ in singles.values()), flush=True)
    for k, (v, _) in singles.items():
        if v != "infeasible":
            print("  feasible single", k, v)
    pairs = collections.Counter()
    good = []
    for a, b in itertools.combinations(free, 2):
        v, found = classify(START | {a, b})
        pairs[v] += 1
        if v != "infeasible":
            good.append((a, b, v))
    print("two extra:", pairs, flush=True)
    for item in good[:40]:
        print("  feasible pair", item)

    # Every edge the board allows, by excluding one edge at a time.
    m_edges = {}
    while True:
        m, x, b, _ = build(START, RING)
        for edge in m_edges:
            cells = [
                (r, c) for r in range(9) for c in range(9) if r in (0, 8) or c in (0, 8)
            ]
            m.AddBoolOr([b[r, c, d].Not() for (r, c), d in zip(cells, edge, strict=True)])
        s = solver(120.0)
        status = s.Solve(m)
        if status == UNKNOWN:
            raise TimeoutError("edges")
        if status not in SOLVED:
            break
        grid = [[s.Value(x[r, c]) for c in range(9)] for r in range(9)]
        m_edges[edge_of(grid)] = grid
    print("edges the board allows:", len(m_edges))
    for edge, grid in m_edges.items():
        print("  completions", completions(grid), "of", "".join(map(str, grid[0])), "".join(map(str, grid[8])))


if __name__ == "__main__":
    main()
