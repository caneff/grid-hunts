"""A two-key toy finder for the hunt resume tests (#487).

Proposes a 1-cell grid, so only two candidates exist and repeats across a kill
are guaranteed; a broken dedupe rebuild shows up as a duplicate.

    uv run finders/hunt/toy_tiny_key_finder.py --out DIR --seeds START:END
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from driver import run
from protocol import Verdict
from toy_slow_finder import SLEEP_SECONDS, SlowToyFinder


class TinyKeyFinder(SlowToyFinder):
    def propose(self, rng):
        time.sleep(SLEEP_SECONDS)
        return (rng.randint(0, 1),)

    def verify(self, candidate):
        return Verdict(ok=True)


if __name__ == "__main__":
    sys.exit(run(TinyKeyFinder(), sys.argv[1:]))
