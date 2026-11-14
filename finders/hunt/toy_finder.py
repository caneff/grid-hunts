"""Toy finder: random 4x4 shadings, for test_toy_hunt.py (#484/#487).

Odd shaded-cell counts are rejected, so a fresh hunt has real rejects to keep
out of examples.jsonl.

    uv run finders/hunt/toy_finder.py --out DIR --seeds START:END
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dedupe import D4
from driver import run
from protocol import Verdict

SIDE = 4


class ToyFinder:
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

    def candidate_from_record(self, record):
        return tuple(record["grid"])


if __name__ == "__main__":
    sys.exit(run(ToyFinder(), sys.argv[1:]))
