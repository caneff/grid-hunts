"""SCRATCH: how far apart can the 8 and 9 be on the row, when both are in the 8 region? 8 processes.

For each row r1-r5 and 8 in columns 1-5, every region with exactly two row cells, not straight, is tested for
holding the circled 8 with the 9 on its other row cell. Prints placements and free shapes by the distance.
Regions with the 9 anywhere on the row are included, since the 9's column may be right of column 5.
"""

import multiprocessing
from collections import Counter, defaultdict

import aqre_r5_eight_regions as eight_regions
from aqre_r5_eight_sheet import has_hole
from jigsaw_r5_diversity import shape_key

FORK = multiprocessing.get_context("fork")


def one_root(args):
    row, c = args
    eight_regions.ROW = row
    tried = Counter()
    found = []
    for cells in eight_regions.grow((row, c)):
        on_row = [q for r, q in cells if r == row]
        if len(on_row) != 2 or eight_regions.straight(cells):
            continue
        gap = abs(on_row[0] - on_row[1])
        tried[gap] += 1
        got = eight_regions.holds_eight(cells, (row, c))
        if got:
            found.append((gap, sorted(cells), got))
    return row, tried, found


def main():
    tried = Counter()
    placements = defaultdict(Counter)
    shapes = defaultdict(set)
    example = {}
    with FORK.Pool(8) as pool:
        for row, t, found in pool.imap_unordered(one_root, [(r, q) for r in range(5) for q in range(5)]):
            tried.update(t)
            for gap, cells, got in found:
                placements[gap][row] += 1
                if not has_hole(cells):
                    shapes[gap].add(shape_key(cells))
                example.setdefault(gap, (row, cells, got))
    print("regions with two row cells tried, by distance:", sorted(tried.items()), flush=True)
    for gap in sorted(placements):
        print(f"distance {gap}: placements on r1-r5 {[placements[gap][r] for r in range(5)]}, {len(shapes[gap])} free shapes not holed", flush=True)
        row, cells, (hole, place) = example[gap]
        rows, cols = sorted({r for r, _ in cells}), sorted({c for _, c in cells})
        for r in range(rows[0], rows[-1] + 1):
            print("   ", "".join((str(place[r, c]) if (r, c) in place else "5" if (r, c) == tuple(hole) else ".") for c in range(cols[0], cols[-1] + 1)), "<- row" if r == row else "", flush=True)
    print("distances with none:", [g for g in sorted(tried) if g not in placements], flush=True)


if __name__ == "__main__":
    main()
