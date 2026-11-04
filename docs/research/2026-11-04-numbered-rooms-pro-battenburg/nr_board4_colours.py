"""SCRATCH: can more marks make Chris's third-board colouring work?

Marks only add constraints, so the colouring must first hold with unmarked windows
free. The colours become soft: minimise how many change. Each smallest set of
changes is listed, up to CAP, with the fewest extra marks a grid needs for it. Each
grid is re-read by the reader. Digits r1c1=9, r9c1=6, r9c6=4 are held. One worker.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from nr import WINDOWS, is_sudoku, marks, outside, show, targets
from nr_board4 import DIGITS, GREEN, MARKS, PINK, RING, cell
from nr_board4_windows import model, name, status_of
from sudoku_kit.cpsat import SOLVED

CAP = 12


def changes_model(digits=DIGITS):
    colours = [(n, 1) for n in PINK] + [(n, 0) for n in GREEN]
    m, x, w = model((), digits)
    t = m.target_vars
    changed = {}
    for n, want in colours:
        lit = t[cell(n)]
        changed[n] = lit.Not() if want else lit
    return m, x, w, changed


def main():
    m, _, _, changed = changes_model()
    m.Minimize(sum(changed.values()))
    s, status = status_of(m)
    print("fewest colour changes:", s.StatusName(status), s.ObjectiveValue(), s.BestObjectiveBound())
    size = round(s.ObjectiveValue())
    seen = []
    while len(seen) < CAP:
        m, x, w, changed = changes_model()
        m.Add(sum(changed.values()) == size)
        for old in seen:
            m.AddBoolOr([changed[n].Not() for n in old])
        s, status = status_of(m)
        if status not in SOLVED:
            print(f"all {len(seen)} smallest sets listed")
            break
        current = sorted(n for n, lit in changed.items() if s.BooleanValue(lit))
        seen.append(current)

        m, x, w, changed = changes_model()
        for n, lit in changed.items():
            m.Add(lit == (1 if n in current else 0))
        m.Minimize(sum(w[k] for k in WINDOWS if k not in MARKS))
        s, status = status_of(m)
        grid = [[s.Value(x[r, c]) for c in range(9)] for r in range(9)]
        assert is_sudoku(grid) and MARKS <= marks(grid)
        ring = outside(grid)
        assert all(ring[c] == v for c, v in RING.items())
        t = targets(grid)
        extra = [name(k) for k in sorted(marks(grid) - MARKS)]
        flips = [f"{n}->{'pink' if cell(n) in t else 'green'}" for n in current]
        print(flips, s.StatusName(status), "extra marks", extra, flush=True)
        print(show(grid), flush=True)
    else:
        print(f"listing capped at {CAP}")


if __name__ == "__main__":
    main()
