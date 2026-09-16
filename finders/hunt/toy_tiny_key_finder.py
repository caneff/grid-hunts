"""A two-key toy finder for the hunt resume tests (#487).

Subclasses toy_slow_finder.SlowToyFinder but proposes a 1-cell grid: only
two possible candidates (grid [0] and grid [1]) exist at all, so any
seed range past a handful guarantees repeat candidates on both sides of a
kill. That makes it a real witness for "the dedupe set is rebuilt from the
durable log" -- the 4x4 toy finders' key space is big enough that a broken
rebuild would rarely produce a visible duplicate.

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
