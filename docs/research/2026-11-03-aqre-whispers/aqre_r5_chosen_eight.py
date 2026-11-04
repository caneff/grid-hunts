"""SCRATCH: the colour-aware r5 cover with the 8 region fixed to Chris's chosen shape.

Chris, 2026-11-04: the sheet's 3x4 run 4 shape, rows X.X / X.X / XXX / XX. Every placement holds
two r5 cells, the 8 and the 9, two columns apart. Each case is one place of the 9 and one column
parity for the 8, with one placement per symmetry group. The 7 is always forced (Chris ruled out
any 7, 2026-11-04). INFEASIBLE proves that case on these lists. Each layout found goes to the fixed-region solve. It
stops at the first grid. The cover runs on 12 workers, on Chris's ask for more, and the
fixed-region solve on one.
"""

import json
import pickle
import sys
from pathlib import Path

import aqre_r5_oriented as oriented
from aqre_r5_cover import mask_of
from aqre_r5_oriented import canonical, solve_case
from jigsaw_r5_diversity import shape_key

ROW = 4
SHAPE = [(0, 0), (0, 2), (1, 0), (1, 2), (2, 0), (2, 1), (2, 2), (3, 0), (3, 1)]


def main(out):
    oriented.WORKERS = 12
    key = shape_key(SHAPE)
    catalogue = json.loads((out / "eight-regions-r5.json").read_text())
    with (out / "oriented.pickle").open("rb") as f:
        table = pickle.load(f)
    places = {}
    for e in catalogue:
        cells = [tuple(x) for x in e["cells"]]
        if shape_key(cells) != key:
            continue
        c = e["column"]
        mask = mask_of(cells)
        if not canonical(mask, c):
            continue
        n = next(q for r, q in cells if r == ROW and q != c)
        places.setdefault((n, c % 2), set()).add(mask)
    print(f"{sum(len(v) for v in places.values())} placements kept in {len(places)} cases", flush=True)
    tally = {}
    for (n, parity), masks in sorted(places.items()):
        name, layouts, size, spent, done = solve_case(table, n, parity, True, out, tally, eight_only=masks)
        print(f"forced 7, 9 in r5c{n + 1}, 8 on column parity {parity}: {name}, {layouts} layouts, {size} candidates, {len(masks)} placements, {spent:.1f}s; tally {tally}", flush=True)
        if done:
            return


if __name__ == "__main__":
    main(Path(sys.argv[1]))
