"""Reading `check.py`'s printed report and grids back, for the tests."""

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


def grid_of(text):
    """The grid `check.one_line` printed, `r1 0231 r2 3420 ...`."""
    return tuple(tuple(map(int, word)) for word in text.split()[1::2])
