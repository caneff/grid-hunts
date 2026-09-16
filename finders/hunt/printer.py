"""Text board printer, so a finder can eyeball a candidate in a terminal
(#483/#485).

Standalone, usable without the driver -- see `finders/AGENTS.md`.
"""


def render_board(grid, empty="."):
    """Render a rows-of-cells grid as space-separated text, one line per row.

    Each cell prints as `str(cell)`, except `None`, which prints as `empty`
    -- a real cell value of 0 or "" is not empty, only the absence of one
    is. No border: a hunt candidate is eyeballed inline, not framed.
    """
    return "\n".join(
        " ".join(empty if cell is None else str(cell) for cell in row) for row in grid
    )
