"""The Dutch Chocolate Banabner hunt on the shared hunt protocol (spec #758).

One seed is one CP-SAT solve of `banabner_model.Model`, the solver's random
seed taken from the seed's rng. Every grid an earlier seed returned is
forbidden (the finder's state), so a later seed finds a new grid or proves
there is none: a capped solve comes back `Empty("timeout")`, a proof
`Empty("infeasible with <k> grids forbidden")`. `verify` re-reads the grid
with `renbanana_verify.check` at difference 4 and the nabner rule, a checker
written from the rules and not from this model.

    uv run finders/banabner/banabner_finder.py --out DIR --seeds 0:4 --timeout 600
    uv run finders/banabner/banabner_finder.py verify DIR

The driver's flags (`--out`, `--seeds`, `--workers`, ...) are its own
(`finders/hunt/driver.py`); `--workers` is the solver's worker count.
`--timeout` is the seconds one seed's solve may take, and a hunt needs it.
`--max-choc-side` is the chocolate side bound, 4 by default
(`banabner_model.MAX_CHOC_SIDE` says why it is a fact, not a cap).
`--no-speedups` drops #762's facts and lex-leader, for timing against them.
"""

import argparse
import sys
from pathlib import Path
from typing import NamedTuple

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "finders"))
sys.path.insert(0, str(ROOT / "finders" / "hunt"))
import banabner_model as bm
import renbanana_verify as rv
from dedupe import D4, canonical_key
from driver import run
from ortools.sat.python import cp_model as cp
from protocol import Empty, Verdict
from sudoku_kit import cpsat

N = 9


class Candidate(NamedTuple):
    """A found grid: digits and shading, each nine row strings."""

    grid: tuple
    shading: tuple


def to_maps(candidate):
    """(grid, is_choc) as `renbanana_verify.check` reads them."""
    grid = {(r, c): int(candidate.grid[r][c]) for r in range(N) for c in range(N)}
    is_choc = {
        (r, c): candidate.shading[r][c] == "C" for r in range(N) for c in range(N)
    }
    return grid, is_choc


def from_maps(grid, is_choc):
    return Candidate(
        tuple("".join(str(grid[r, c]) for c in range(N)) for r in range(N)),
        tuple(
            "".join("C" if is_choc[r, c] else "b" for c in range(N)) for r in range(N)
        ),
    )


def from_key(key):
    """The candidate a `BanabnerFinder.key` tuple reads as."""
    grid = {(r, c): key[r * N + c] % 10 for r in range(N) for c in range(N)}
    is_choc = {(r, c): key[r * N + c] >= 10 for r in range(N) for c in range(N)}
    return from_maps(grid, is_choc)


def leader(candidate):
    """The candidate's least image under the board's 8 symmetries: the one copy
    of it the model's lex-leader accepts."""
    return from_key(canonical_key(BanabnerFinder.key(candidate), D4))


def check(candidate):
    """`renbanana_verify.check` under the Banabner rules."""
    grid, is_choc = to_maps(candidate)
    return rv.check(grid, is_choc, difference=bm.DIFFERENCE, banana_rule=rv.NABNER)


class BanabnerFinder:
    # The rules are the same under every rotation and reflection of the board.
    symmetry = D4

    def __init__(self, timeout=None, max_side=bm.MAX_CHOC_SIDE, speedups=True):
        self.config = {
            "timeout": timeout,
            "max_choc_side": max_side,
            "speedups": speedups,
        }
        self.found = []

    def model(self):
        """The model with every grid found so far forbidden."""
        model = bm.Model(self.config["max_choc_side"], self.config["speedups"])
        cells = {("d", p): v for p, v in model.d.items()}
        cells |= {("c", p): v for p, v in model.choc.items()}
        for i, (rows, shading) in enumerate(self.found):
            grid, is_choc = to_maps(Candidate(rows, shading))
            pinned = {("d", p): v for p, v in grid.items()}
            pinned |= {("c", p): int(v) for p, v in is_choc.items()}
            cpsat.forbid(model.m, cells, pinned, tag=f"found{i}")
        return model

    def propose(self, rng):
        status, grid, is_choc = self.model().solve(
            self.config["timeout"], self.workers, rng.randrange(2**31)
        )
        if status == cp.INFEASIBLE:
            return Empty(f"infeasible with {len(self.found)} grids forbidden")
        if status == cp.UNKNOWN:
            return Empty("timeout")
        if grid is None:
            raise RuntimeError(f"banabner model: solver status {status.name}")
        candidate = from_maps(grid, is_choc)
        self.found.append([list(candidate.grid), list(candidate.shading)])
        return candidate

    def verify(self, candidate):
        bad = check(candidate)
        return Verdict(not bad, "; ".join(bad))

    def record(self, candidate):
        return {"grid": list(candidate.grid), "shading": list(candidate.shading)}

    @staticmethod
    def key(candidate):
        return tuple(
            bm.cell_value(int(candidate.grid[r][c]), candidate.shading[r][c] == "C")
            for r in range(N)
            for c in range(N)
        )

    def candidate_from_record(self, record):
        return Candidate(tuple(record["grid"]), tuple(record["shading"]))

    def save_state(self):
        return {"found": self.found}

    def load_state(self, state):
        self.found = [list(map(list, f)) for f in state["found"]]


def main(argv):
    if argv[:1] in (["-h"], ["--help"]):
        print(__doc__)
        return 0
    parser = argparse.ArgumentParser(prog="banabner_finder", add_help=False)
    parser.add_argument("--timeout", type=float)
    parser.add_argument("--max-choc-side", type=int, default=bm.MAX_CHOC_SIDE)
    parser.add_argument("--no-speedups", action="store_true")
    own, rest = parser.parse_known_args(argv)
    if rest[:1] == ["verify"]:
        return run(BanabnerFinder(), rest)
    if own.timeout is None:
        print("banabner_finder: a hunt needs --timeout", file=sys.stderr)
        return 2
    finder = BanabnerFinder(own.timeout, own.max_choc_side, not own.no_speedups)
    return run(finder, rest)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
