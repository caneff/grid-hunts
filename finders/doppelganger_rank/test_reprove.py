"""The second uniqueness model (#70), judged against the 4x4 answer key
(`brute.py`), which takes no part in it:

- On each 4x4 board of the check's tests (`fixtures/*_4x4.json`) the
  second model's status is the key's, and a `unique` board's one grid is
  the key's grid.
- So it is on 60 boards of random clues, each clue a key grid's rank at a
  random place, 1 to 4 clues to a board: unique, not unique and (from two
  grids' clues mixed) infeasible boards all occur.
- Every grid it returns is a key grid that keeps the clues, and a
  `not_unique` board's two grids differ.
- The 4x4 key has no tie, so ties are checked on `fixtures/tie_6x6.json`
  (two places both rank 2, which only a tie gives): the re-proof finds
  grids, and the rule reader finds every rule and clue kept in each.
- A re-proof given no time is a timeout, never unique.
- `reprove.py` imports only the standard library, `ortools` and
  `sudoku_kit`, read from its source: never `model`, `rules` or any other
  module of this repo, so the independence its docstring claims holds.

    uv run finders/doppelganger_rank/test_reprove.py
"""

import ast
import json
import random
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import brute
import rules
from reprove import reprove

FIXTURES = HERE / "fixtures"


def agrees(clues):
    """The re-proof's status, asserted equal to the key's."""
    want, keep = brute.classify(clues)
    got = reprove(4, brute.BOX, clues, time_limit=30.0)
    assert got.status == want, (clues, got, want)
    for grid in (got.first, got.second):
        if grid is not None:
            assert grid in keep, (clues, grid)
    if want == "unique":
        assert [got.first] == keep, (clues, got.first, keep)
    if want == "not_unique":
        assert got.first != got.second, (clues, got)
    return want


for name in ("unique_4x4", "not_unique_4x4", "infeasible_4x4"):
    board = json.loads((FIXTURES / f"{name}.json").read_text())
    assert agrees(board["clues"]) == name.removesuffix("_4x4"), name

rng = random.Random(70)
key = brute.grids()
seen = Counter()
for _ in range(60):
    picks = rng.sample(rules.places(4), rng.randint(1, 4))
    sources = [rng.choice(key)[1] for _ in range(2)]
    clues = [
        {"line": p[0], "end": p[1], "rank": rng.choice(sources).ranks[p]} for p in picks
    ]
    seen[agrees(clues)] += 1
assert set(seen) == {"unique", "not_unique", "infeasible"}, seen

tie = json.loads((FIXTURES / "tie_6x6.json").read_text())
got = reprove(6, (2, 3), tie["clues"], time_limit=30.0)
assert got.status in ("unique", "not_unique"), got
for grid in (got.first, got.second):
    if grid is not None:
        reading = rules.read(grid, (2, 3))
        assert reading.violations + reading.broken_clues(tie["clues"]) == [], grid

board = json.loads((FIXTURES / "unique_4x4.json").read_text())
assert reprove(4, brute.BOX, board["clues"], time_limit=1e-9).status == "timeout"

roots = set()
for node in ast.walk(ast.parse((HERE / "reprove.py").read_text())):
    if isinstance(node, ast.Import):
        roots.update(alias.name.split(".")[0] for alias in node.names)
    elif isinstance(node, ast.ImportFrom):
        # A relative import (`from . import x`) is this repo's code.
        roots.add(node.module.split(".")[0] if node.level == 0 else ".")
allowed = set(sys.stdlib_module_names) | {"ortools", "sudoku_kit"}
assert roots <= allowed, f"reprove.py imports {sorted(roots - allowed)}"

print(f"test_reprove: ok {dict(seen)}")
