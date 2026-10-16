"""Report on Chris's board: the uniqueness status of its lines, and whether
each of his marks holds in every solution.

    uv run finders/halver_between/report.py [--marks FILE] [--time-limit S]

The lines are `board.json`'s, decoded from BOARD_LINK.txt. The marks
are `marks.json`'s unless `--marks` names another file: deductions to check,
never constraints on the board. The first line is `L1-L<k>: <status>`, then
one line per mark, `held` or `NOT HELD` (with a solution that breaks it) or
`TIMEOUT` (no verdict in `--time-limit` seconds, 60 unless given, never
read as held). Exits 0 when every mark held, 1
otherwise. A board with no solution, or no verdict on its own status, has no
mark checked and exits 1 with the reason.
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import rules

HERE = Path(__file__).resolve().parent


def describe(solution):
    rows = " ".join(
        f"r{r + 1} {''.join(map(str, row))}" for r, row in enumerate(solution.digits)
    )
    halvers = " ".join(rules.cell_name(c) for c in sorted(solution.halvers))
    return f"{rows}; halvers {halvers}"


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--marks", type=Path, default=HERE / "marks.json")
    parser.add_argument("--time-limit", type=float, default=60.0)
    args = parser.parse_args(argv)
    lines = rules.load_lines(HERE / "board.json")
    marks = json.loads(args.marks.read_text())

    board = rules.RuleModel(lines)
    status = board.check(time_limit=args.time_limit).status
    print(f"L1-L{len(lines)}: {status}")
    if status not in ("unique", "not_unique"):
        print(f"no mark checked: the board's status is {status}")
        return 1

    all_held = True
    for mark in marks:
        result = board.mark_holds(mark, time_limit=args.time_limit)
        name = rules.mark_name(mark)
        if result.status == "held":
            print(f"held      {name}")
            continue
        all_held = False
        if result.status == "not_held":
            print(f"NOT HELD  {name}")
            print(f"  broken by: {describe(result.counterexample)}")
        else:
            print(f"TIMEOUT   {name} (no verdict in {args.time_limit:g}s)")
    return 0 if all_held else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
