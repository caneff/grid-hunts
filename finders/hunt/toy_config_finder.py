"""Toy finder with a config of its own, for test_finder_config.py (#491).

Random 4x4 shadings, as in toy_finder.py, but `--parity even|odd` -- a flag
the driver does not know -- picks which shaded-cell count `verify` accepts,
and some seeds come back `Empty` with a reason. The script parses its own
flag and hands the rest of argv to `run`; the finder's `config` is what
run.json records and a resume must match.

    uv run finders/hunt/toy_config_finder.py --out DIR --seeds START:END --parity odd
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dedupe import D4
from driver import run
from protocol import Empty, Verdict

SIDE = 4


class ToyConfigFinder:
    symmetry = D4

    def __init__(self, parity):
        self.parity = parity
        self.config = {"parity": parity}

    def propose(self, rng):
        if rng.random() < 0.3:
            return Empty("toy: nothing this seed")
        return tuple(rng.randint(0, 1) for _ in range(SIDE * SIDE))

    def verify(self, candidate):
        ok = sum(candidate) % 2 == (self.parity == "odd")
        return Verdict(ok=ok, reason="" if ok else f"not {self.parity}")

    def record(self, candidate):
        return {"grid": list(candidate)}

    def key(self, candidate):
        return candidate


if __name__ == "__main__":
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--parity", choices=("even", "odd"), default="even")
    own, rest = parser.parse_known_args(sys.argv[1:])
    sys.exit(run(ToyConfigFinder(own.parity), rest))
