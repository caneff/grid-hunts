"""Toy finder with the summary, links and finish hooks, for
test_summary_links.py (#121).

Same rule as toy_finder.py (random 4x4 shadings, even-count verifier), plus
the three hooks a finder may supply: `link_document` (the SudokuMaker
document of a verified hit), `describe_hit` (its summary wording) and
`finish` (stamps `finished.txt` when a hunt completes). Two env knobs drive
the tests, counting `propose` calls from 1 in a fresh process:

- `TOY_EMPTY=timeout:2,infeasible:4` makes those calls return
  `Empty("<reason>: ...")`;
- `TOY_STALL_CALL=N` makes call N sleep 60 s, so a test can kill the hunt there.

    uv run finders/hunt/toy_summary_finder.py --out DIR --seeds START:END
    uv run finders/hunt/toy_summary_finder.py summary DIR
    uv run finders/hunt/toy_summary_finder.py links DIR
"""

import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dedupe import D4
from driver import run
from protocol import Empty, Verdict

SIDE = 4
FINISHED = "finished.txt"


def link_doc(grid):
    """The SudokuMaker document of a shading: digit 1 unshaded, 2 shaded."""
    return {
        "formatVersion": "1.6.0",
        "puzzle": {
            "name": "",
            "author": "",
            "type": "custom",
            "width": SIDE,
            "height": SIDE,
            "minDigit": 1,
            "maxDigit": 2,
            "cells": [{"value": 1 + g} for g in grid],
            "constraints": [],
        },
    }


class ToySummaryFinder:
    symmetry = D4

    def __init__(self):
        self.calls = 0
        self.empty = {}
        for part in filter(None, os.environ.get("TOY_EMPTY", "").split(",")):
            reason, call = part.split(":")
            self.empty[int(call)] = reason

    def propose(self, rng):
        self.calls += 1
        if os.environ.get("TOY_STALL_CALL") == str(self.calls):
            time.sleep(60)
        if self.calls in self.empty:
            return Empty(f"{self.empty[self.calls]}: scripted")
        return tuple(rng.randint(0, 1) for _ in range(SIDE * SIDE))

    def verify(self, candidate):
        ok = sum(candidate) % 2 == 0
        return Verdict(ok=ok, reason="" if ok else "odd shaded-cell count")

    def record(self, candidate):
        return {"grid": list(candidate)}

    def key(self, candidate):
        return candidate

    def candidate_from_record(self, record):
        return tuple(record["grid"])

    def link_document(self, candidate):
        return link_doc(candidate)

    def describe_hit(self, record):
        return f"hit, {sum(record['grid'])} shaded: {record['grid']}"

    def finish(self, out):
        (Path(out) / FINISHED).write_text("done\n")


if __name__ == "__main__":
    sys.exit(run(ToySummaryFinder(), sys.argv[1:]))
