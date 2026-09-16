"""Neighbour and connected-components helpers, on hand-drawn boards (#485).

uv run finders/hunt/test_grid.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from grid import connected_components, neighbors_king, neighbors_orthogonal

ok = True


def check(name, cond):
    global ok
    status = "ok" if cond else "FAIL"
    if not cond:
        ok = False
    print(f"{status}: {name}")


# --- neighbors_orthogonal, on a 3x5 (non-square) board ---

check(
    "orthogonal interior cell has 4 neighbours",
    sorted(neighbors_orthogonal(1, 2, 3, 5)) == [(0, 2), (1, 1), (1, 3), (2, 2)],
)
check(
    "orthogonal top-left corner has 2 neighbours",
    sorted(neighbors_orthogonal(0, 0, 3, 5)) == [(0, 1), (1, 0)],
)
check(
    "orthogonal bottom-right corner has 2 neighbours",
    sorted(neighbors_orthogonal(2, 4, 3, 5)) == [(1, 4), (2, 3)],
)
check(
    "orthogonal top edge (not corner) has 3 neighbours",
    sorted(neighbors_orthogonal(0, 2, 3, 5)) == [(0, 1), (0, 3), (1, 2)],
)
check(
    "orthogonal right edge (not corner) has 3 neighbours",
    sorted(neighbors_orthogonal(1, 4, 3, 5)) == [(0, 4), (1, 3), (2, 4)],
)

# --- neighbors_king, on the same 3x5 board ---

check(
    "king interior cell has 8 neighbours",
    sorted(neighbors_king(1, 2, 3, 5))
    == sorted(
        [
            (0, 1),
            (0, 2),
            (0, 3),
            (1, 1),
            (1, 3),
            (2, 1),
            (2, 2),
            (2, 3),
        ]
    ),
)
check(
    "king top-left corner has 3 neighbours",
    sorted(neighbors_king(0, 0, 3, 5)) == [(0, 1), (1, 0), (1, 1)],
)
check(
    "king bottom-right corner has 3 neighbours",
    sorted(neighbors_king(2, 4, 3, 5)) == [(1, 3), (1, 4), (2, 3)],
)
check(
    "king top edge (not corner) has 5 neighbours",
    sorted(neighbors_king(0, 2, 3, 5))
    == sorted([(0, 1), (0, 3), (1, 1), (1, 2), (1, 3)]),
)

# --- connected_components, hand-drawn 4x4 board ---
#
#   1 1 0 0
#   1 0 0 1
#   0 0 1 1
#   0 0 0 0
#
# orthogonal adjacency: the two 1s in row 0 join the 1 below-left of them
# (one group of three, since (0,0)-(0,1) and (0,0)-(1,0) are each
# orthogonally adjacent); the two 1s at (2,2)/(2,3) join (1,3) below-right
# of the first (via (2,3)) into a second group of three. (1,3) is diagonal
# to (2,2), not orthogonally adjacent to it -- the group only holds together
# because (2,3) is orthogonally adjacent to both.
BOARD = [
    [1, 1, 0, 0],
    [1, 0, 0, 1],
    [0, 0, 1, 1],
    [0, 0, 0, 0],
]

components = connected_components(BOARD)
sorted_components = sorted(sorted(comp) for comp in components)
check(
    "hand-drawn board's components match by hand",
    sorted_components == [[(0, 0), (0, 1), (1, 0)], [(1, 3), (2, 2), (2, 3)]],
)

# A diagonal-only touch must NOT merge components under orthogonal
# adjacency (it would under king adjacency), so this board is the one that
# tells the two apart:
#
#   1 0 1 0
#   0 1 0 1
#   0 0 0 0
#   0 0 0 0
#
# (0,0), (0,2), (1,1), (1,3) touch each other only diagonally -- four
# singleton components, not one group of four.
DIAGONAL_ONLY_BOARD = [
    [1, 0, 1, 0],
    [0, 1, 0, 1],
    [0, 0, 0, 0],
    [0, 0, 0, 0],
]
diagonal_components = connected_components(DIAGONAL_ONLY_BOARD)
check(
    "diagonally-touching cells stay in separate components (orthogonal, not king)",
    sorted(sorted(comp) for comp in diagonal_components)
    == [[(0, 0)], [(0, 2)], [(1, 1)], [(1, 3)]],
)

empty_components = connected_components([[0, 0], [0, 0]])
check("an all-empty board has no components", empty_components == [])

full_components = connected_components([[1, 1], [1, 1]])
check(
    "a fully-filled board is one component",
    sorted(full_components[0]) == [(0, 0), (0, 1), (1, 0), (1, 1)]
    and len(full_components) == 1,
)

ragged_raised = False
try:
    connected_components([[1, 1, 1], [1, 0]])
except ValueError:
    ragged_raised = True
check("a ragged grid raises ValueError instead of dropping cells", ragged_raised)

sys.exit(0 if ok else 1)
