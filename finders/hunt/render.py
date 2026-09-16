"""PIL grid-drawing base a finder's renderer extends (#483/#490).

`GridCanvas` owns the image: cells, box lines, shading, digits, circles. A
finder's own render module builds one, draws its candidate onto it, and
returns `.image` to the driver. Standalone, usable without the driver -- see
`finders/AGENTS.md`.
"""

from functools import lru_cache

from PIL import Image, ImageDraw, ImageFont

DEFAULT_FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"


@lru_cache
def _load_font(font_path, size):
    """Cache the parsed font by (path, size): `digit()` is called once per
    filled cell, and re-parsing the same TTF from disk every time is
    wasted work on every render (#490 correctness review)."""
    return ImageFont.truetype(font_path, size)


class GridCanvas:
    """A blank grid of `n_rows` x `n_cols` cells, each `cell` pixels square,
    with `margin` pixels of border on every side."""

    def __init__(self, n_rows, n_cols, cell=64, margin=20, background="white"):
        self.n_rows = n_rows
        self.n_cols = n_cols
        self.cell = cell
        self.margin = margin
        width = n_cols * cell + 2 * margin
        height = n_rows * cell + 2 * margin
        self.image = Image.new("RGB", (width, height), background)
        self.draw = ImageDraw.Draw(self.image)

    def _cell_box(self, r, c):
        """The (x0, y0, x1, y1) pixel box of cell (r, c)."""
        x0 = self.margin + c * self.cell
        y0 = self.margin + r * self.cell
        return x0, y0, x0 + self.cell, y0 + self.cell

    def _cell_center(self, r, c):
        x0, y0, x1, y1 = self._cell_box(r, c)
        return (x0 + x1) / 2, (y0 + y1) / 2

    def shade_cell(self, r, c, color):
        """Fill cell (r, c) with a flat colour."""
        self.draw.rectangle(self._cell_box(r, c), fill=color)

    def box_lines(self, box_rows, box_cols, thin=1, thick=4, color="black"):
        """Grid lines over the whole board: thick every `box_rows`/`box_cols`
        cells and always on the outer edge (even when `n_rows`/`n_cols`
        isn't a multiple of `box_rows`/`box_cols`), thin otherwise. Draws
        the line centred on the boundary, so a `margin` under `thick / 2`
        clips the outer edge -- match the margin to the line weight, as the
        existing board renderers in `finders/` do (`MARGIN=24` for a
        `width=5` box line)."""
        if box_rows <= 0 or box_cols <= 0:
            raise ValueError(
                f"box_rows and box_cols must be positive, got {box_rows}, {box_cols}"
            )
        left = self.margin
        top = self.margin
        right = self.margin + self.n_cols * self.cell
        bottom = self.margin + self.n_rows * self.cell
        for i in range(self.n_rows + 1):
            is_boundary = i in (0, self.n_rows) or i % box_rows == 0
            width = thick if is_boundary else thin
            y = self.margin + i * self.cell
            self.draw.line((left, y, right, y), fill=color, width=width)
        for j in range(self.n_cols + 1):
            is_boundary = j in (0, self.n_cols) or j % box_cols == 0
            width = thick if is_boundary else thin
            x = self.margin + j * self.cell
            self.draw.line((x, top, x, bottom), fill=color, width=width)

    def digit(self, r, c, text, color="black", font_size=None, font_path=DEFAULT_FONT):
        """A centred digit (or short string) in cell (r, c)."""
        size = font_size or int(self.cell * 0.6)
        font = _load_font(font_path, size)
        cx, cy = self._cell_center(r, c)
        self.draw.text((cx, cy), str(text), fill=color, font=font, anchor="mm")

    def circle(self, r, c, color="black", width=3, radius_frac=0.38, fill=None):
        """A circle centred in cell (r, c), sized as a fraction of the cell."""
        cx, cy = self._cell_center(r, c)
        rad = self.cell * radius_frac
        self.draw.ellipse(
            (cx - rad, cy - rad, cx + rad, cy + rad),
            outline=color,
            width=width,
            fill=fill,
        )
