"""SCRATCH: next hand steps on the 27-mark board from Chris's picture.

Propagates simple rules only over the border digits and target status, logging each new
fact: a pointer cannot point at a non-target; a target with one route takes it; a cell
with no route is not a target; marks and the negative rule on status; singles and hidden
singles on r1, r9, c1, c9 and the boxes. Then tries each open status and each open
border digit, reporting those that fail by propagation alone. Solver-free apart from the
final check against the 2 borders the marks allow.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_link_t36 import GRID
from nr import CLUES, WINDOWS, clue_name, line_cells, marks
from nr_full_targets_edges import BORDER

BOARD = marks(GRID)
PINK = "r1c7 r2c6 r3c8 r4c7 r4c9 r5c1 r5c6 r5c7 r5c8 r6c2 r6c3 r6c5 r6c9 r7c2 r7c4 r7c6 r7c8 r8c3 r8c5 r8c7 r8c9 r9c4 r9c6 r9c8".split()
GREEN = (
    "r1c6 r1c8 r2c7 r2c8 r2c9 r3c6 r3c7 r3c9 r4c5 r4c6 r4c8 r5c2 r5c3 r5c4 r5c5 r5c9 r6c1 r6c4 r6c6 r6c7 r6c8 "
    "r7c1 r7c3 r7c5 r7c7 r7c9 r8c1 r8c2 r8c4 r8c6 r8c8 r9c2 r9c3 r9c5 r9c7 r9c9"
).split()
PENCIL = {
    "r1c9": "168", "r5c1": "1678", "r6c1": "2359", "r7c1": "2468", "r8c1": "3579", "r5c9": "2349",
    "r6c9": "1578", "r7c9": "2468", "r8c9": "1357", "r9c6": "1358", "r9c8": "1357", "r9c9": "2469",
}
CELLS = [(r, c) for r in range(9) for c in range(9)]
LINES = {k: line_cells(k) for k in CLUES}
UNITS = [[(0, c) for c in range(9)], [(8, c) for c in range(9)], [(r, 0) for r in range(9)], [(r, 8) for r in range(9)]]
BOXES = [
    [(br * 3 + r, bc * 3 + c) for r in range(3) for c in range(3) if (br * 3 + r, bc * 3 + c) in set(BORDER)]
    for br in range(3)
    for bc in range(3)
]
ROUTES = {cell: [] for cell in CELLS}
for key, cells in LINES.items():
    for i, cell in enumerate(cells):
        ROUTES[cell].append((cells[0], i + 1, key))


def cell(name):
    return int(name[1]) - 1, int(name[3]) - 1


def nm(k):
    return f"r{k[0] + 1}c{k[1] + 1}"


class Fail(Exception):
    pass


def start():
    cand = {k: set(range(1, 10)) for k in BORDER}
    for name, text in PENCIL.items():
        cand[cell(name)] = {int(d) for d in text}
    status = dict.fromkeys(CELLS)
    for n in PINK:
        status[cell(n)] = 1
    for n in GREEN:
        status[cell(n)] = 0
    return cand, status


def propagate(cand, status, log):
    def remove(k, d, why):
        if d in cand[k]:
            cand[k].discard(d)
            log.append(f"{nm(k)} != {d} ({why})")
            if not cand[k]:
                raise Fail(f"{nm(k)} has no digit")
            return True
        return False

    def set_status(k, v, why):
        if status[k] is None:
            status[k] = v
            log.append(f"{nm(k)} {'target' if v else 'not a target'} ({why})")
            return True
        if status[k] != v:
            raise Fail(f"{nm(k)} both target and not ({why})")
        return False

    changed = True
    while changed:
        changed = False
        for key, cells in LINES.items():
            p = cells[0]
            for d in sorted(cand[p]):
                if status[cells[d - 1]] == 0:
                    changed |= remove(p, d, f"{clue_name(key)} would hit non-target {nm(cells[d - 1])}")
        for k in CELLS:
            routes = [(p, d) for p, d, _ in ROUTES[k] if d in cand[p]]
            if not routes:
                changed |= set_status(k, 0, "no route")
            if status[k] == 1:
                distinct = {route for route in routes}
                if not distinct:
                    raise Fail(f"{nm(k)} target with no route")
                if len(distinct) == 1:
                    p, d = next(iter(distinct))
                    for other in sorted(cand[p] - {d}):
                        changed |= remove(p, other, f"only route to target {nm(k)}")
            # A pointer with one digit makes its target.
        for line in [[(r, c) for c in range(9)] for r in range(9)] + [[(r, c) for r in range(9)] for c in range(9)]:
            known = sum(status[x] == 1 for x in line)
            if known > 4:
                raise Fail("line with 5 targets")
            if known == 4:
                for x in line:
                    if status[x] is None:
                        changed |= set_status(x, 0, "line already has 4 targets")
        full = []
        for i in range(9):
            row = [(i, c) for c in range(9)]
            col = [(r, i) for r in range(9)]
            for line in (row, col):
                if sum(status[x] == 1 for x in line) == 4:
                    full.extend(line)
        for k in set(full):
            if status[k] != 1:
                continue
            sure = [(p, d) for p, d, _ in ROUTES[k] if cand[p] == {d}]
            if sure:
                for p, d, _ in ROUTES[k]:
                    if (p, d) != sure[0] and d in cand[p] and cand[p] != {d}:
                        changed |= remove(p, d, f"{nm(k)} already hit by {nm(sure[0][0])} = {sure[0][1]}, and its line has 4 targets")
        for key, cells in LINES.items():
            if len(cand[cells[0]]) == 1:
                d = next(iter(cand[cells[0]]))
                changed |= set_status(cells[d - 1], 1, f"{clue_name(key)} {nm(cells[0])} = {d}")
        for r, c in WINDOWS:
            w = [(r, c), (r, c + 1), (r + 1, c), (r + 1, c + 1)]
            a, f, d, e = (status[x] for x in w)
            if (r, c) in BOARD:
                for x, y in ((w[0], w[3]), (w[1], w[2])):
                    if status[x] is not None:
                        changed |= set_status(y, status[x], f"mark {nm((r, c))}")
                    if status[y] is not None:
                        changed |= set_status(x, status[y], f"mark {nm((r, c))}")
                for x, y in ((w[0], w[1]), (w[1], w[0])):
                    if status[x] is not None:
                        changed |= set_status(y, 1 - status[x], f"mark {nm((r, c))}")
            else:
                pattern = {(1, 0, 0, 1), (0, 1, 1, 0)}
                values = [a, f, d, e]
                if values.count(None) == 1:
                    i = values.index(None)
                    for v in (0, 1):
                        trial = list(values)
                        trial[i] = v
                        if tuple(trial) in pattern:
                            changed |= set_status(w[i], 1 - v, f"unmarked {nm((r, c))}")
                elif None not in values and tuple(values) in pattern:
                    raise Fail(f"unmarked {nm((r, c))} is a checkerboard")
        for unit in UNITS + BOXES:
            for k in unit:
                if len(cand[k]) == 1:
                    d = next(iter(cand[k]))
                    for other in unit:
                        if other != k:
                            changed |= remove(other, d, f"{nm(k)} = {d}")
        for unit in UNITS:
            for d in range(1, 10):
                places = [k for k in unit if d in cand[k]]
                if not places:
                    raise Fail(f"no place for {d}")
                if len(places) == 1:
                    for other in sorted(cand[places[0]] - {d}):
                        changed |= remove(places[0], other, f"only {d} on its line")
    return cand, status


def copy(cand, status):
    return {k: set(v) for k, v in cand.items()}, dict(status)


def main():
    cand, status = start()
    propagate(cand, status, [])
    print("border after simple rules:", {nm(k): "".join(map(str, sorted(v))) for k, v in cand.items() if len(v) <= 4})
    for round_no in range(1, 40):
        fails = []
        for k in CELLS:
            if status[k] is None:
                for v in (1, 0):
                    a, b = copy(cand, status)
                    b[k] = v
                    steps = []
                    try:
                        propagate(a, b, steps)
                    except Fail as e:
                        fails.append((len(steps), f"{nm(k)} {'target' if v else 'not a target'}", str(e), steps, ("s", k, 1 - v)))
        for k in BORDER:
            if len(cand[k]) > 1:
                for d in sorted(cand[k]):
                    a, b = copy(cand, status)
                    a[k] = {d}
                    steps = []
                    try:
                        propagate(a, b, steps)
                    except Fail as e:
                        fails.append((len(steps), f"{nm(k)} = {d}", str(e), steps, ("d", k, d)))
        if not fails:
            print("no more one-step tries fail")
            break
        fails.sort(key=lambda x: x[0])
        print(f"round {round_no}: {len(fails)} tries fail; shortest:")
        for n, label, why, steps, _ in fails[:4]:
            print(f"  {label}: {n} steps, {why}")
            print("     ", " | ".join(steps[:9]))
        _, label, _, _, action = fails[0]
        kind, k, v = action
        if kind == "s":
            status[k] = v
        else:
            cand[k].discard(v)
        propagate(cand, status, [])
        print("  applied: not", label)
    print("border:", {nm(k): "".join(map(str, sorted(v))) for k, v in cand.items() if len(v) < 9})
    print("open status:", [nm(k) for k in CELLS if status[k] is None])


if __name__ == "__main__":
    main()
