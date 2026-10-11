"""A hybrid grid as a picture (#791): the board in the puzzle's layout, with
its regions coloured and a ring on every cell a circle could sit on.

`Picture(net, rows, cols, circles, blank_strip).image` is a PIL image. The
strips of number cells lie above the grid and to its left with every outside
number filled in, the icon cells at the head of each strip, and the network
runs through the grid cells. A chocolate is one colour; each banana has a
tint of its own, so separate bananas can be told apart and counted, and a
heavy line runs wherever cells of different parity meet. A ring marks every
valid circle, a cell whose value is the size of its region: a heavier ring
in a second colour when the circle is one of the grid's conditions.
Everything the picture says about values, regions and circles is
`hybrid.py`'s, the solver-free rule reader; no model is asked.

`hybrid_finder.py render` is the command that writes one.
"""

import colorsys
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "hunt"))
# isort: split
import hybrid
from render import GridCanvas

CELL = 64
MARGIN = 20
BACKGROUND = (255, 255, 255)
CHOCOLATE = (201, 162, 126)
# The first bananas' tints, the largest banana first; `_tint` goes on past
# them.
TINTS = (
    (255, 243, 166),
    (255, 210, 127),
    (217, 240, 163),
    (191, 227, 245),
    (247, 198, 220),
    (216, 201, 242),
    (200, 235, 216),
    (255, 224, 194),
)
PARITY_LINE = (93, 58, 26)
ICON = (232, 185, 35)
GRID_LINE = (136, 136, 136)
FRAME = (0, 0, 0)
NETWORK = (21, 101, 192)
# A ring on a valid circle, and the heavier one on a circle that is a
# condition of the grid.
VALID_RING = (198, 40, 40)
GIVEN_RING = (106, 27, 154)
NUMBER_SIZE = 34


def _tint(i):
    """The i-th banana's tint: `TINTS`, then pale hues a golden-ratio step
    apart, so no two bananas of one picture share one."""
    if i < len(TINTS):
        return TINTS[i]
    red, green, blue = colorsys.hls_to_rgb((i * 0.618034) % 1, 0.86, 0.9)
    return round(red * 255), round(green * 255), round(blue * 255)


class Picture(GridCanvas):
    """The picture of one hybrid grid. Raises ValueError, saying why, when
    the edges and circles are not a hybrid grid on the board drawn: a region
    coloured as a chocolate is then a rectangle, and the picture never shows
    a grid the rules refuse."""

    def __init__(self, net, rows, cols, circles=(), blank_strip=False):
        why = hybrid.why_not_hybrid(net, rows, cols, circles, blank_strip)
        if why:
            raise ValueError(f"not a hybrid grid: {why}")
        self.rows, self.cols = rows, cols
        self.depth = hybrid.strips(blank_strip)
        super().__init__(rows + self.depth, cols + self.depth, CELL, MARGIN, BACKGROUND)
        self.board = hybrid.values(net, rows, cols, blank_strip)
        self._cells()
        self._parity_lines()
        self._icons()
        self._frames()
        given = set(circles)
        for r, c in hybrid.valid_circles(self.board):
            colour, width = (GIVEN_RING, 7) if (r, c) in given else (VALID_RING, 4)
            self.circle(r + self.depth, c + self.depth, colour, width, radius_frac=0.41)
        # Each edge runs from one cell's centre to the next, so the bar's
        # reach is one cell; drawn last, over the rings.
        for first, second in net:
            self._arm(first, 1 if first[0] == second[0] else 2, NETWORK, 4, CELL)

    def box(self, cell):
        """The (x0, y0, x1, y1) pixel box of a cell of the board, or of an
        icon cell."""
        r, c = cell
        return self._cell_box(r + self.depth, c + self.depth)

    def _cells(self):
        """Every cell's fill and thin outline, and a number cell's number."""
        bananas = sorted(
            (g for g in hybrid.regions(self.board) if self.board[min(g)] % 2),
            key=len,
            reverse=True,
        )
        tint = {cell: _tint(i) for i, g in enumerate(bananas) for cell in g}
        for cell, value in self.board.items():
            r, c = cell
            numbered = min(cell) < 0
            self.draw.rectangle(
                self.box(cell),
                fill=tint.get(cell, CHOCOLATE),
                outline=FRAME if numbered else GRID_LINE,
            )
            if numbered:
                self.digit(r + self.depth, c + self.depth, value, font_size=NUMBER_SIZE)

    def _parity_lines(self):
        """A heavy line along every side two cells of different parity
        share."""
        for (r, c), value in self.board.items():
            for dr, dc in ((0, 1), (1, 0)):
                other = self.board.get((r + dr, c + dc))
                if other is None or other % 2 == value % 2:
                    continue
                x0, y0, _, _ = self.box((r + dr, c + dc))
                end = (x0, y0 + CELL) if dc else (x0 + CELL, y0)
                self.draw.line([(x0, y0), end], fill=PARITY_LINE, width=5)

    def _arm(self, cell, arm, colour, half, reach):
        """One arm of a piece: a filled bar from the cell's centre `reach`
        pixels towards north, east, south or west (`arm` 0 to 3), running
        `half` pixels past both ends, so two arms at a right angle meet in a
        full square corner with no notch."""
        x0, y0, x1, y1 = self.box(cell)
        cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
        dx, dy = ((0, -1), (1, 0), (0, 1), (-1, 0))[arm]
        xs = sorted((cx, cx + dx * reach))
        ys = sorted((cy, cy + dy * reach))
        self.draw.rectangle(
            [xs[0] - half, ys[0] - half, xs[1] + half - 1, ys[1] + half - 1],
            fill=colour,
        )

    def _icons(self):
        """The icon cell at the head of each strip: the piece the strip
        counts, and for the blank strip an empty cell."""
        for k in range(1, self.depth + 1):
            for cell in ((-k, -1), (-1, -k)):
                self.draw.rectangle(
                    self.box(cell), fill=BACKGROUND, outline=FRAME, width=3
                )
                for arm, has in enumerate(hybrid.icon_arms(cell)):
                    if has:
                        self._arm(cell, arm, ICON, 3, CELL // 2 - 3)

    def _frames(self):
        """Heavy frames around the grid and around each block of strips."""
        depth, rows, cols = self.depth, self.rows, self.cols
        for top, left, height, width in (
            (-depth, 0, depth, cols),
            (0, -depth, rows, depth),
            (0, 0, rows, cols),
        ):
            x0, y0, _, _ = self.box((top, left))
            self.draw.rectangle(
                [x0, y0, x0 + width * CELL, y0 + height * CELL],
                outline=FRAME,
                width=4,
            )
