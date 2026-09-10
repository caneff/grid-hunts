"""Choose which grids the next walk round starts from.

The walk climbs the count of circled wanted shapes and refuses to step
downhill, so where it starts caps what it can reach: a round seeded from grids
holding one circled 2x3 is hunting for the second one. Seeds are therefore
ranked by that count first, and among equals the freshest grids win, since a
seed that has already been walked out mostly returns keys the skip-set throws
straight back.

    uv run docs/research/renbanana/tools/pick_seeds.py --want 2x2,2x3 --top 24
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import renbanana_verify as rv


def parse_want(text):
    out = set()
    for bit in text.split(","):
        if bit.strip():
            a, b = (int(x) for x in bit.strip().lower().split("x"))
            out.add(tuple(sorted((a, b))))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--want", default="2x2,2x3")
    ap.add_argument("--top", type=int, default=24)
    ap.add_argument("--min-score", type=int, default=1)
    ap.add_argument(
        "--rank",
        choices=("circled", "small"),
        default="circled",
        help="rank seeds by circled wanted shapes, or by small banana groups",
    )
    ap.add_argument(
        "--small-max",
        type=int,
        default=4,
        help="a banana group this size or under counts as small",
    )
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()

    want = parse_want(a.want)
    rows = []
    for path in sorted(Path("docs/research/renbanana").glob("candidates*/cand_*.json")):
        grid, is_choc, _ = rv.load(path)
        if a.rank == "circled":
            score = sum(
                1
                for g in rv.components(is_choc, True)
                if tuple(sorted(rv.shape(g))) in want
                and any(grid[p] == len(g) for p in g)
            )
        else:
            score = sum(
                1 for g in rv.components(is_choc, False) if len(g) <= a.small_max
            )
        if score >= a.min_score:
            rows.append((score, path.stat().st_mtime, str(path)))
    rows.sort(reverse=True)
    picked = rows[: a.top]
    a.out.write_text("\n".join(p for _, _, p in picked) + "\n")
    best = picked[0][0] if picked else 0
    print(f"{len(picked)} seeds picked from {len(rows)} eligible, best score {best}")
    return 0 if picked else 1


if __name__ == "__main__":
    sys.exit(main())
