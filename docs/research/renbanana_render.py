"""Pictures for Renbanana candidates (#380): chocolate/banana fill, digits, circles.

    uv run --with pillow docs/research/renbanana_render.py cand_00.json out.png
    uv run --with pillow docs/research/renbanana_render.py --html DIR page.html

A circle marks a cell whose digit equals the size of its own chocolate group —
a clue the puzzle could offer, not one that has been chosen. The HTML mode
collects every `cand_*.json` in a directory into one page, PNGs inlined, so a
batch is reviewed in a single file rather than as loose images.
"""

import base64
import html
import io
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

N = 9
CELL = 64
MARGIN = 16
SIDE = N * CELL + 2 * MARGIN
CHOCOLATE = (110, 72, 46)
BANANA = (250, 236, 150)
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


def render(d):
    img = Image.new("RGB", (SIDE, SIDE), "white")
    dr = ImageDraw.Draw(img)
    font = ImageFont.truetype(FONT, 32)
    circles = {tuple(p) for p in d.get("circles", [])}
    for r in range(N):
        for c in range(N):
            x0, y0 = MARGIN + c * CELL, MARGIN + r * CELL
            choc = d["shading"][r][c] == "C"
            dr.rectangle(
                [x0, y0, x0 + CELL, y0 + CELL], fill=CHOCOLATE if choc else BANANA
            )
            if (r, c) in circles:
                dr.ellipse(
                    [x0 + 7, y0 + 7, x0 + CELL - 7, y0 + CELL - 7],
                    outline="white" if choc else "black",
                    width=4,
                )
            t = d["grid"][r][c]
            bb = dr.textbbox((0, 0), t, font=font)
            dr.text(
                (
                    x0 + CELL / 2 - (bb[2] - bb[0]) / 2,
                    y0 + CELL / 2 - (bb[3] - bb[1]) / 2 - 4,
                ),
                t,
                fill="white" if choc else "black",
                font=font,
            )
    for i in range(N + 1):
        w = 4 if i % 3 == 0 else 1
        dr.line(
            [MARGIN + i * CELL, MARGIN, MARGIN + i * CELL, MARGIN + N * CELL],
            fill="black",
            width=w,
        )
        dr.line(
            [MARGIN, MARGIN + i * CELL, MARGIN + N * CELL, MARGIN + i * CELL],
            fill="black",
            width=w,
        )
    return img


def data_uri(img):
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


PAGE = """<!doctype html>
<meta charset="utf-8"><title>Renbanana candidates</title>
<style>
 body {{ font: 15px/1.5 system-ui, sans-serif; margin: 2rem; max-width: 62rem; }}
 .card {{ display: flex; gap: 1.5rem; align-items: flex-start;
          border-top: 1px solid #ddd; padding: 1.5rem 0; }}
 img {{ width: 340px; image-rendering: auto; }}
 dt {{ font-weight: 600; }} dd {{ margin: 0 0 .4rem 0; }}
 code {{ background: #f4f4f4; padding: 0 .2rem; }}
</style>
<h1>Renbanana candidates</h1>
<p>Chocolate is brown, banana is yellow. A circle marks a cell whose digit
equals the size of its own chocolate group — a clue the grid could carry.
Every grid below was re-checked from scratch by <code>renbanana_verify.py</code>.</p>
{cards}
"""

CARD = """<div class="card"><img src="{png}" alt="grid">
<dl>
 <dt>{name}</dt><dd>objective <code>{objective}</code> = <b>{value}</b>, seed {seed}</dd>
 <dt>shapes</dt><dd>{shapes}</dd>
 <dt>chocolate</dt><dd>{cells} cells in {groups} groups, largest {largest}</dd>
 <dt>circle-bearing groups</dt><dd>{circleable}</dd>
</dl></div>"""


def page(directory, out):
    cards = []
    for path in sorted(Path(directory).glob("cand_*.json")):
        d = json.loads(path.read_text())
        prof = d["profile"]
        cards.append(
            CARD.format(
                png=data_uri(render(d)),
                name=html.escape(path.name),
                objective=html.escape(d["objective"]),
                value=d["value"],
                seed=d["seed"],
                shapes=html.escape(" ".join(prof["shapes"])),
                cells=prof["chocolate_cells"],
                groups=prof["chocolate_groups"],
                largest=prof["largest_rectangle"],
                circleable=prof["circleable_groups"],
            )
        )
    Path(out).write_text(PAGE.format(cards="\n".join(cards)))
    print(f"{len(cards)} candidates -> {out}")


def main():
    if sys.argv[1] == "--html":
        page(sys.argv[2], sys.argv[3])
    else:
        render(json.loads(Path(sys.argv[1]).read_text())).save(sys.argv[2])


if __name__ == "__main__":
    main()
