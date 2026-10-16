"""A circle in `probe_circle_pattern` costs one constraint, not a model.

Group sizes are computed once for all 81 cells and shared, so circling a cell
only ties its digit to a size already in the model. Adding circles must not
grow the model's variables at all.

    uv run finders/renbanana/tools/test_probe_circle_cost.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import probe_circle_pattern as pcp

TWELVE = pcp.parse_cells("r1c1,r1c5,r2c8,r3c3,r4c6,r5c1,r5c9,r6c4,r7c7,r8c2,r9c5,r9c9")


def model_size(model):
    return len(model.proto.variables), len(model.proto.constraints)


def test_twelve_circles_add_no_variables_and_one_constraint_each():
    bare_vars, bare_cons = model_size(pcp.build([])[0])
    vars12, cons12 = model_size(pcp.build(TWELVE)[0])
    assert vars12 == bare_vars, f"circles added {vars12 - bare_vars} variables"
    assert cons12 - bare_cons <= len(TWELVE), (
        f"circles added {cons12 - bare_cons} constraints"
    )


if __name__ == "__main__":
    test_twelve_circles_add_no_variables_and_one_constraint_each()
    print("OK")
