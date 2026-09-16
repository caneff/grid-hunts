"""strip() removes at least one item from an over-clued puzzle and keeps
uniqueness (#486).

    uv run finders/hunt/test_minimizer.py
"""

import sys
from pathlib import Path

from ortools.sat.python import cp_model

sys.path.insert(0, str(Path(__file__).resolve().parent))
from minimizer import strip
from uniqueness import check_uniqueness

ok = True


def check(name, cond):
    global ok
    status = "ok" if cond else "FAIL"
    if not cond:
        ok = False
    print(f"{status}: {name}")


# A 2x2 Latin square (digits 1/2, each row and column distinct) with all
# four cells given -- more clues than a unique Latin square needs, since
# fixing any one cell forces the rest.
SOLUTION = {(0, 0): 1, (0, 1): 2, (1, 0): 2, (1, 1): 1}
CELLS = list(SOLUTION)


def build_model(givens):
    m = cp_model.CpModel()
    x = {c: m.NewIntVar(1, 2, f"x{c}") for c in CELLS}
    m.Add(x[(0, 0)] != x[(0, 1)])
    m.Add(x[(1, 0)] != x[(1, 1)])
    m.Add(x[(0, 0)] != x[(1, 0)])
    m.Add(x[(0, 1)] != x[(1, 1)])
    for c, v in givens.items():
        m.Add(x[c] == v)
    return m, x


def is_unique(givens):
    m, x = build_model(givens)
    return check_uniqueness(m, [x[c] for c in CELLS]).unique


check("the fully given puzzle is unique (sanity)", is_unique(SOLUTION))

stripped = strip(SOLUTION, keep=set(), test=is_unique)
check("at least one given was removed", len(stripped) < len(SOLUTION))
check("the stripped puzzle is still unique", is_unique(stripped))
check(
    "every remaining given is a real given, not an invented value",
    set(stripped.items()) <= set(SOLUTION.items()),
)
check(
    "stripping this 2x2 Latin square reaches its true minimum: one clue",
    len(stripped) == 1,
)

# A `keep` cell is never removed even when the puzzle would stay unique
# without it.
kept = strip(SOLUTION, keep={(0, 0)}, test=is_unique)
check("a kept item survives stripping", (0, 0) in kept)

sys.exit(0 if ok else 1)
