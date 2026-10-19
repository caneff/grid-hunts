"""Check a lockout + halver board: the uniqueness status of its lines, and
whether each mark holds in every solution.

    uv run finders/halver_lockout/check.py BOARD [--marks FILE] [--time-limit S]

BOARD is a decoded 9x9 SudokuMaker document; its lockout lines are its
constraint type 407 lines, diamonds first and last. A lockout board has
nothing else (spec #52): beside the given-digits and regions elements (types
0 and 1), any other constraint, or a cell marked `"given": true`, is refused
rather than left unchecked. Digits entered in cells, never given, are not
read. The marks, in `halver_between`'s `marks.json` format, are deductions
to check, never constraints on the board; with no `--marks` there are none.
A board or marks file that cannot be read (missing, not JSON, not 9x9, no
type-407 line, a line with no body cell, an unknown mark kind) is refused,
exit 2, so a malformed input never exits like a verdict. The first line is `L1-L<k>: <status>`, then one line per
mark, `held` or `NOT HELD` (with a solution that breaks it) or `TIMEOUT` (no
verdict in `--time-limit` seconds, 60 unless given, never read as held).
Exits 0 when every mark held, 1 otherwise. A board with no solution, or no
verdict on its own status, has no mark checked and exits 1 with the reason.
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import rules

# isort: split
from halver_report import report
from halver_rules import cell_name, mark_name

ALLOWED = {0, 1, rules.LOCKOUT_LINE}  # given digits, regions, lockout lines


def read_board(path):
    """The board's lockout lines; a ValueError naming what is wrong."""
    doc = json.loads(path.read_text())
    cells = len(doc["puzzle"]["cells"])
    if cells != 81:
        raise ValueError(f"{cells} cells, and only 9x9 is checked")
    lines = rules.lines_from_doc(doc)
    other = sorted(
        {c.get("type") for c in doc["puzzle"]["constraints"]} - ALLOWED, key=str
    )
    if other:
        raise ValueError(f"constraint type {other[0]} on a lockout-only board")
    given = [i for i, cell in enumerate(doc["puzzle"]["cells"]) if cell.get("given")]
    if given:
        raise ValueError(f"given digit in {cell_name(divmod(given[0], 9))}")
    return lines


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("board", type=Path)
    parser.add_argument("--marks", type=Path)
    parser.add_argument("--time-limit", type=float, default=60.0)
    args = parser.parse_args(argv)
    try:
        try:
            lines = read_board(args.board)
            board = rules.RuleModel(lines)
        except (OSError, ValueError, KeyError) as error:
            raise ValueError(f"{args.board}: {error}") from error
        try:
            marks = json.loads(args.marks.read_text()) if args.marks else []
            for mark in marks:
                mark_name(mark)
        except (OSError, ValueError, KeyError) as error:
            raise ValueError(f"{args.marks}: {error}") from error
    except ValueError as error:
        print(f"check.py: {error}", file=sys.stderr)
        return 2
    return report(board, marks, args.time_limit)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
