"""`prove`, the real join of the two stages, on a live CP-SAT run.

With no circles every legal grid is a solution, so the enumeration must reach
NOT UNIQUE with two *different* verified solutions. A handled shading that is
not really cut would come back from stage 1 and hand over the same grid twice.
About 17 s on one worker, so it stays out of `just check`.

    uv run finders/renbanana/tools/test_prove_two_stage_slow.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import prove_two_stage as pts
import renbanana_verify as rv

verdict, sols, survivors = pts.prove([], 150.0, 1, log=lambda _: None)
assert verdict == "NOT UNIQUE", verdict
assert len(sols) == 2 and sols[0] != sols[1], "the two solutions must differ"
for grid, is_choc in sols:
    assert not rv.check(grid, is_choc)
print(f"OK  NOT UNIQUE after {survivors} survivors")
