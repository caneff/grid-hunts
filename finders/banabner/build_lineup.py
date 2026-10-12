"""Build the Banabner Lineup page from hunt directories (#763).

    uv run finders/banabner/build_lineup.py OUT.html HUNT_DIR [HUNT_DIR ...]

Every line of each directory's `examples.jsonl` (a `banabner` hunt's output,
`{"grid": [...], "shading": [...]}`, optionally with `id` and `run`) becomes one
card. The Renbanana lineup (`finders/renbanana/tools/build_lineup.py`) is a
separate page: a circle means something different under the two rule sets, so
the two share no template and no data.

The record section is `docs/research/banabner/lineup-record.json`, spliced into
the template beside the grids. A grid that fails `banabner_finder.check` stops
the build, and a grid that is another listed grid under the board's 8
symmetries is listed once.

Circles (Chris, 2026-10-09, #761): every cell whose digit equals the size of
its own group is circled, on chocolate and banana groups alike.

* `circles`: such cells in a chocolate group.
* `bcircles`: such cells in a banana group of 3 or 4 cells.
* `forced`: the 5 of a 5-cell banana. That group is exactly {1,3,5,7,9}, so
  the circle is there whatever the shading, and it is drawn dashed.

The circle score is the number of groups carrying a circle, forced ones left
out: a rectangle repeats digits, so several of its cells can equal its size,
and the score counts the rectangle once. This is the Renbanana lineup's rule
(its generator records one circle per group, and counts 5-plus bananas as
forced); the count is the builder's own choice for Banabner, since no hunt
records a score.
"""

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "finders"))
sys.path.insert(0, str(ROOT / "finders" / "hunt"))
import banabner_finder as bf
import renbanana_verify as rv
from dedupe import D4, canonical_key

TEMPLATE = HERE / "lineup_template.html"
RECORD = ROOT / "docs" / "research" / "banabner" / "lineup-record.json"
N = 9
FORCED_SIZE = 5


def houses():
    out = [(f"row {i + 1}", [(i, c) for c in range(N)]) for i in range(N)]
    out += [(f"col {i + 1}", [(r, i) for r in range(N)]) for i in range(N)]
    out += [
        (
            f"box r{br * 3 + 1}c{bc * 3 + 1}",
            [(br * 3 + r, bc * 3 + c) for r in range(3) for c in range(3)],
        )
        for br in range(3)
        for bc in range(3)
    ]
    return out


def shape_of(group):
    rows = {r for r, _ in group}
    cols = {c for _, c in group}
    a, b = sorted((len(rows), len(cols)))
    return f"{a}x{b}"


def row(candidate, run, ident):
    """The page's data for one grid: its groups, circles and stats."""
    grid, is_choc = bf.to_maps(candidate)
    gid = [[-1] * N for _ in range(N)]
    gsize = []
    size_of = {}
    circles, bcircles, forced = [], [], []
    circled_groups = 0
    small_banana = 0
    five_cell = 0
    choc_groups = []
    for colour in (True, False):
        for group in rv.components(is_choc, colour):
            for p in group:
                gid[p[0]][p[1]] = len(gsize)
                size_of[p] = len(group)
            gsize.append(len(group))
            k = len(group)
            hits = [list(p) for p in group if grid[p] == k]
            if colour:
                choc_groups.append(group)
                circles += hits
                circled_groups += bool(hits)
            elif k == FORCED_SIZE:
                forced += hits
                five_cell += 1
            else:
                bcircles += hits
                circled_groups += bool(hits)
                small_banana += bool(hits) * (FORCED_SIZE - k)
    house_n, house_name, house_cells = max(
        (sum(1 for p in cells if grid[p] == size_of[p]), name, cells)
        for name, cells in houses()
    )
    big = [g for g in choc_groups if len(g) > 1]
    big.sort(key=lambda g: (-len(g), shape_of(g)))
    return {
        "id": ident,
        "run": run,
        "grid": list(candidate.grid),
        "shading": list(candidate.shading),
        "circles": circles,
        "bcircles": bcircles,
        "forced": forced,
        "gid": gid,
        "gsize": gsize,
        "value": circled_groups,
        "shapes": [shape_of(g) for g in big],
        "cells": sum(len(g) for g in choc_groups),
        "groups": len(choc_groups),
        "largest": max(len(g) for g in choc_groups),
        "bananaCircles": len(bcircles),
        "smallBanana": small_banana,
        "forcedCircles": len(forced),
        "fiveCell": five_cell,
        "houseCircles": house_n,
        "houseName": house_name,
        "houseCells": [list(p) for p in house_cells],
    }


def rows(hunt_dirs):
    out = []
    seen = {}
    for hunt in map(Path, hunt_dirs):
        lines = (hunt / "examples.jsonl").read_text().splitlines()
        for i, line in enumerate(filter(None, lines)):
            rec = json.loads(line)
            candidate = bf.Candidate(tuple(rec["grid"]), tuple(rec["shading"]))
            ident = rec.get("id", f"{hunt.name}/{i}")
            bad = bf.check(candidate)
            if bad:
                sys.exit(f"{ident} is not a legal Banabner grid: {bad[0]}")
            key = canonical_key(bf.BanabnerFinder.key(candidate), D4)
            if key in seen:
                print(f"  {ident} is {seen[key]} rotated or reflected: one card")
                continue
            seen[key] = ident
            out.append(row(candidate, rec.get("run", hunt.name), ident))
    out.sort(key=lambda d: (-d["value"], d["id"]))
    for i, d in enumerate(out):
        d["i"] = i
    return out


def main(argv):
    if len(argv) < 2:
        sys.exit(__doc__)
    out, hunts = Path(argv[0]), argv[1:]
    data = rows(hunts)
    tpl = TEMPLATE.read_text()
    for marker, value in (
        ("const DATA=[];\n", data),
        ("const LOG=[];\n", json.loads(RECORD.read_text())),
    ):
        assert tpl.count(marker) == 1, f"template must hold exactly one {marker!r}"
        name = marker.split()[1].split("=")[0]
        blob = json.dumps(value, separators=(",", ":"), ensure_ascii=False)
        tpl = tpl.replace(marker, f"const {name}={blob};\n", 1)
    out.write_text(tpl)
    print(f"{len(data)} grids -> {out}")


if __name__ == "__main__":
    main(sys.argv[1:])
