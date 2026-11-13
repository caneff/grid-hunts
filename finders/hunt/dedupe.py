"""Canonical dedupe key under a finder's symmetry group (#483/#484).

A cell map is a tuple of source indices: `transformed[i] = grid[map[i]]`.
`D4` is built from the grid's side length (square grids only); `IDENTITY`
changes nothing; a custom group is a list of such maps. `canonical_key` is the
least image under the group.
"""

from functools import lru_cache
from math import isqrt

D4 = "D4"
IDENTITY = "IDENTITY"


@lru_cache
def d4_cell_maps(n):
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


def _normalize_group(maps):
    """A hashable tuple-of-tuples for `maps`; raises if it is empty."""
    maps = list(maps)
    if not maps:
        raise ValueError("a custom symmetry group must not be empty")
    return tuple(tuple(m) for m in maps)


@lru_cache
def _validate_custom_group(maps, n):
    """Validate `maps` is a group of permutations of range(n): each map a
    bijection, closed under composition. The minimum image is only an
    equivalence when the maps form a group; a non-closed set such as
    `[identity, rotate90]` merges unrelated grids as false duplicates (#508).

    No separate identity check: closure alone forces the identity.

    Cached, so `maps` is a tuple of tuples: the closure check is O(k^2 * n).
    """
    for cell_map in maps:
        if len(cell_map) != n or sorted(cell_map) != list(range(n)):
            raise ValueError(
                f"a custom cell map must be a permutation of range({n}), "
                f"got {cell_map!r}"
            )
    map_set = set(maps)
    for f in maps:
        for g in maps:
            composed = tuple(f[g[i]] for i in range(n))
            if composed not in map_set:
                raise ValueError(
                    "a custom symmetry group must be closed under "
                    f"composition: {f!r} composed with {g!r} gives "
                    f"{composed!r}, which is not one of the declared maps "
                    f"{maps!r}"
                )


def validate_group(maps):
    """Validate a custom symmetry group before any candidate exists: the checks
    `canonical_key` runs, with `n` taken from the group's own maps."""
    maps = _normalize_group(maps)
    _validate_custom_group(maps, len(maps[0]))


def canonical_key(grid, group):
    """The least image of `grid` under `group` (D4, IDENTITY or custom maps)."""
    grid = tuple(grid)
    if group == IDENTITY:
        return grid
    if group == D4:
        n = isqrt(len(grid))
        if n * n != len(grid):
            raise ValueError(f"D4 needs a square grid, got {len(grid)} cells")
        maps = d4_cell_maps(n)
    else:
        maps = _normalize_group(group)
        _validate_custom_group(maps, len(grid))
    return min(tuple(grid[i] for i in cell_map) for cell_map in maps)
