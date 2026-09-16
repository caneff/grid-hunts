"""The text board printer, output matched by hand (#485).

uv run finders/hunt/test_printer.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from printer import render_board

ok = True


def check(name, cond):
    global ok
    status = "ok" if cond else "FAIL"
    if not cond:
        ok = False
    print(f"{status}: {name}")


check(
    "a small digit board renders one space-separated row per line",
    render_board([[1, 2], [3, 4]]) == "1 2\n3 4",
)

check(
    "None cells print as the default empty marker",
    render_board([[1, None], [None, 2]]) == "1 .\n. 2",
)

check(
    "a custom empty marker is used instead of the default",
    render_board([[0, None], [None, 0]], empty="_") == "0 _\n_ 0",
)

check(
    "a single-row board has no trailing newline",
    render_board([[1, 2, 3]]) == "1 2 3",
)

check("an empty board renders as an empty string", render_board([]) == "")

sys.exit(0 if ok else 1)
