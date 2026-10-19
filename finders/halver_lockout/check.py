"""Check a lockout + halver board: the uniqueness status of its lines, and
whether each mark holds in every solution.

    uv run finders/halver_lockout/check.py BOARD [--marks FILE] [--time-limit S]

BOARD is a decoded 9x9 SudokuMaker document; its lockout lines are its
constraint type 407 lines, diamonds first and last. A file with none is
refused, exit 2. The marks, in `halver_between`'s `marks.json` format, are
deductions to check, never constraints on the board; with no `--marks`
there are none. The first line is `L1-L<k>: <status>`, then one line per
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


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("board", type=Path)
    parser.add_argument("--marks", type=Path)
    parser.add_argument("--time-limit", type=float, default=60.0)
    args = parser.parse_args(argv)
    try:
        cells = len(json.loads(args.board.read_text())["puzzle"]["cells"])
        if cells != 81:
            raise ValueError(f"{args.board}: {cells} cells, and only 9x9 is checked")
        lines = rules.load_lines(args.board)
    except ValueError as error:
        print(f"check.py: {error}", file=sys.stderr)
        return 2
    marks = json.loads(args.marks.read_text()) if args.marks else []
    return report(rules.RuleModel(lines), marks, args.time_limit)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
