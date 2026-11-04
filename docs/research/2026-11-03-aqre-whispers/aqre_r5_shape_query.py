"""SCRATCH: every r5 placement of the sheet's 3x4 run 4 shape that can be the circled 8.

The shape is taken from the sheet: its rows read X.X / X.X / XXX / XX. For each placement in
the catalogue: how many r5 cells it holds, where the 8 and the 9 sit, and how many shadings work.
"""

import json
import sys
from collections import Counter
from pathlib import Path

from aqre_r5_eight_regions import ROW
from aqre_r5_seven_unshaded import lines_of
from aqre_jigsaw_feasible import neighbours
from itertools import permutations
from jigsaw_r5_diversity import shape_key

SHAPE = [(0, 0), (0, 2), (1, 0), (1, 2), (2, 0), (2, 1), (2, 2), (3, 0), (3, 1)]


def fills(cells, root, nine):
    """All (hole, digits) for this placement with the 8 on root and any 9 on `nine`."""
    high = sum(root) % 2
    found = []
    for hole in cells:
        if hole in (root, nine):
            continue
        shaded = cells - {hole}
        highs = [x for x in shaded if sum(x) % 2 == high]
        lows = [x for x in shaded if sum(x) % 2 != high]
        if len(highs) != 4 or len(lows) != 4:
            continue
        if any(len({x in shaded for x in line}) == 1 for line in lines_of(cells)):
            continue
        edges = [(a, b) for a in lows for b in neighbours(a) if b in shaded]
        others = [x for x in highs if x != root]
        for low_digits in permutations((1, 2, 3, 4)):
            place = dict(zip(lows, low_digits))
            for high_digits in permutations((6, 7, 9)):
                place.update(zip(others, high_digits))
                place[root] = 8
                if nine and place[nine] != 9:
                    continue
                if all(place[b] - place[a] >= 5 for a, b in edges):
                    found.append((hole, dict(place)))
    return found


def main(out):
    key = shape_key(SHAPE)
    catalogue = json.loads((out / "eight-regions-r5.json").read_text())
    entries = [e for e in catalogue if shape_key([tuple(x) for x in e["cells"]]) == key]
    print(f"{len(entries)} placements with the circle in r5c1-5", flush=True)
    r5_cells = Counter(sum(x[0] == ROW for x in e["cells"]) for e in entries)
    print("placements by r5 cells held:", sorted(r5_cells.items()), flush=True)
    shown = 0
    for e in entries:
        cells = {tuple(x) for x in e["cells"]}
        root = (ROW, e["column"])
        second = [x for x in cells if x[0] == ROW and x != root]
        found = fills(cells, root, second[0] if second else None)
        holes = Counter(hole for hole, _ in found)
        if second and shown < 12:
            shown += 1
            rows = sorted({r for r, _ in cells})
            cols = sorted({c for _, c in cells})
            print(f"8 in r5c{root[1] + 1}, 9 in r5c{second[0][1] + 1}: {len(found)} fillings, {len(holes)} places for the 5", flush=True)
            for r in rows:
                print("   ", "".join(("8" if (r, c) == root else "9" if (r, c) == second[0] else "#") if (r, c) in cells else "." for c in cols), flush=True)
    both = [e for e in entries if sum(x[0] == ROW for x in e["cells"]) == 2]
    gaps = Counter(abs(next(x[1] for x in e["cells"] if x[0] == ROW and x[1] != e["column"]) - e["column"]) for e in both)
    print("distance between the 8 and the 9 on r5:", sorted(gaps.items()), flush=True)


if __name__ == "__main__":
    main(Path(sys.argv[1]))
