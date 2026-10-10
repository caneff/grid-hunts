"""The U-Bahn finder on the shared hunt protocol (#773): pure U-Bahn, every
outside number given.

One seed samples one network from the flow model, steered by the seed's own
random order and polarity over the edges, on one worker so a seed gives the
same network every run. The network's full set of outside numbers is then
proved to have no other network (solve, forbid, re-solve), on the hunt's
`--workers`. A seed whose network is not unique is `Empty("not unique")`, a
capped solve `Empty("timeout ...")`.

`verify` re-reads the network with `network.py`, which states the rules
without the model (dead ends, flood fill, the condition by counting), and
re-proves uniqueness with the spanning-tree encoding. That re-proof shares
the search's piece table, number sums and root; only its connectivity is a
second encoding.

Conditions are finder rules passed as flags. The one so far:
`--exactly N:PIECE:rK` (or `cK`), exactly N of a piece in a row or column;
PIECE is turn, straight, branch, cross, or blank for the cells with no arm.

    uv run finders/ubahn/ubahn_finder.py --out DIR --seeds 0:50 --workers 1 \\
        --rows 6 --cols 6 --exactly 2:cross:r2 --timeout 60
    uv run finders/ubahn/ubahn_finder.py verify DIR

The driver's flags (`--out`, `--seeds`, `--workers`, ...) are its own
(finders/hunt/driver.py).
"""

import argparse
import sys
from pathlib import Path
from typing import NamedTuple

from ortools.sat.python import cp_model

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "hunt"))
# isort: split
import model
import network
from dedupe import D4
from driver import run
from protocol import Empty, Verdict

DEFAULT_SIDE = 6
DEFAULT_TIMEOUT = 60.0


class Candidate(NamedTuple):
    """A found network with the board and the condition it answers."""

    rows: int
    cols: int
    network: frozenset
    exactly: network.Exactly | None


def board_symmetry(rows, cols):
    """The group the grid of kinds dedupes under: the square's eight rotations
    and reflections, or on any other board the four maps that keep its
    shape (identity, the two reflections, the half turn)."""
    if rows == cols:
        return D4
    return [
        tuple(
            (rows - 1 - r if flip_rows else r) * cols
            + (cols - 1 - c if flip_cols else c)
            for r in range(rows)
            for c in range(cols)
        )
        for flip_rows in (False, True)
        for flip_cols in (False, True)
    ]


