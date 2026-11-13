"""Toy finder with `render`, for the `hunt render DIR` test (#490, #119).

Same rule as toy_finder.py, plus a `render` that draws the shading.
toy_finder.py stays render-less to prove the driver writes no renders/ for it.

    uv run finders/hunt/toy_render_finder.py --out DIR --seeds START:END
    uv run finders/hunt/toy_render_finder.py render DIR
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dedupe import D4
from driver import run
from protocol import Verdict
from render import GridCanvas

SIDE = 4


class ToyRenderFinder:
    symmetry = D4

    def propose(self, rng):
        return tuple(rng.randint(0, 1) for _ in range(SIDE * SIDE))

    def verify(self, candidate):
        shaded = sum(candidate)
        ok = shaded % 2 == 0
        return Verdict(ok=ok, reason="" if ok else "odd shaded-cell count")

    def record(self, candidate):
        return {"grid": list(candidate)}

    def key(self, candidate):
        return candidate

    def render(self, candidate):
        # TOY_RENDER_FAIL simulates a render failure for test_render_hook.py's
        # test that a failed `render DIR` leaves the previous set.
        if os.environ.get("TOY_RENDER_FAIL"):
            raise RuntimeError("simulated transient render failure")
        canvas = GridCanvas(SIDE, SIDE, cell=20, margin=4)
        for i, cell in enumerate(candidate):
            if cell:
                canvas.shade_cell(i // SIDE, i % SIDE, (0, 0, 0))
        canvas.box_lines(box_rows=SIDE, box_cols=SIDE)
        return canvas.image


if __name__ == "__main__":
    sys.exit(run(ToyRenderFinder(), sys.argv[1:]))
