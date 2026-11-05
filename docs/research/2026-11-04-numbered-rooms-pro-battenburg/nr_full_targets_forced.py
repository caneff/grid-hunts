"""SCRATCH: what the 36-target grid's 13 marks force, across all their solutions.

Reads the per-border digit masks that count_fills.c writes to stderr. Reports each
cell's digits, each cell's target status and each outside cell's digits. A target
depends only on the border, so status comes from the border alone, and an outside digit
is whatever its target cell can hold under that border.

Usage: nr_full_targets_forced.py MASKS_FILE
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from nr import CLUES, clue_name, line_cells, targets
from nr_full_targets_edges import BORDER, GRID


def digits(mask):
    return [d for d in range(1, 10) if mask >> d & 1]


def main(path):
    union = {(r, c): 0 for r in range(9) for c in range(9)}
    target_yes = {cell: 0 for cell in union}
    target_no = {cell: 0 for cell in union}
    ring = {clue: 0 for clue in CLUES}
    borders = 0
    known = "".join(str(GRID[r][c]) for r, c in BORDER)
    for line in Path(path).read_text().splitlines():
        parts = line.split()
        text, inner = parts[0], [int(v) for v in parts[1:]]
        assert len(text) == 32 and len(inner) == 49
        assert all(inner), text
        borders += 1
        masks = {cell: 1 << int(d) for cell, d in zip(BORDER, text, strict=True)}
        cells = [(r, c) for r in range(1, 8) for c in range(1, 8)]
        masks.update(zip(cells, inner, strict=True))
        hit = set()
        for clue in CLUES:
            line_of = line_cells(clue)
            pointer = digits(masks[line_of[0]])[0]
            target = line_of[pointer - 1]
            hit.add(target)
            ring[clue] |= masks[target]
        if text == known:
            assert hit == targets(GRID)
        for cell in union:
            union[cell] |= masks[cell]
            if cell in hit:
                target_yes[cell] += 1
            else:
                target_no[cell] += 1
    print("borders", borders)
    print("digits (. = 5 or more options)")
    for r in range(9):
        row = []
        for c in range(9):
            options = digits(union[r, c])
            row.append("".join(map(str, options)) if len(options) <= 4 else ".")
        print(f"r{r + 1}", " ".join(f"{v:>5}" for v in row))
    forced = [
        (f"r{r + 1}c{c + 1}", digits(union[r, c])[0])
        for r in range(9)
        for c in range(9)
        if len(digits(union[r, c])) == 1
    ]
    print("forced digits", len(forced), forced)
    print("status (X target, . not, ? open)")
    for r in range(9):
        print("".join("X" if not target_no[r, c] else "." if not target_yes[r, c] else "?" for c in range(9)))
    print("forced target", sum(not v for v in target_no.values()), "forced not", sum(not v for v in target_yes.values()))
    print("outside with 1 option", {clue_name(k): digits(v)[0] for k, v in ring.items() if len(digits(v)) == 1})
    print("outside with 2 to 4", {clue_name(k): digits(v) for k, v in ring.items() if 1 < len(digits(v)) <= 4})


if __name__ == "__main__":
    main(sys.argv[1])
