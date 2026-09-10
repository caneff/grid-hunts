"""Rebuild lineup.html from the candidate pools: DATA spliced into lineup_template.html.

    uv run python docs/research/renbanana/tools/build_lineup.py

Every `cand_*.json` under a pool directory becomes one card. A pool's name is
the run label on the card, so a new hunt only needs a line in POOLS.

**Looking at the page you just built.** A change here is judged from a picture,
and Orca's own browser renders it — no web server, no headless Chrome. The
commands are top-level, not under an `orca browser` group, which is what makes
them easy to miss in a truncated `--help`:

    orca-ide tab create --url file://wsl.localhost/Ubuntu-24.04/$PWD/lineup.html
    orca-ide tab list --json            # check `loadError` is null
    orca-ide screenshot --format png --json | ...   # base64 in .result.data

Three things that cost half an hour the first time:

* **The URL must be the UNC form.** Orca is the Windows build and WSL is only
  the shell, so `file:///home/caneff/...` returns `ERR_FILE_NOT_FOUND` while
  `file://wsl.localhost/Ubuntu-24.04/home/caneff/...` loads. `tab list --json`
  reports the failure in `loadError`; the tab itself looks fine.
* **`screenshot` shoots the active tab.** Passing `--page <id>` to it answered
  `runtime_unavailable`; `orca-ide tab switch --page <id>` first, then shoot.
* **The page's own controls are off by default**, so a shot of the plain page
  proves nothing about a toggle. Drive them with `orca-ide eval`, which wants
  an *expression* — wrap the statements in an IIFE, and reach the elements
  through `document.getElementById`, since a bare `sort` is not a global:

    orca-ide eval --expression "(()=>{const s=document.getElementById('sort');
      s.value='houseCircles';s.dispatchEvent(new Event('input'));
      const h=document.getElementById('house');h.checked=true;
      h.dispatchEvent(new Event('input'));return s.value})()"

The page is theme-aware and Orca usually runs dark, so check both: the tokens
are defined on bare `:root` and re-defined under `prefers-color-scheme: dark`.
"""

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
POOLS = {
    "candidates": "free",
    "candidates-2x4": "forced 2x4",
    "candidates-multi2": "2+ rectangles",
    "candidates-multi3": "3+ rectangles",
    "candidates-only22": "circled 2x2",
    "candidates-only23": "circled 2x3",
    "candidates-circ2": "circled 2x2 + 2x3",
    "candidates-walk": "walked",
    "candidates-walk2": "walked twice",
    "candidates-circled": "circled climb",
    "candidates-small": "small bananas",
    "candidates-two-circles": "TWO circled rectangles",
    "candidates-house": "fullest house",
    "candidates-circle-pattern": "box-3 circle pattern",
    "candidates-fully-circled": "fully circled pick",
}

sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT.parent))
import canon
import renbanana_verify as rv


