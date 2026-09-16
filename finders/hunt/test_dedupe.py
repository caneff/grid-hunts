"""The dedupe key holds up under each symmetry group (#484).

Independent of dedupe.py's own transform code: this test rotates and flips
a 4x4 shape by hand (plain nested-list index arithmetic) and checks
canonical_key agrees across all eight images under D4, disagrees under
IDENTITY, and follows a hand-picked custom group instead of the full D4 one.

    uv run finders/hunt/test_dedupe.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
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


ok = True


def check(name, cond):
    global ok
    status = "ok" if cond else "FAIL"
    if not cond:
        ok = False
    print(f"{status}: {name}")


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
transpose_map = (0, 2, 1, 3)  # (r, c) -> (c, r) on a 2x2 board, flat index
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

# A custom group that isn't a set of permutations must be rejected before
# any output is written -- a non-bijective map like (0, 0, 0, 0) collapses
# unrelated grids onto the same key, so a verified candidate would be
# silently dropped as a false duplicate (#507 review).
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

sys.exit(0 if ok else 1)
