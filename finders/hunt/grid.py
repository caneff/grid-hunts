"""Neighbour and connected-components helpers over a grid (#483/#485).

Standalone, usable without the driver -- see `finders/AGENTS.md`. A grid is
any rows-of-cells sequence (`grid[r][c]`), not required to be square, so a
finder on a non-9x9 board (or a rectangular one) uses these unchanged.
"""

_ORTHOGONAL_OFFSETS = ((-1, 0), (1, 0), (0, -1), (0, 1))
_KING_OFFSETS = tuple(
    (dr, dc) for dr in (-1, 0, 1) for dc in (-1, 0, 1) if (dr, dc) != (0, 0)
)


def _neighbors(r, c, n_rows, n_cols, offsets):
    return [
        (r + dr, c + dc)
        for dr, dc in offsets
        if 0 <= r + dr < n_rows and 0 <= c + dc < n_cols
    ]


def neighbors_orthogonal(r, c, n_rows, n_cols):
    """The in-bounds up/down/left/right neighbours of (r, c)."""
    return _neighbors(r, c, n_rows, n_cols, _ORTHOGONAL_OFFSETS)


def neighbors_king(r, c, n_rows, n_cols):
    """The in-bounds 8-directional neighbours of (r, c)."""
    return _neighbors(r, c, n_rows, n_cols, _KING_OFFSETS)


def connected_components(labels):
    """The orthogonally-connected groups of truthy cells in `labels`.

    `labels` is a rows-of-cells sequence of any truthy/falsy values (bool,
    0/1, ...). Every row must be the same length -- a ragged grid raises
    `ValueError` rather than silently dropping cells past the first row's
    width. Returns a list of components, each a list of (r, c) cells; an
    all-empty board returns an empty list.
    """
    n_rows = len(labels)
    n_cols = len(labels[0]) if n_rows else 0
    for row in labels:
        if len(row) != n_cols:
            raise ValueError(
                f"connected_components needs equal-length rows, got "
                f"{n_cols} and {len(row)}"
            )
    seen = set()
    components = []
    for r in range(n_rows):
        for c in range(n_cols):
            if not labels[r][c] or (r, c) in seen:
                continue
            stack = [(r, c)]
            seen.add((r, c))
            component = []
            while stack:
                cr, cc = stack.pop()
                component.append((cr, cc))
                for nr, nc in neighbors_orthogonal(cr, cc, n_rows, n_cols):
                    if labels[nr][nc] and (nr, nc) not in seen:
                        seen.add((nr, nc))
                        stack.append((nr, nc))
            components.append(component)
    return components
