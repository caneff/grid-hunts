"""Exhaustive enumeration of U-Bahn edge assignments, for the tests (#773).

Feasible only on a tiny board: every free edge doubles the space. It lists
edge sets and filters them with `network.py`'s rule check, so no solver takes
part.

The hybrid's answers (#782) come from the same pass, judged by `hybrid.py`:

    uv run finders/ubahn/brute.py 4 4 [--blank-strip] [--draw] \
        [--circles "r2c2 c1:turn"]...

prints how many edge sets have no dead end, how many are valid hybrid grids,
and each `--circles` condition's classification.
"""

import argparse
import sys
from collections import Counter
from functools import cache
from itertools import product
from pathlib import Path
from typing import NamedTuple

sys.path.insert(0, str(Path(__file__).resolve().parent))
import hybrid
import network


def assignments(rows, cols, forced):
    """Every set of edges of the board that holds all of `forced`."""
    free = [e for e in network.all_edges(rows, cols) if e not in forced]
    base = frozenset(forced)
    return [
        base | {e for e, on in zip(free, bits, strict=True) if on}
        for bits in product((0, 1), repeat=len(free))
    ]


def no_dead_end(rows, cols):
    """Every set of edges of the board that leaves no cell with one arm, the
    empty set among them. Cell by cell in reading order: a cell's north and
    west edges are decided by then, so its east and south edges are chosen
    together and a choice that leaves it one arm is dropped with everything
    under it."""
    on_board = set(network.all_edges(rows, cols))
    cells = [(r, c) for r in range(rows) for c in range(cols)]
    on = set()

    def extend(i):
        if i == len(cells):
            yield frozenset(on)
            return
        north, east, south, west = network.arm_edges(cells[i])
        had = (north in on) + (west in on)
        free = [e for e in (east, south) if e in on_board]
        for bits in product((0, 1), repeat=len(free)):
            if had + sum(bits) == 1:
                continue
            added = [e for e, bit in zip(free, bits, strict=True) if bit]
            on.update(added)
            yield from extend(i + 1)
            on.difference_update(added)

    return extend(0)


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


@cache
def hybrid_grids(rows, cols, blank_strip=False):
    """Every valid hybrid grid of the board with no condition, as a frozenset
    of networks: each edge set with no dead end, judged by `hybrid.py`."""
    return frozenset(
        net
        for net in no_dead_end(rows, cols)
        if not hybrid.why_not_hybrid(net, rows, cols, blank_strip=blank_strip)
    )


def classify(rows, cols, circles, blank_strip=False):
    """(word, count): how many valid hybrid grids meet these circles, and the
    uniqueness check's word for it: "infeasible" for none, "unique" for one,
    "not_unique" for more. A circle only ever rules a grid out, so the grids
    with no condition are the ones to ask."""
    count = sum(
        1
        for net in hybrid_grids(rows, cols, blank_strip)
        if not hybrid.why_not_hybrid(net, rows, cols, circles, blank_strip)
    )
    return ("infeasible", "unique", "not_unique")[min(count, 2)], count


def main(argv):
    parser = argparse.ArgumentParser(
        description="Count a tiny board's valid hybrid grids by brute force."
    )
    parser.add_argument("rows", type=int)
    parser.add_argument("cols", type=int)
    parser.add_argument("--blank-strip", action="store_true")
    parser.add_argument("--draw", action="store_true", help="draw every valid grid")
    parser.add_argument(
        "--circles",
        action="append",
        default=[],
        metavar="CELLS",
        help="circled cells to classify, as in 'r2c2 c1:turn'; may repeat",
    )
    args = parser.parse_args(argv)
    rows, cols, blank_strip = args.rows, args.cols, args.blank_strip
    edges = len(network.all_edges(rows, cols))
    kept = sum(1 for _ in no_dead_end(rows, cols))
    grids = hybrid_grids(rows, cols, blank_strip)
    strip = " with the blank strip" if blank_strip else ""
    print(f"{rows}x{cols}{strip}: {2**edges} edge sets, {kept} with no dead end")
    print(f"valid hybrid grids, no condition: {len(grids)}")
    for text in args.circles:
        circles = frozenset(hybrid.parse_cell(name) for name in text.split())
        word, count = classify(rows, cols, circles, blank_strip)
        print(f"circles {text}: {word} ({count})")
    if args.draw:
        for net in sorted(grids, key=sorted):
            print()
            print("\n".join(hybrid.drawing(net, rows, cols, blank_strip=blank_strip)))


if __name__ == "__main__":
    main(sys.argv[1:])
