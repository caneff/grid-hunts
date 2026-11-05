"""SCRATCH: what the grids that need the fewest extra outside digits have in common.

For each such grid, lists every smallest set of extra clues exactly, then tallies clues,
clue digits and whole sets, and each inner cell's digit across those grids. One worker.

With REQUIRED, such as L4=8 or L4=8,T5=3, only sets holding those clue digits are tallied.

Usage: nr_outside_common.py BOARD_JSON BORDER PINS SIZE [REQUIRED]
"""

import collections
import itertools
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from nr import CLUES, clue_name, outside
from nr_outside_finish import all_grids


def main(path, border, pin_text, size, required=""):
    size = int(size)
    need = dict(item.split("=") for item in required.split(",") if item)
    data = json.loads(Path(path).read_text())
    pins = [(int(p[0]) - 1, int(p[1]) - 1, int(p[2])) for p in pin_text.split(",")]
    grids = all_grids(border, pins)
    rings = [outside(g) for g in grids]
    given = {(k[0], int(k[1:]) - 1) for k in data["outside"]}
    free = [c for c in CLUES if c not in given and len({r[c] for r in rings}) > 1]
    print("clues that can still differ:", len(free), [clue_name(c) for c in free], flush=True)
    bit = {c: 1 << i for i, c in enumerate(free)}
    winners = []
    clue_tally = collections.Counter()
    digit_tally = collections.Counter()
    set_tally = collections.Counter()
    for i, me in enumerate(rings):
        diffs = set()
        fixed = True
        for j, other in enumerate(rings):
            if i == j:
                continue
            mask = sum(bit[c] for c in free if other[c] != me[c])
            if not mask:
                fixed = False
                break
            diffs.add(mask)
        if not fixed:
            continue
        diffs = sorted(diffs, key=lambda m: m.bit_count())
        sets = []
        for combo in itertools.combinations(free, size):
            chosen = sum(bit[c] for c in combo)
            if all(chosen & m for m in diffs):
                sets.append(combo)
        if not sets:
            continue
        if need:
            sets = [
                combo
                for combo in sets
                if all(any(clue_name(c) == k and str(me[c]) == v for c in combo) for k, v in need.items())
            ]
            if not sets:
                continue
        winners.append(i)
        for combo in sets:
            set_tally[" ".join(sorted(clue_name(c) for c in combo))] += 1
            for c in combo:
                clue_tally[clue_name(c)] += 1
                digit_tally[f"{clue_name(c)}={me[c]}"] += 1
    print("grids", len(winners), "smallest sets", sum(set_tally.values()), flush=True)
    print("clues:", clue_tally.most_common(12))
    print("clue digits:", digit_tally.most_common(14))
    print("sets:", set_tally.most_common(8))
    cell = collections.defaultdict(collections.Counter)
    for i in winners:
        for r in range(9):
            for c in range(9):
                cell[r, c][grids[i][r][c]] += 1
    print("most common digit per cell (count of", len(winners), "):")
    for r in range(9):
        print(" ".join(f"{cell[r, c].most_common(1)[0][0]}:{cell[r, c].most_common(1)[0][1]:>3}" for c in range(9)))
    print("rows of the commonest digits:", " ".join("".join(str(cell[r, c].most_common(1)[0][0]) for c in range(9)) for r in range(9)))


if __name__ == "__main__":
    main(*sys.argv[1:])
