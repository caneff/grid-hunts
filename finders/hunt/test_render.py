"""The grid-drawing base's public function: image size, sampled pixels (#490).

uv run finders/hunt/test_render.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from render import GridCanvas

ok = True


def check(name, cond):
    global ok
    status = "ok" if cond else "FAIL"
    if not cond:
        ok = False
    print(f"{status}: {name}")


# --- image size, for a given grid size and cell size ---

canvas = GridCanvas(4, 4, cell=20, margin=10)
check(
    "a 4x4 board at cell=20, margin=10 is 100x100",
    canvas.image.size == (100, 100),
)

canvas_rect = GridCanvas(3, 5, cell=10, margin=4)
check(
    "a non-square (3 rows, 5 cols) board sizes width and height independently",
    canvas_rect.image.size == (5 * 10 + 2 * 4, 3 * 10 + 2 * 4),
)

canvas_default_bg = GridCanvas(2, 2, cell=10, margin=0)
check(
    "an undrawn cell is white by default",
    canvas_default_bg.image.getpixel((5, 5)) == (255, 255, 255),
)

# --- shaded and plain cells, sampled at the cell's own centre pixel ---

canvas_shaded = GridCanvas(3, 3, cell=30, margin=0, background="white")
canvas_shaded.shade_cell(1, 1, (200, 0, 0))
check(
    "a shaded cell's centre pixel is that colour",
    canvas_shaded.image.getpixel((45, 45)) == (200, 0, 0),
)
check(
    "an untouched cell's centre pixel is still the background colour",
    canvas_shaded.image.getpixel((15, 15)) == (255, 255, 255),
)

canvas_row_col = GridCanvas(2, 4, cell=10, margin=5, background="white")
canvas_row_col.shade_cell(1, 3, (0, 150, 0))
# Row 1, col 3 centre: margin + col*cell + cell/2, margin + row*cell + cell/2
check(
    "shade_cell targets (row, col), not (col, row)",
    canvas_row_col.image.getpixel((5 + 3 * 10 + 5, 5 + 1 * 10 + 5)) == (0, 150, 0),
)

# --- box_lines: thick on box boundaries, thin elsewhere, sampled by pixel ---

canvas_lines = GridCanvas(4, 4, cell=20, margin=0, background="white")
canvas_lines.box_lines(box_rows=2, box_cols=2, thin=1, thick=5, color="black")
# The horizontal line at y=0 (a box boundary, i=0) is thick -> pixel at
# (10, 2) (3rd row down from a 1px-thin line) is still on the thick line.
check(
    "a box-boundary line is thick enough to cover a pixel a thin line would miss",
    canvas_lines.image.getpixel((10, 2)) == (0, 0, 0),
)
# The vertical line at x=20 (i=1, not a box multiple of 2) is thin -> a
# pixel 2px away from it is background, not line.
check(
    "a non-boundary line is thin: a pixel just past it is background",
    canvas_lines.image.getpixel((22, 10)) == (255, 255, 255),
)

# --- box_lines: the outer edge is always thick, even when n_rows/n_cols
# isn't a multiple of box_rows/box_cols (#490 correctness review C3) ---

canvas_uneven = GridCanvas(5, 5, cell=20, margin=0, background="white")
canvas_uneven.box_lines(box_rows=3, box_cols=3, thin=1, thick=5)
check(
    "the bottom edge is thick even when n_rows % box_rows != 0",
    canvas_uneven.image.getpixel((10, 98)) == (0, 0, 0),
)
check(
    "the right edge is thick even when n_cols % box_cols != 0",
    canvas_uneven.image.getpixel((98, 10)) == (0, 0, 0),
)

value_error_raised = False
try:
    GridCanvas(4, 4, cell=10).box_lines(box_rows=0, box_cols=4)
except ValueError:
    value_error_raised = True
check(
    "box_lines(box_rows=0, ...) raises ValueError, not a bare ZeroDivisionError",
    value_error_raised,
)

# --- circle: centred in the cell, sampled at its own ring pixel ---

canvas_circle = GridCanvas(2, 2, cell=40, margin=0, background="white")
canvas_circle.circle(0, 0, color=(0, 0, 255), width=4, radius_frac=0.4)
check(
    "a circle's ring pixel (top of the circle) is the given colour",
    canvas_circle.image.getpixel((20, 4)) == (0, 0, 255),
)
check(
    "a circle's own centre is untouched when it has no fill",
    canvas_circle.image.getpixel((20, 20)) == (255, 255, 255),
)

canvas_circle_fill = GridCanvas(1, 1, cell=40, margin=0, background="white")
canvas_circle_fill.circle(0, 0, color="black", fill=(255, 0, 0), radius_frac=0.4)
check(
    "a filled circle's centre pixel is the fill colour",
    canvas_circle_fill.image.getpixel((20, 20)) == (255, 0, 0),
)

# --- digit: draws something other than background in the cell (text
# anti-aliasing makes an exact colour match at a chosen pixel unreliable,
# so this checks the cell actually changed, not a specific pixel) ---

canvas_digit = GridCanvas(1, 1, cell=40, margin=0, background="white")
canvas_digit.digit(0, 0, "5", color="black")
cell_pixels = [
    canvas_digit.image.getpixel((x, y)) for x in range(40) for y in range(40)
]
check(
    "drawing a digit changes at least one pixel in its cell",
    any(p != (255, 255, 255) for p in cell_pixels),
)

sys.exit(0 if ok else 1)
