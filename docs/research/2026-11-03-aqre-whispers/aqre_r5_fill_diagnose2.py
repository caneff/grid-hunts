"""SCRATCH: control and second pass for aqre_r5_fill_diagnose.

Control: the known grid-8-r1 layout must fill under the same `status`. Then, per logged
layout: which single houses fail alone, and a minimal failing set with no whispers.
"""

import json
import sys
from pathlib import Path

import aqre_r5_fill_diagnose as base


def layout_of_known(path):
    known = json.loads(Path(path).read_text())
    region = [[0] * 9 for _ in range(9)]
    for k, cells in enumerate(known["regions"]):
        for r, c in cells:
            region[r][c] = k
    return {"region": region, "shaded": known["shaded"], "n": 4}


def single_houses(layout, every):
    region = layout["region"]
    failed = []
    for house in [p for p in every if p[0] in ("row", "col", "region")]:
        cells = set(base.house_cells(house, region))
        chosen = [house]
        for p in every:
            if p[0] == "sign" and p[1] in cells:
                chosen.append(p)
            elif p[0] == "whisper" and p[1] in cells and p[2] in cells:
                chosen.append(p)
            elif p[0] == "given" and p[1] in cells:
                chosen.append(p)
        if base.status(layout, chosen) == "INFEASIBLE":
            failed.append(house)
    return failed


def core_of(layout, chosen):
    core = list(chosen)
    for piece in chosen:
        trial = [p for p in core if p != piece]
        if base.status(layout, trial) == "INFEASIBLE":
            core = trial
    return core


def main(known_path, path, limit):
    base.ROW = 0
    known = layout_of_known(known_path)
    print("control, grid-8-r1 all rules:", base.status(known, base.pieces(known)))
    base.ROW = 4
    layouts = [json.loads(line) for line in Path(path).read_text().splitlines()][:limit]
    for i, layout in enumerate(layouts):
        every = base.pieces(layout)
        print(f"layout {i + 1}: 9 in r5c{layout['n'] + 1}")
        print("  single houses failing alone:", single_houses(layout, every))
        rest = [p for p in every if p[0] != "whisper"]
        print("  no whispers:", base.status(layout, rest))
        print("  failing set with no whispers:", core_of(layout, rest))
        rest = [p for p in every if p[0] not in ("whisper", "given")]
        print("  no whispers, no r5 digits:", base.status(layout, rest))
        print("  failing set:", core_of(layout, rest) if base.status(layout, rest) == "INFEASIBLE" else "none")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], int(sys.argv[3]))
