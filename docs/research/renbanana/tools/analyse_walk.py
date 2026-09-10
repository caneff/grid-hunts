"""Is the walk's output diverse, or is it the parent grid in a new coat?

The walk is only worth its ~25x cost saving if the grids it finds are new. It
is judged by the same rule the shading-first hunt uses to accept a candidate
into a pool: a grid is new if its shading is at least 12 cells different from
every grid already held, OR its multiset of chocolate rectangle shapes differs.
Either-or, because requiring both over-filters and starves the pool.

    uv run docs/research/renbanana/tools/analyse_walk.py docs/research/renbanana/walk

No solver, no cores.
"""

import json
import statistics as st
import sys
from pathlib import Path

MIN_DISTANCE = 12


def hamming(a, b):
    return sum(
        x != y for ra, rb in zip(a, b, strict=True) for x, y in zip(ra, rb, strict=True)
    )


def novel(row, pool):
    """The hunt's own diversity rule, applied to an accepted pool."""
    return all(
        hamming(row["shading"], other["shading"]) >= MIN_DISTANCE
        or row["shapes"] != other["shapes"]
        for other in pool
    )


def main():
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "docs/research/renbanana/walk")
    rows = [
        json.loads(line)
        for path in sorted(root.glob("*.jsonl"))
        for line in path.read_text().splitlines()
        if line.strip()
    ]
    if not rows:
        print("no walk output yet")
        return

    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    import renbanana_verify as rv

    parents = {}
    for row in rows:
        p = row["source"]
        if p not in parents:
            _, is_choc, _ = rv.load(p)
            parents[p] = {
                "shading": [
                    "".join("C" if is_choc[r, c] else "b" for c in range(9))
                    for r in range(9)
                ],
                "shapes": sorted(
                    "x".join(map(str, rv.shape(g)))
                    for g in rv.components(is_choc, True)
                ),
            }

    same_shape_as_parent = sum(
        r["shapes"] == parents[r["source"]]["shapes"] for r in rows
    )
    shading_moves = [r["shading_distance_from_origin"] for r in rows]
    grid_moves = [r["grid_distance_from_origin"] for r in rows]

    pool = list(parents.values())
    accepted = []
    for row in rows:
        if novel(row, pool):
            pool.append(row)
            accepted.append(row)

    print(
        f"walk produced           {len(rows)} shadeable grids from {len(parents)} seeds"
    )
    print(f"tries per accepted step median {st.median(r['tries'] for r in rows):.0f}")
    print()
    print(f"grid cells moved        median {st.median(grid_moves):.0f} of 81")
    print(f"shading cells moved     median {st.median(shading_moves):.0f} of 81")
    print(f"same shape multiset as its parent  {same_shape_as_parent}/{len(rows)}")
    print()
    print(
        f"NEW by the hunt's own rule (shading >= {MIN_DISTANCE} apart OR different "
        f"shapes): {len(accepted)}/{len(rows)}"
    )
    if accepted:
        print(
            f"  their shading distance from parent: median "
            f"{st.median(r['shading_distance_from_origin'] for r in accepted):.0f}"
        )


if __name__ == "__main__":
    main()
