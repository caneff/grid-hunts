"""Turn the walk's accepted steps into a candidate pool.

The walk writes one JSONL row per shadeable grid it steps onto. This selects
the ones worth keeping and writes them in the candidate format the rest of the
tooling reads -- `renbanana_verify.load`, `build_lineup.py`, the lineup page.

Selection is the hunt's own diversity rule, seeded with the existing pool so a
walk result never duplicates a grid we already had: keep a grid when its
shading is at least 12 cells from every grid already held, or its multiset of
chocolate rectangle shapes differs. Every kept grid is re-checked from the
rules before it is written; nothing enters a pool unverified.

    uv run docs/research/renbanana/tools/walk_to_candidates.py \
        --walk docs/research/renbanana/walk \
        --out docs/research/renbanana/candidates-walk
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import build_lineup
import canon
import renbanana_cpsat as rc
import renbanana_verify as rv

MIN_DISTANCE = 12


def hamming(a, b):
    return sum(
        x != y for ra, rb in zip(a, b, strict=True) for x, y in zip(ra, rb, strict=True)
    )


def shapes_of(is_choc):
    return sorted("x".join(map(str, rv.shape(g))) for g in rv.components(is_choc, True))


def as_rows(mapping, true_char, false_char=None):
    if false_char is None:
        return ["".join(str(mapping[r, c]) for c in range(9)) for r in range(9)]
    return [
        "".join(true_char if mapping[r, c] else false_char for c in range(9))
        for r in range(9)
    ]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--walk", type=Path, default=Path("docs/research/renbanana/walk"))
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument(
        "--rebuild",
        action="store_true",
        help="build the pool from scratch instead of adding to what it holds",
    )
    a = ap.parse_args()

    pool = []
    keys = set()
    for path in sorted(Path("docs/research/renbanana").glob("candidates*/cand_*.json")):
        if a.rebuild and path.parent == a.out:
            continue
        grid, is_choc, _ = rv.load(path)
        pool.append(
            {"shading": as_rows(is_choc, "C", "b"), "shapes": shapes_of(is_choc)}
        )
        keys.add(canon.key(grid, is_choc))
    held = len(pool)

    rows = [
        json.loads(line)
        for path in sorted(a.walk.glob("*.jsonl"))
        for line in path.read_text().splitlines()
        if line.strip()
    ]

    a.out.mkdir(parents=True, exist_ok=True)
    # Round after round adds to the same pool, so new files carry on from the
    # highest number already there rather than overwriting it.
    start = 1 + max(
        (int(f.stem.split("_")[1]) for f in a.out.glob("cand_*.json")), default=-1
    )
    kept = rejected = illegal = same = 0
    for row in rows:
        k = canon.key_from_rows(row["grid"], row["shading"])
        if k in keys:
            same += 1
            continue
        if not all(
            hamming(row["shading"], other["shading"]) >= MIN_DISTANCE
            or row["shapes"] != other["shapes"]
            for other in pool
        ):
            rejected += 1
            continue
        grid = {(r, c): int(row["grid"][r][c]) for r in range(9) for c in range(9)}
        is_choc = {
            (r, c): row["shading"][r][c] == "C" for r in range(9) for c in range(9)
        }
        bad = rv.check(grid, is_choc)
        if bad:
            illegal += 1
            print(f"REFUSED an illegal grid from {row['source']}: {bad[0]}")
            continue
        keys.add(k)
        pool.append(row)
        (a.out / f"cand_{start + kept:03d}.json").write_text(
            json.dumps(
                {
                    # The card format the lineup reads, built by the generator's
                    # own profile and circle helpers rather than a second copy
                    # of them.
                    "objective": "walk",
                    "value": len(rc.circle_cells(grid, is_choc)),
                    "seed": f"{Path(row['source']).parent.name}/"
                    f"{Path(row['source']).stem}+{row['step']}",
                    "grid": row["grid"],
                    "shading": row["shading"],
                    "circles": rc.circle_cells(grid, is_choc),
                    "profile": rc.profile(grid, is_choc),
                },
                indent=1,
            )
            + "\n"
        )
        kept += 1

    (a.out / "stats.json").write_text(
        json.dumps(
            {
                "kept": kept,
                "same_puzzle_up_to_symmetry": same,
                "rejected_as_too_close": rejected,
                "refused_illegal": illegal,
                "walk_rows": len(rows),
                "pool_held_before": held,
            },
            indent=1,
        )
        + "\n"
    )
    # The lineup is how the pool gets looked at, so it is rebuilt here rather
    # than left for someone to remember: every round that adds a grid also
    # refreshes the page.
    build_lineup.main()
    print(
        f"kept {kept} of {len(rows)} walk rows ({same} the same puzzle, "
        f"{rejected} too close, {illegal} illegal) into {a.out}"
    )


if __name__ == "__main__":
    main()
