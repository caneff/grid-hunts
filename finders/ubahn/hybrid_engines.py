"""The hybrid finder's engines and its finder: the `ENGINES` that sample and
classify grids, `Conditions`' reader and writer of a hunt (`HybridFinder`, on
the hunt protocol) and the symmetry its dedupe uses. Nothing here reads a
command line or writes a search's files: `hybrid_searches.py` holds the
searches, `hybrid_finder.py` the command line, and a tool or test that wants
the engines imports this module and never the command line (spec #117, #133).
"""

import sys
from pathlib import Path
from typing import NamedTuple

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "hunt"))
# isort: split
import hybrid
import hybrid_model
import hybrid_sat
from dedupe import IDENTITY
from protocol import Empty, Verdict
from ubahn_finder import DEFAULT_TIMEOUT, UbahnFinder
from ubahn_finder import Candidate as PlainCandidate

# Each engine offers `grid(conditions, rng, *, time_limit)`, a
# `hybrid.Sampled`, and `classify(conditions, *, time_limit, workers)`, a
# `hybrid.Classified`.
ENGINES = {
    "cpsat": hybrid_model,
    "pysat-lazy": hybrid_sat.Engine(hybrid_sat.LAZY),
    "pysat-propagator": hybrid_sat.Engine(hybrid_sat.PROPAGATOR),
}
# Chris ruled PySAT with lazy cuts the default on 2026-10-11, on the timing
# in docs/research/2026-10-10-u-bahn-optimization-queue.md (#786).
DEFAULT_ENGINE = "pysat-lazy"

# The classification's words as Chris reads them, in the order the
# `fewest-markings` report counts them.
SAID = {
    "unique": "exactly one grid",
    "not_unique": "more than one grid",
    "infeasible": "no grid",
    "timeout": "time limit reached",
}


# Why a seed gave no grid, as `propose` says it and `climb` reads it back.
EMPTY_TIMEOUT = "timeout sampling a grid"
EMPTY_INFEASIBLE = "infeasible: no grid meets the conditions"


class Candidate(NamedTuple):
    """A found grid with the conditions it answers."""

    conditions: hybrid.Conditions
    network: frozenset


def mirror(cells):
    """The cells reflected in the main diagonal, sorted. A window's image is
    the window named by its top-left cell's image."""
    return tuple(sorted((c, r) for r, c in cells))


def condition_symmetry(conditions):
    """The group a grid's key (`HybridFinder.key`) dedupes under: the
    identity and the reflection in the main diagonal when that reflection
    keeps the conditions, the identity alone when it moves one. It keeps
    them on a square board whose circled cells are circled in the image too
    and whose marked windows are marked there too (a window's image is the
    window named by its top-left cell's image), with no piece-count
    condition, which names a row or a column. The reflection sends a cell's
    east arm to its image's south arm and back."""
    rows, cols, circles = conditions.rows, conditions.cols, conditions.circles
    marked = conditions.battenberg
    if (
        rows != cols
        or conditions.exactly
        or set(mirror(circles)) != set(circles)
        or set(mirror(marked)) != set(marked)
    ):
        return IDENTITY
    cells = rows * cols
    image = [c * cols + r for r in range(rows) for c in range(cols)]
    return [
        tuple(range(2 * cells)),
        tuple([cells + i for i in image] + image),
    ]


