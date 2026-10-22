"""The Doppelganger + Full Rank rule reader (spec #66): pure Python, no
solver. The rules and their sources:
`docs/research/2026-10-22-doppelganger-full-rank-rules.md`.

`read(grid, box)` reads a full n x n grid of digits 0..n with boxes `box`
(rows, columns) tall and wide, and returns a `Reading`:

- `violations`, one sentence per broken rule, empty when the grid keeps
  every Doppelganger rule: each row, column and box holds one 0 and n - 1
  different digits of 1..n; no two rows miss the same digit, nor two
  columns, nor two boxes; a 0's row, column and box miss three different
  digits.
- `missing`, each unit's missing digit by unit name (r1, c1, b1; boxes
  numbered across, then down), None for a unit that does not miss exactly
  one digit.
- `numbers`, the 4n numbers by place, a place being (line, end): a row's
  `left` or `right` end, a column's `top` or `bottom`. Each is read away
  from its end, a 0 read as the digit 0, and kept as its digit string.
- `ranks`, each number's rank by place: 1 plus how many of the 4n are
  strictly smaller, so equal numbers share a rank and the next is skipped.

`Reading.broken_clues(clues)` names each rank clue (a board file's
`{"line", "end", "rank"}`) whose place ranks otherwise.
"""

from typing import NamedTuple

ENDS = {"r": ("left", "right"), "c": ("top", "bottom")}
# Equal-length digit strings compare as the numbers they spell, which is why
# `numbers` keeps strings: a leading 0 stays, and n <= 9 keeps one character
# per digit.


def houses(n, box):
    """Rows, columns and boxes as lists of (row, column) cells from 0, each
    with its unit name."""
    bh, bw = box
    if bh * bw != n:
        raise ValueError(f"{bh}x{bw} boxes do not hold {n} cells")
    rows = {f"r{r + 1}": [(r, c) for c in range(n)] for r in range(n)}
    cols = {f"c{c + 1}": [(r, c) for r in range(n)] for c in range(n)}
    boxes = {}
    for br in range(0, n, bh):
        for bc in range(0, n, bw):
            cells = [(br + dr, bc + dc) for dr in range(bh) for dc in range(bw)]
            boxes[f"b{len(boxes) + 1}"] = cells
    return rows, cols, boxes


def cell_name(cell):
    return f"r{cell[0] + 1}c{cell[1] + 1}"


def parse_cell(name):
    """The (row, column) from 0 of a cell named rNcM."""
    row, col = name.removeprefix("r").split("c")
    return int(row) - 1, int(col) - 1


def place_name(place):
    """A place in words, as the reports print it: `c1 from the top`."""
    line, end = place
    return f"{line} from the {end}"


def line_cells(n, place):
    """The cells of a place's line in reading order, away from its end."""
    line, end = place
    index = int(line[1:]) - 1
    if line[0] == "r":
        cells = [(index, c) for c in range(n)]
    else:
        cells = [(r, index) for r in range(n)]
    return cells if end in ("left", "top") else cells[::-1]


def places(n):
    """The 4n places, rows first, each line's two ends together."""
    return [
        (f"{kind}{i + 1}", end) for kind in "rc" for i in range(n) for end in ENDS[kind]
    ]


class Reading(NamedTuple):
    violations: list
    missing: dict
    numbers: dict
    ranks: dict

    def broken_clues(self, clues):
        broken = []
        for clue in clues:
            place = (clue["line"], clue["end"])
            if self.ranks[place] != clue["rank"]:
                broken.append(
                    f"{place_name(place)} ranks {self.ranks[place]}, not {clue['rank']}"
                )
        return broken


def read(grid, box):
    n = len(grid)
    rows, cols, boxes = houses(n, box)
    violations = []
    for r, row in enumerate(grid):
        for c, digit in enumerate(row):
            if not 0 <= digit <= n:
                violations.append(f"{cell_name((r, c))} holds {digit}, outside 0..{n}")

    missing = {}
    for units in (rows, cols, boxes):
        for name, cells in units.items():
            digits = [grid[r][c] for r, c in cells]
            violations.extend(
                f"{name} holds {d} twice"
                for d in sorted(set(digits))
                if digits.count(d) > 1
            )
            if 0 not in digits:
                violations.append(f"{name} has no 0")
            absent = set(range(1, n + 1)) - set(digits)
            missing[name] = absent.pop() if len(absent) == 1 else None

    for units in (rows, cols, boxes):
        first = {}
        for name in units:
            digit = missing[name]
            if digit is None:
                continue
            if digit in first:
                violations.append(f"{first[digit]} and {name} both miss {digit}")
            else:
                first[digit] = name

    box_of = {cell: name for name, cells in boxes.items() for cell in cells}
    for r, row in enumerate(grid):
        for c, digit in enumerate(row):
            if digit != 0:
                continue
            three = (missing[f"r{r + 1}"], missing[f"c{c + 1}"], missing[box_of[r, c]])
            if None not in three and len(set(three)) < 3:
                violations.append(
                    f"{cell_name((r, c))} holds 0 and its row, column and box miss "
                    + ", ".join(map(str, three))
                )

    numbers = {
        place: "".join(str(grid[r][c]) for r, c in line_cells(n, place))
        for place in places(n)
    }
    ranks = {
        place: 1 + sum(other < mine for other in numbers.values())
        for place, mine in numbers.items()
    }
    return Reading(violations, missing, numbers, ranks)
