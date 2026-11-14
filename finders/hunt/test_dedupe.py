"""Rotates and flips a 4x4 shape by hand, independent of dedupe.py's transforms."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cli_checks import check, finish
from dedupe import D4, IDENTITY, canonical_key

N = 4


def flat(rows):
    return tuple(v for row in rows for v in row)


def rotate90(rows):
    n = len(rows)
    return [[rows[n - 1 - c][r] for c in range(n)] for r in range(n)]


def flip_h(rows):
    return [list(reversed(row)) for row in rows]


def eight_images(rows):
    out = []
    cur = rows
    for _ in range(4):
        out.append(cur)
        out.append(flip_h(cur))
        cur = rotate90(cur)
    return out


# An asymmetric L-tetromino-ish shape: no image of it equals another image
# under a smaller group, so a bug that only checks 4 of the 8 transforms
# would still pass by accident if the shape were symmetric.
SHAPE = [
    [1, 0, 0, 0],
    [1, 0, 0, 0],
    [1, 1, 0, 0],
    [0, 0, 0, 0],
]

images = eight_images(SHAPE)
keys_d4 = {canonical_key(flat(img), D4) for img in images}
check("D4 gives one key for all eight images", len(keys_d4) == 1)

keys_identity = {canonical_key(flat(img), IDENTITY) for img in images}
check(
    "IDENTITY does not merge images that D4 would",
    len(keys_identity) > 1,
)
check(
    "IDENTITY's key is the grid itself, untransformed",
    canonical_key(flat(SHAPE), IDENTITY) == flat(SHAPE),
)

# A custom group over a 2x2 grid: identity plus a diagonal transpose only
# (not the full D4 of a 2x2 board), so a rotation-only duplicate must NOT
# be merged even though a 90-degree rotation is in D4. The live cell sits
# off the transpose's diagonal (not a fixed point of the map), so a broken
# handler that silently drops the transpose and dedupes by identity alone
# gives a different answer than the real one -- a live cell on the
# diagonal would pass either way and prove nothing.
tiny = [
    [0, 1],
    [0, 0],
]
tiny_rotated_90 = rotate90(tiny)
transpose_map = (0, 2, 1, 3)
custom_group = [(0, 1, 2, 3), transpose_map]

key_tiny = canonical_key(flat(tiny), custom_group)
key_rot = canonical_key(flat(tiny_rotated_90), custom_group)
check(
    "a custom group dedupes only by its own maps, not by D4",
    key_tiny != key_rot,
)

transposed = [[tiny[c][r] for c in range(2)] for r in range(2)]
key_transposed = canonical_key(flat(transposed), custom_group)
check(
    "a custom group's own map is honoured",
    key_tiny == key_transposed,
)

try:
    canonical_key(flat(tiny), [(0, 0, 0, 0)])
    check("a non-permutation cell map is rejected", False)
except ValueError:
    check("a non-permutation cell map is rejected", True)

try:
    canonical_key(flat(tiny), [(0, 1, 2)])
    check("a cell map of the wrong length is rejected", False)
except ValueError:
    check("a cell map of the wrong length is rejected", True)

try:
    canonical_key(flat(tiny), [])
    check("an empty custom group is rejected", False)
except ValueError:
    check("an empty custom group is rejected", True)

identity_2x2 = (0, 1, 2, 3)
rotate90_2x2 = (1, 3, 0, 2)
rotate180_2x2 = (3, 2, 1, 0)

try:
    canonical_key(flat(tiny), [identity_2x2, rotate90_2x2])
    check("[identity, rotate90] (not closed) is rejected", False)
except ValueError:
    check("[identity, rotate90] (not closed) is rejected", True)

try:
    canonical_key(flat(tiny), [rotate90_2x2, rotate180_2x2, rotate180_2x2])
    check("a custom group missing the identity is rejected", False)
except ValueError:
    check("a custom group missing the identity is rejected", True)

try:
    canonical_key(flat(tiny), [identity_2x2, rotate180_2x2])
    check("identity + 180-degree rotation (a valid subgroup) is accepted", True)
except ValueError:
    check("identity + 180-degree rotation (a valid subgroup) is accepted", False)

try:
    canonical_key(flat(tiny), {identity_2x2, rotate90_2x2})
    check("a non-closed custom group given as a set is rejected", False)
except ValueError:
    check("a non-closed custom group given as a set is rejected", True)
except TypeError:
    check("a non-closed custom group given as a set is rejected", False)

finish()
