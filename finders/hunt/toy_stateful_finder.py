"""Slow, stateful toy finder for the hunt resume tests (#487).

Subclasses toy_slow_finder.SlowToyFinder, adding a counter of seeds seen so
far that `save_state`/`load_state` round-trip through state.json. `record`
stamps each example with the counter's value at the time it was found, so a
test can tell a resumed run picked the counter back up instead of
restarting it at zero.

    uv run finders/hunt/toy_stateful_finder.py --out DIR --seeds START:END
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from driver import run
from toy_slow_finder import SlowToyFinder


class StatefulToyFinder(SlowToyFinder):
    def __init__(self):
        self.seeds_seen = 0

    def propose(self, rng):
        candidate = super().propose(rng)
        self.seeds_seen += 1
        return candidate

    def record(self, candidate):
        record = super().record(candidate)
        record["seeds_seen_at_find"] = self.seeds_seen
        return record

    def save_state(self):
        return {"seeds_seen": self.seeds_seen}

    def load_state(self, state):
        self.seeds_seen = state["seeds_seen"]


if __name__ == "__main__":
    sys.exit(run(StatefulToyFinder(), sys.argv[1:]))
