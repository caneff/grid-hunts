"""Reading `check.py`'s printed report back, for the tests."""

import re

ROW = re.compile(r"^  (r\d) (\d+) ")


def solutions(out):
    """The grids printed after each `solution <k>` line, in order."""
    found = []
    for line in out:
        if re.fullmatch(r"solution \d", line):
            found.append([])
        elif found and (match := ROW.match(line)):
            found[-1].append(tuple(map(int, match.group(2))))
    return [tuple(grid) for grid in found]