class HybridFinder:
    def __init__(
        self,
        conditions,
        engine=DEFAULT_ENGINE,
        timeout=DEFAULT_TIMEOUT,
        engines=ENGINES,
    ):
        """`engine` names one of `engines`, a mapping of the engines a hunt
        may use: a test passes its own to hunt with a fake."""
        self.conditions, self.engine, self.timeout = conditions, engine, timeout
        self.engines = engines
        self.symmetry = condition_symmetry(conditions)
        self.config = {
            "rows": conditions.rows,
            "cols": conditions.cols,
            "circles": sorted(map(hybrid.cell_name, conditions.circles)),
            "exactly": conditions.exactly.text() if conditions.exactly else None,
            "blank_strip": conditions.blank_strip,
            "number_circles": conditions.number_circles,
            "engine": engine,
            "timeout": timeout,
        }
        # Only when asked for: the driver refuses to resume a hunt whose
        # config differs, and a hunt from before the condition has no such key.
        if conditions.min_bananas:
            self.config["min_bananas"] = conditions.min_bananas
        if conditions.battenberg:
            self.config["battenberg"] = sorted(
                map(hybrid.cell_name, conditions.battenberg)
            )
        if conditions.battenberg_only:
            self.config["battenberg_only"] = True

    def propose(self, rng):
        status, found = self.engines[self.engine].grid(
            self.conditions, rng, time_limit=self.timeout
        )
        if status == "timeout":
            return Empty(EMPTY_TIMEOUT)
        if status == "infeasible":
            return Empty(EMPTY_INFEASIBLE)
        if found is None:
            raise RuntimeError(f"{self.engine} answered {status!r} with no grid")
        return Candidate(self.conditions, found)

    def verify(self, candidate):
        asked, found = candidate
        rows, cols, exactly = asked.rows, asked.cols, asked.exactly
        why = hybrid.why_not_hybrid(
            found,
            rows,
            cols,
            asked.circles,
            asked.blank_strip,
            min_bananas=asked.min_bananas,
            number_circles=asked.number_circles,
            battenberg=asked.battenberg,
            battenberg_only=asked.battenberg_only,
        )
        if why:
            return Verdict(False, why)
        if exactly and not exactly.on_board(rows, cols):
            return Verdict(
                False, f"condition {exactly.text()} is off the {rows}x{cols} board"
            )
        if exactly and not exactly.holds(found, rows, cols):
            return Verdict(False, f"condition {exactly.text()} does not hold")
        return Verdict(True)

    def record(self, candidate):
        asked, found = candidate
        rows, cols, circles = asked.rows, asked.cols, asked.circles
        board = hybrid.values(found, rows, cols, asked.blank_strip)
        return {
            # The plain finder's record of the network: the board, the
            # piece-count condition, the edge rows and the outside numbers.
            **UbahnFinder().record(PlainCandidate(rows, cols, found, asked.exactly)),
            "circles": sorted(map(hybrid.cell_name, circles)),
            "blank_strip": asked.blank_strip,
            "min_bananas": asked.min_bananas,
            "number_circles": asked.number_circles,
            # The reader's own count, whatever the condition asked for.
            "number_cell_circles": [
                hybrid.cell_name(cell) for cell in hybrid.number_cell_circles(board)
            ],
            "battenberg": sorted(map(hybrid.cell_name, asked.battenberg)),
            "battenberg_only": asked.battenberg_only,
            # Every checkerboard window of the grid, marked or not.
            "checkerboard_windows": [
                hybrid.cell_name(window)
                for window in hybrid.checkerboard_windows(board)
            ],
            "engine": self.engine,
            "drawing": hybrid.drawing(found, rows, cols, circles, asked.blank_strip),
        }

    def key(self, candidate):
        """The network itself: every cell's east arm, row by row, then every
        cell's south arm. Two networks can have the same kind in every cell
        and both be valid grids, so the kinds alone would drop one of them
        as a repeat."""
        asked, found = candidate
        rows, cols = asked.rows, asked.cols
        cells = [(r, c) for r in range(rows) for c in range(cols)]
        return tuple(
            int(((r, c), (r + dr, c + dc)) in found)
            for dr, dc in ((0, 1), (1, 0))
            for r, c in cells
        )

    def candidate_from_record(self, record):
        """Raises ValueError, naming it, on a circle `hybrid.parse_cell`
        refuses, anything the plain finder's reader refuses in the edge
        rows and the piece-count condition, a `min_bananas` that is no whole
        number of 0 or more, a `battenberg` that is no list of window names,
        a `battenberg_only` that is not true or false, or a field the record
        lacks. A record with no
        `min_bananas` is of a hunt from before that condition (#792) and asks
        for none; `record` has written the field in every record since. One
        with no `battenberg` or `battenberg_only` is from before Battenberg
        markings (spec #20): no markings, the negative constraint off."""
        try:
            rows, cols, found, exactly = UbahnFinder().candidate_from_record(record)
            circles = frozenset(map(hybrid.parse_cell, record["circles"]))
            min_bananas = record.get("min_bananas", 0)
            if type(min_bananas) is not int or min_bananas < 0:
                raise ValueError(
                    f"min_bananas is {min_bananas!r}: it is a whole number, 0 or more"
                )
            battenberg = record.get("battenberg", [])
            if type(battenberg) is not list or not all(
                type(name) is str for name in battenberg
            ):
                raise ValueError(
                    f"battenberg is {battenberg!r}: it is a list of window names"
                )
            battenberg_only = record.get("battenberg_only", False)
            if type(battenberg_only) is not bool:
                raise ValueError(
                    f"battenberg_only is {battenberg_only!r}: it is true or false"
                )
            conditions = hybrid.Conditions(
                rows,
                cols,
                circles,
                exactly,
                record["blank_strip"],
                min_bananas,
                # A record older than the condition (#794) asked for none.
                record.get("number_circles", 0),
                frozenset(map(hybrid.parse_cell, battenberg)),
                battenberg_only,
            )
        except KeyError as e:
            raise ValueError(
                f"the record has no {e.args[0]!r}: no hybrid hunt wrote it"
            ) from e
        return Candidate(conditions, found)