class UbahnFinder:
    def __init__(
        self,
        rows=DEFAULT_SIDE,
        cols=DEFAULT_SIDE,
        exactly=None,
        timeout=DEFAULT_TIMEOUT,
    ):
        self.rows, self.cols, self.exactly, self.timeout = rows, cols, exactly, timeout
        self.symmetry = board_symmetry(rows, cols)
        self.config = {
            "rows": rows,
            "cols": cols,
            "exactly": exactly.text() if exactly else None,
            "timeout": timeout,
        }

    def propose(self, rng):
        built = model.build(self.rows, self.cols, "flow", exactly=self.exactly)
        # The seed picks which edges the search decides first and which way:
        # left to itself the solver returns the same dull network every time.
        order = list(built.edge.values())
        rng.shuffle(order)
        built.m.add_decision_strategy(
            [var if rng.random() < 0.5 else var.Not() for var in order],
            cp_model.CHOOSE_FIRST,
            cp_model.SELECT_MAX_VALUE,
        )
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = self.timeout
        solver.parameters.num_workers = 1
        solver.parameters.search_branching = cp_model.FIXED_SEARCH
        status = solver.Solve(built.m)
        if status == cp_model.UNKNOWN:
            return Empty("timeout sampling a network")
        if status == cp_model.INFEASIBLE:
            return Empty("infeasible: no network meets the condition")
        if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            raise RuntimeError(solver.StatusName(status))
        found = frozenset(e for e, var in built.edge.items() if solver.Value(var))

        status, _ = model.uniqueness(
            self.rows,
            self.cols,
            network.outside_numbers(found, self.rows, self.cols),
            "flow",
            time_limit=self.timeout,
            workers=self.workers,
        )
        if status == "timeout":
            return Empty("timeout proving uniqueness")
        if status == "not_unique":
            return Empty("not unique")
        if status != "unique":
            raise RuntimeError(f"the sampled network's own outside numbers: {status}")
        return Candidate(self.rows, self.cols, found, self.exactly)

    def verify(self, candidate):
        rows, cols, found, exactly = candidate
        why = network.why_not_network(found, rows, cols)
        if why:
            return Verdict(False, why)
        if exactly and not exactly.on_board(rows, cols):
            return Verdict(
                False, f"condition {exactly.text()} is off the {rows}x{cols} board"
            )
        if exactly and not exactly.holds(found, rows, cols):
            return Verdict(False, f"condition {exactly.text()} does not hold")
        status, other = model.uniqueness(
            rows,
            cols,
            network.outside_numbers(found, rows, cols),
            "tree",
            time_limit=self.timeout,
            # `hunt verify` sets no worker count, and a re-proof on one
            # worker gives the same verdict every run.
            workers=1,
        )
        if status == "timeout":
            return Verdict(False, "timeout re-proving uniqueness")
        if status != "unique":
            return Verdict(False, f"outside numbers: {status.replace('_', ' ')}")
        if other != found:
            return Verdict(False, "the tree model's one network is another")
        return Verdict(True)

    def record(self, candidate):
        rows, cols, found, exactly = candidate
        row_numbers, col_numbers = network.outside_numbers(found, rows, cols)
        return {
            "rows": rows,
            "cols": cols,
            "exactly": exactly.text() if exactly else None,
            # One string per row of horizontal, then of vertical, edges.
            "h": [
                "".join(
                    str(int(((r, c), (r, c + 1)) in found)) for c in range(cols - 1)
                )
                for r in range(rows)
            ],
            "v": [
                "".join(str(int(((r, c), (r + 1, c)) in found)) for c in range(cols))
                for r in range(rows - 1)
            ],
            "drawing": network.drawing(found, rows, cols),
            # Per row and per column: turns, straights, branches, crosses,
            # blank cells.
            "numbers": {"rows": row_numbers, "cols": col_numbers},
        }

    def key(self, candidate):
        return network.kind_grid(candidate.network, candidate.rows, candidate.cols)

    def candidate_from_record(self, record):
        """Raises ValueError, naming it, on an edge row that is not the
        board's width of 0s and 1s or a condition `Exactly.parse` refuses."""
        rows, cols = record["rows"], record["cols"]
        found = set()
        for name, step, count, width in (
            ("h", (0, 1), rows, cols - 1),
            ("v", (1, 0), rows - 1, cols),
        ):
            if len(record[name]) != count:
                raise ValueError(f"{name} has {len(record[name])} rows, not {count}")
            for r, bits in enumerate(record[name]):
                if len(bits) != width or set(bits) - {"0", "1"}:
                    raise ValueError(
                        f"edge row {bits!r} of {name} is not {width} 0s and 1s"
                    )
                found |= {
                    ((r, c), (r + step[0], c + step[1]))
                    for c, bit in enumerate(bits)
                    if bit == "1"
                }
        exactly = record["exactly"]
        return Candidate(
            rows,
            cols,
            frozenset(found),
            None if exactly is None else network.Exactly.parse(exactly),
        )


def main(argv):
    parser = argparse.ArgumentParser(prog="ubahn_finder", add_help=False)
    parser.add_argument("--rows", type=int, default=DEFAULT_SIDE)
    parser.add_argument("--cols", type=int, default=DEFAULT_SIDE)
    parser.add_argument("--exactly", metavar="N:PIECE:rK")
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT)
    own, rest = parser.parse_known_args(argv)
    if rest[:1] == ["verify"]:
        # A record carries its own board and condition; only the cap is ours.
        return run(UbahnFinder(timeout=own.timeout), rest)
    if own.rows < 2 or own.cols < 2:
        print("ubahn_finder: the smallest board with a network is 2x2", file=sys.stderr)
        return 2
    exactly = None
    if own.exactly is not None:
        try:
            exactly = network.Exactly.parse(own.exactly)
        except ValueError as e:
            print(f"ubahn_finder: --exactly: {e}", file=sys.stderr)
            return 2
        if not exactly.on_board(own.rows, own.cols):
            print(
                f"ubahn_finder: --exactly names {own.exactly.split(':')[2]}, "
                f"off a {own.rows}x{own.cols} board",
                file=sys.stderr,
            )
            return 2
    return run(UbahnFinder(own.rows, own.cols, exactly, own.timeout), rest)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