def rows():
    out = []
    # One card per *puzzle*, not per file. Two hunts can land on the same grid
    # up to a rotation or a reflection, and the pools keep both because each
    # records what its own hunt found -- but the lineup shows it once.
    seen = {}
    for pool, label in POOLS.items():
        if not (ROOT / pool).is_dir():  # a hunt that has not been run
            continue
        for path in sorted((ROOT / pool).glob("cand_*.json")):
            # A hunt still running writes here; take whatever it has so far.
            d = json.loads(path.read_text())
            is_choc = {
                (r, c): ch == "C"
                for r, row in enumerate(d["shading"])
                for c, ch in enumerate(row)
            }
            # One id per maximal group, chocolate and banana alike, so the page
            # can outline a group and light it up on hover.
            grid = {
                (r, c): int(ch)
                for r, row in enumerate(d["grid"])
                for c, ch in enumerate(row)
            }
            gid = [[-1] * 9 for _ in range(9)]
            gsize = []
            circles = []  # every chocolate cell that could take a circle
            bcircles = []  # on a banana group of size < 5: says something
            bsizes = []  # the size of the group carrying each of those
            bmax = []  # and the top of each of those groups' renban runs
            forced = []  # on a banana group of size >= 5: says nothing, below
            for colour in (True, False):
                for group in rv.components(is_choc, colour):
                    for r, c in group:
                        gid[r][c] = len(gsize)
                    gsize.append(len(group))
                    if colour:
                        # A rectangle repeats digits, so more than one of its
                        # cells can equal its size. The generator records one
                        # per group for scoring; every site is drawn.
                        circles += [
                            [r, c] for r, c in sorted(group) if grid[r, c] == len(group)
                        ]
                        continue
                    # A banana circle is as legal as a chocolate one -- the
                    # verifier checks both -- but the generator never scores
                    # them, so they are recovered here. A banana group is a
                    # renban holding the run [m, m+k-1], so at most one cell
                    # can equal k, and one does exactly when m <= k. The run
                    # must fit in 1..9, so m <= 10-k, and the circle fails only
                    # for m in [k+1, 10-k] -- empty once k >= 5. Every banana
                    # group of five cells or more therefore carries a circle
                    # whatever its digits, so that circle rules out no shading
                    # and is tracked apart from the ones that do.
                    k = len(group)
                    for r, c in sorted(group):
                        if grid[r, c] == k:
                            if k >= 5:
                                forced.append([r, c])
                            else:
                                bcircles.append([r, c])
                                bsizes.append(k)
                                bmax.append(max(grid[q] for q in group))
                            break
            # The most circles any one row, column or box carries. Every
            # circle counts here, chocolate and banana and forced alike: the
            # question is how many can share a house, not how much each says.
            size_of = {}
            for colour in (True, False):
                for group in rv.components(is_choc, colour):
                    for p in group:
                        size_of[p] = len(group)
            houses = [(f"row {i + 1}", [(i, c) for c in range(9)]) for i in range(9)]
            houses += [(f"col {i + 1}", [(r, i) for r in range(9)]) for i in range(9)]
            houses += [
                (
                    f"box r{br * 3 + 1}c{bc * 3 + 1}",
                    [(br * 3 + r, bc * 3 + c) for r in range(3) for c in range(3)],
                )
                for br in range(3)
                for bc in range(3)
            ]
            house_n, house_name, house_cells = max(
                (sum(1 for p in cells if grid[p] == size_of[p]), name, cells)
                for name, cells in houses
            )

            k = canon.key_from_rows(d["grid"], d["shading"])
            if k in seen:
                print(f"  {pool}/{path.stem} is {seen[k]} rotated — one card")
                continue
            seen[k] = f"{pool}/{path.stem}"
            prof = d["profile"]
            out.append(
                {
                    "i": len(out),
                    "id": f"{pool}/{path.stem}",
                    "run": label,
                    "seed": d["seed"],
                    "value": d["value"],
                    "grid": d["grid"],
                    "shading": d["shading"],
                    "circles": circles,
                    "bcircles": bcircles,
                    "forced": forced,
                    "gid": gid,
                    "gsize": gsize,
                    "shapes": prof["shapes"],
                    "cells": prof["chocolate_cells"],
                    "groups": prof["chocolate_groups"],
                    "largest": prof["largest_rectangle"],
                    "circleable": prof["circleable_groups"],
                    "bananaCircles": len(bcircles),
                    # How small the groups carrying those circles are, not
                    # just how many there are. Rule 4 puts a floor at three: a
                    # lone banana cell is a 1x1 and a banana domino a 1x2, both
                    # rectangles, so the smallest banana group is a three-cell
                    # L. With sizes 5 and up forced, a scoreable circle sits on
                    # a group of 3 or 4 and nothing else, and 5 - k scores it 2
                    # or 1. The circle on the L is the sharper clue: it pins
                    # the run to one of {1,2,3}, {2,3,4}, {3,4,5}.
                    "smallBanana": sum(5 - k for k in bsizes),
                    # The lowest run-top among this grid's scoreable banana
                    # circles. The circle says its group's run holds k, so the
                    # top lands in 3..5 for a three-cell L and 4..7 for a group
                    # of four, and the lowest one is the sharpest clue the grid
                    # offers: a group running 1-2-3 tops out at 3 and pins all
                    # three digits, where one running 2-3-4-5 tops at 5. A grid
                    # holding both scores 3, by its best clue and not its
                    # worst. Forced circles are left out -- a group of five or
                    # more always carries one and its run reaches 9 -- and a
                    # grid with no scoreable banana circle scores 0, which the
                    # page sorts last rather than first.
                    "minBananaTop": min(bmax, default=0),
                    "forcedCircles": len(forced),
                    "houseCircles": house_n,
                    "houseName": house_name,
                    "houseCells": [list(p) for p in house_cells],
                }
            )
    return out


def main():
    data = rows()
    tpl = (HERE / "lineup_template.html").read_text()
    marker = "const DATA=[];\n"
    assert tpl.count(marker) == 1, "template must hold exactly one DATA line"
    blob = json.dumps(data, separators=(",", ":"), ensure_ascii=False)
    (ROOT / "lineup.html").write_text(tpl.replace(marker, f"const DATA={blob};\n", 1))
    print(f"{len(data)} grids -> {ROOT / 'lineup.html'}")


if __name__ == "__main__":
    main()
