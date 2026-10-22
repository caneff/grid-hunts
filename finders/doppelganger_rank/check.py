"""Check a Doppelganger + Full Rank board: the status of its rank clues, a
solution with every rank and missing digit (two for not_unique), and
whether each mark holds in every solution.

    uv run finders/doppelganger_rank/check.py BOARD [--time-limit S]

BOARD is a hand-written JSON board file:

    {"size": 4, "box": [2, 2],
     "clues": [{"line": "r1", "end": "left", "rank": 1}, ...],
     "marks": [{"kind": "digit", "cell": "r1c1", "digit": 0},
               {"kind": "missing", "unit": "c4", "digit": 3}, ...]}

`size` is n (4, 6 or 9), `box` the box's rows and columns. A rank clue
ranks the number its row (`left`, `right` end) or column (`top`, `bottom`)
makes, read away from that end, among all 4n. A mark is a deduction to
check, never a constraint: a digit in a grid cell, or the digit a row (r),
column (c) or box (b, numbered across, then down) misses.

The first line is `<k> rank clues: <status>`, one of `sudoku_kit`'s five.
Then each solution: per row and column its digits read from the left or
the top, its missing digit and the ranks from both ends, then the boxes'
missing digits. Then one line per mark, in `halver_report`'s format: `held`,
`NOT HELD` with a solution that breaks it, or `TIMEOUT` (no verdict in
`--time-limit` seconds, 60 unless given, never read as held). Exits 0 when
every mark held, 1 otherwise; a board with no solution, or no verdict on
its own status, has no mark checked and exits 1 with the reason. A board
file that cannot be read is refused by name, exit 2.
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import rules
from model import RankModel

BOXES = {4: (2, 2), 6: (2, 3), 9: (3, 3)}


def read_board(path):
    """The board file's size, box, clues and marks; a ValueError naming
    what is wrong."""
    doc = json.loads(path.read_text())
    n, box = doc["size"], tuple(doc["box"])
    if BOXES.get(n) != box:
        raise ValueError(f"size {n} with {box} boxes; known: {BOXES}")
    rows, cols, boxes = rules.houses(n, box)
    seen = set()
    for clue in doc["clues"]:
        place = (clue["line"], clue["end"])
        if place not in rules.places(n):
            raise ValueError(f"no place {clue['line']} {clue['end']} on a {n}x{n}")
        if place in seen:
            raise ValueError(f"two clues at {rules.place_name(place)}")
        seen.add(place)
        if not 1 <= clue["rank"] <= 4 * n:
            raise ValueError(f"rank {clue['rank']} outside 1..{4 * n}")
    for mark in doc["marks"]:
        name = mark_name(mark)
        if mark["kind"] == "digit":
            r, c = rules.parse_cell(mark["cell"])
            if not (0 <= r < n and 0 <= c < n and 0 <= mark["digit"] <= n):
                raise ValueError(f"mark {name} is off a {n}x{n} board")
        elif mark["unit"] not in {**rows, **cols, **boxes} or not (
            1 <= mark["digit"] <= n
        ):
            raise ValueError(f"mark {name} is off a {n}x{n} board")
    return n, box, doc["clues"], doc["marks"]


def mark_name(mark):
    """The mark in words, as the report prints it."""
    if mark["kind"] == "digit":
        return f"{mark['cell']} = {mark['digit']}"
    if mark["kind"] == "missing":
        return f"{mark['unit']} misses {mark['digit']}"
    raise ValueError(f"unknown mark kind {mark['kind']!r}: {mark}")


def describe(grid, box, clues):
    """A solution's lines: rows and columns, then the boxes. Raises when
    the rule reader finds a broken rule or clue in it, so an encoding bug
    is never printed as an answer."""
    reading = rules.read(grid, box)
    broken = reading.violations + reading.broken_clues(clues)
    if broken:
        raise RuntimeError(f"the model's solution breaks a rule: {broken}")
    lines = []
    for kind in "rc":
        for i in range(1, len(grid) + 1):
            line = f"{kind}{i}"
            near, far = rules.ENDS[kind]
            lines.append(
                f"  {line} {reading.numbers[line, near]}"
                f"  misses {reading.missing[line]}"
                f"  ranks {reading.ranks[line, near]} from the {near},"
                f" {reading.ranks[line, far]} from the {far}"
            )
    boxes = [f"b{b} {reading.missing[f'b{b}']}" for b in range(1, len(grid) + 1)]
    lines.append(f"  boxes miss {', '.join(boxes)}")
    return lines


def one_line(grid):
    return " ".join(f"r{r + 1} {''.join(map(str, row))}" for r, row in enumerate(grid))


def report(board, box, marks, time_limit):
    """Print the status, its solutions and each mark's verdict; the exit
    status."""
    result = board.check(time_limit=time_limit)
    print(f"{len(board.clues)} rank clues: {result.status}")
    if result.status not in ("unique", "not_unique"):
        print(f"no mark checked: the board's status is {result.status}")
        return 1
    for k, grid in enumerate((result.first, result.second), 1):
        if grid is not None:
            print(f"solution {k}")
            print("\n".join(describe(grid, box, board.clues)))

    all_held = True
    for mark in marks:
        verdict = board.mark_holds(mark, time_limit=time_limit)
        name = mark_name(mark)
        if verdict.status == "held":
            print(f"held      {name}")
            continue
        all_held = False
        if verdict.status == "not_held":
            describe(verdict.counterexample, box, board.clues)
            print(f"NOT HELD  {name}")
            print(f"  broken by: {one_line(verdict.counterexample)}")
        else:
            print(f"TIMEOUT   {name} (no verdict in {time_limit:g}s)")
    return 0 if all_held else 1


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("board", type=Path)
    parser.add_argument("--time-limit", type=float, default=60.0)
    args = parser.parse_args(argv)
    try:
        n, box, clues, marks = read_board(args.board)
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f"check.py: {args.board}: {error!s}", file=sys.stderr)
        return 2
    return report(RankModel(n, box, clues), box, marks, args.time_limit)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
