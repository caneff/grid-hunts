"""Slow toy finder for the hunt resume tests (#487).

toy_finder.py's rule; `propose` sleeps per seed so a test's SIGKILL lands
mid-hunt.

    uv run finders/hunt/toy_slow_finder.py --out DIR --seeds START:END
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dedupe import D4
from driver import run
from protocol import Verdict

SIDE = 4
SLEEP_SECONDS = 0.01


class SlowToyFinder:
    symmetry = D4

    def propose(self, rng):
        time.sleep(SLEEP_SECONDS)
        return tuple(rng.randint(0, 1) for _ in range(SIDE * SIDE))

    def verify(self, candidate):
        shaded = sum(candidate)
        ok = shaded % 2 == 0
        return Verdict(ok=ok, reason="" if ok else "odd shaded-cell count")

    def record(self, candidate):
        return {"grid": list(candidate)}

    def key(self, candidate):
        return candidate

    def candidate_from_record(self, record):
        return tuple(record["grid"])


if __name__ == "__main__":
    sys.exit(run(SlowToyFinder(), sys.argv[1:]))
