"""Exhaustive enumeration of U-Bahn edge assignments, for the tests (#773).

Feasible only on a tiny board: every free edge doubles the space. It lists
edge sets and filters them with `network.py`'s rule check, so no solver takes
part.
"""

import sys
from collections import Counter
from functools import cache
from itertools import product
from pathlib import Path
from typing import NamedTuple

sys.path.insert(0, str(Path(__file__).resolve().parent))
import network


def assignments(rows, cols, forced):
    """Every set of edges of the board that holds all of `forced`."""
    free = [e for e in network.all_edges(rows, cols) if e not in forced]
    base = frozenset(forced)
    return [
        base | {e for e, on in zip(free, bits, strict=True) if on}
        for bits in product((0, 1), repeat=len(free))
    ]


class Space(NamedTuple):
    """An exhaustively listed space: how many edges were free and how many
    assignments that makes, its valid networks, how many of them share each
    full set of outside numbers, and the networks alone under theirs."""

    free_edges: int
    assignments: int
    valid: frozenset
    by_numbers: Counter
    unique: frozenset


@cache
def two_crosses_in_r2():
    """The 4x4 space with exactly 2 crosses in r2 (#773). A cross cannot sit
    on the border, so the crosses are r2c2 and r2c3 and their 7 edges are
    forced on."""
    rows = cols = 4
    forced = {e for cell in ((1, 1), (1, 2)) for e in network.arm_edges(cell)}
    space = assignments(rows, cols, forced)
    valid = frozenset(
        net
        for net in space
        if not network.why_not_network(net, rows, cols)
        and network.outside_numbers(net, rows, cols)[0][1][network.CROSS] == 2
    )
    by_numbers = Counter(network.outside_numbers(net, rows, cols) for net in valid)
    unique = frozenset(
        net
        for net in valid
        if by_numbers[network.outside_numbers(net, rows, cols)] == 1
    )
    return Space(
        len(network.all_edges(rows, cols)) - len(forced),
        len(space),
        valid,
        by_numbers,
        unique,
    )
