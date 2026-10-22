"""`hunt.py links DIR` (#71): one SudokuMaker link per verified hit, in
Chris's layout (#66 § Links), each decoded and checked against its record:

- `DIR/links/<seed>.txt` for each hit's seed, and no other file.
- A `"custom"` canvas, `minDigit` 0 and `maxDigit` n.
- The grid's boxes are regions, and so is each cell of the box notespace,
  which the drawing borders cell by cell. The row and column notespaces,
  which it only shades, and every other cell are in no region (-1).
- Every rank clue, the board's and the added ones, is cosmetic text at the
  centre of the cell just past its line's end, outside the grid.
- The solution is entered, notespaces' missing digits included, and no cell
  is a given; every other cell is empty.
- No constraint but the givens (type 0), the regions (1) and the text
  (2002), and no answer check.

`fixtures/links_9x9/` is the logs of a 9x9 hunt from Chris's opening with
one verified hit, an input to this test only. The layout cells are written
out here from Chris's drawing
(`docs/research/2026-10-22-doppelganger-rank-opening.png`) at 9x9, and at
4x4 as the same drawing shrunk, not taken from `links.py`.

    uv run finders/doppelganger_rank/test_links.py
"""

import json
import shutil
import sys
import tempfile
from pathlib import Path

from sudoku_kit.link_codec import decode_puzzle, read_link

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "hunt"))

# isort: split
from cli_checks import read_jsonl, run_cli

SCRIPT = HERE / "hunt.py"

# Rows and columns from 1 on the canvas: its side, the row notespace's cells
# (row k's missing digit at the k-th), the column notespace's, and the box
# notespace's, boxes numbered across, then down.
LAYOUT = {
    4: {
        "side": 8,
        "rows": [(r, 7) for r in range(1, 5)],
        "cols": [(7, c) for c in range(1, 5)],
        "boxes": [(7, 7), (7, 8), (8, 7), (8, 8)],
    },
    9: {
        "side": 13,
        "rows": [(r, 12) for r in range(1, 10)],
        "cols": [(12, c) for c in range(1, 10)],
        "boxes": [(r, c) for r in range(11, 14) for c in range(11, 14)],
    },
}


def text_at(place, n):
    """The (x, y) of a clue's text: the centre of the cell past its end."""
    line, end = place
    k = int(line[1:]) - 0.5
    return {
        "top": (k, -0.5),
        "bottom": (k, n + 0.5),
        "left": (-0.5, k),
        "right": (n + 0.5, k),
    }[end]


def check(doc, record):
    n, (bh, bw) = record["size"], record["box"]
    grid = [list(map(int, row)) for row in record["solution"]]
    layout = LAYOUT[n]
    side = layout["side"]
    p = doc["puzzle"]
    assert (p["type"], p["width"], p["height"]) == ("custom", side, side), p
    assert (p["minDigit"], p["maxDigit"]) == (0, n), p
    assert "solution" not in p, "the link carries an answer check"
    kinds = sorted(c["type"] for c in p["constraints"])
    assert kinds == [0, 1, 2002], kinds

    def at(r, c):
        return (r - 1) * side + (c - 1)

    digits = set(range(1, n + 1))
    want_value, want_region = {}, {}
    for r in range(n):
        for c in range(n):
            want_value[at(r + 1, c + 1)] = grid[r][c]
            want_region[at(r + 1, c + 1)] = (r // bh) * (n // bw) + c // bw
    boxes = [
        [grid[br + i][bc + j] for i in range(bh) for j in range(bw)]
        for br in range(0, n, bh)
        for bc in range(0, n, bw)
    ]
    units = {
        "rows": grid,
        "cols": [list(col) for col in zip(*grid, strict=True)],
        "boxes": boxes,
    }
    for name in ("rows", "cols", "boxes"):
        for cell, unit in zip(layout[name], units[name], strict=True):
            (missing,) = digits - set(unit)
            want_value[at(*cell)] = missing
    for k, cell in enumerate(layout["boxes"]):
        want_region[at(*cell)] = n + k

    cells = p["cells"]
    assert len(cells) == side * side, len(cells)
    assert not any(cell.get("given") for cell in cells), "a cell is a given"
    for i, cell in enumerate(cells):
        if i in want_value:
            assert cell == {"value": want_value[i]}, (i, cell, want_value[i])
        else:
            assert cell == {}, (i, cell)

    (regions,) = [c["regions"] for c in p["constraints"] if c["type"] == 1]
    assert regions == [want_region.get(i, -1) for i in range(side * side)], regions

    (text,) = [c for c in p["constraints"] if c["type"] == 2002]
    shown = set()
    for x, y, *i in text["symbols"]:
        param = text["params"][i[0] if i else 0]
        assert param["type"] == "text", param
        shown.add((x, y, param["text"]))
    want = {
        (*text_at((c["line"], c["end"]), n), str(c["rank"])) for c in record["clues"]
    }
    assert shown == want, (shown, want)


def links_of(out):
    """Each hit's seed and record, and its decoded link: `links DIR` run on
    `out`, every file under `out/links` read."""
    result = run_cli(SCRIPT, "links", out)
    assert result.returncode == 0, result.stderr
    seeds = [
        e["seed"]
        for e in read_jsonl(out / "progress.jsonl")
        if e["outcome"] == "example"
    ]
    records = read_jsonl(out / "examples.jsonl")
    files = sorted((out / "links").iterdir())
    assert [f.name for f in files] == sorted(f"{s}.txt" for s in seeds), files
    assert result.stdout.strip() == f"wrote {len(seeds)} links to {out / 'links'}"
    return [
        (seed, record, decode_puzzle(read_link(out / "links" / f"{seed}.txt")))
        for seed, record in zip(seeds, records, strict=True)
    ]


with tempfile.TemporaryDirectory() as tmp:
    tmp = Path(tmp)
    empty = tmp / "empty_4x4.json"
    empty.write_text(json.dumps({"size": 4, "box": [2, 2], "clues": [], "marks": []}))
    out = tmp / "hits"
    result = run_cli(SCRIPT, "--board", empty, "--out", out, "--seeds", "0:4")
    assert result.returncode == 0, result.stderr
    found = links_of(out)
    assert len(found) == 4, found
    for _seed, record, doc in found:
        check(doc, record)

    # Chris's 9x9 layout, on the hit of a 9x9 hunt from his opening (seed 1
    # of two, 14 added clues, run 2026-10-22); `links` writes into the
    # directory, so it reads a copy.
    nine = tmp / "links_9x9"
    shutil.copytree(HERE / "fixtures" / "links_9x9", nine)
    ((seed, record, doc),) = links_of(nine)
    assert seed == 1 and len(record["clues"]) == 18, record
    check(doc, record)

print("ok")
