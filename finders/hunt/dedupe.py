"""Canonical dedupe key under a finder's declared symmetry group (#483/#484).

`key(candidate)` (part of the finder contract) returns a flat tuple of cell
values, in whatever fixed order the finder chooses. A cell map is a tuple of
source indices the same length as that grid: `transformed[i] = grid[map[i]]`.
`D4` is generated from the grid's own side length (the grid must be square);
`IDENTITY` is the one-element group that changes nothing; a custom group is
any list of such maps, for a rule whose symmetry is not the whole square.

`canonical_key` is the least of the grid's images under the group -- equal
keys mean the same candidate up to that symmetry.
"""

from functools import lru_cache
from math import isqrt

D4 = "D4"
IDENTITY = "IDENTITY"


@lru_cache
def _d4_cell_maps(n):
    """The eight index maps of the n x n dihedral group, flat row-major."""

    def idx(r, c):
        return r * n + c

    rotations = (
        lambda r, c: (r, c),
        lambda r, c: (c, n - 1 - r),
        lambda r, c: (n - 1 - r, n - 1 - c),
        lambda r, c: (n - 1 - c, r),
    )
    maps = []
    for rot in rotations:
        maps.append(tuple(idx(*rot(r, c)) for r in range(n) for c in range(n)))
        maps.append(tuple(idx(*rot(r, n - 1 - c)) for r in range(n) for c in range(n)))
    return maps


def _validate_custom_group(maps, n):
    if not maps:
        raise ValueError("a custom symmetry group must not be empty")
    for cell_map in maps:
        if len(cell_map) != n or sorted(cell_map) != list(range(n)):
            raise ValueError(
                f"a custom cell map must be a permutation of range({n}), "
                f"got {cell_map!r}"
            )


def canonical_key(grid, group):
    grid = tuple(grid)
    if group == IDENTITY:
        return grid
    if group == D4:
        n = isqrt(len(grid))
        if n * n != len(grid):
            raise ValueError(f"D4 needs a square grid, got {len(grid)} cells")
        maps = _d4_cell_maps(n)
    else:
        _validate_custom_group(group, len(grid))
        maps = group
    return min(tuple(grid[i] for i in cell_map) for cell_map in maps)
