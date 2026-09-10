"""Second stage of the harvest: ask a refused hit's digits for a shading again.

The joint model returns digits and a shading together, and the shared-label
hole means the shading can be wrong while the digits are not. So a hit refused
by `renbanana_verify` still holds a sudoku the model has *proved* carries both
circled rectangles -- the expensive half of the problem, thrown away with the
cheap half.

This asks the cheap half on its own: fix the digits, and let the inverted
model search shadings with its cut loop, which forbids each illegal shading
and keeps going until one survives every rule or the clock runs out. Over the
53 refused hits on record it settled every one -- 51 proved to admit no legal
shading at all, 2 produced one -- at one to three seconds each, against the
joint model's 85% timeout rate at 120 seconds. It is close to free and it is
decisive, so every hit comes through here, refused or not.
"""

import argparse
import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
from ortools.sat.python import cp_model as cp

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_lineup
import canon
import probe_inverted as pi
import renbanana_cpsat as rc
import renbanana_verify as rv

N = 9


def work(job):
    rows, seconds = job
    grid = np.array([[int(ch) for ch in row] for row in rows])
    began = time.monotonic()
    model = pi.Shadings(grid, want_circled=2)
    status, is_choc = model.solve(seconds, 1, 0)
    out = {
        "grid": rows,
        "seconds": round(time.monotonic() - began, 1),
        "cuts": model.cuts,
    }
    if is_choc is None:
        out["verdict"] = "infeasible" if status == cp.INFEASIBLE else "unknown"
        return out
    out["shading"] = [
        "".join("C" if is_choc[r, c] else "b" for c in range(N)) for r in range(N)
    ]
    digits = {(r, c): int(grid[r, c]) for r in range(N) for c in range(N)}
    bad = rv.check(digits, is_choc)
    out["verdict"] = "LEGAL" if not bad else "illegal"
    out["violations"] = bad[:3]
    return out


def hits_from(paths):
    """Every distinct grid a hit carried, refused or not."""
    seen, out = set(), []
    for path in paths:
        for line in path.read_text().splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            rows = row.get("grid")
            if not rows or tuple(rows) in seen:
                continue
            seen.add(tuple(rows))
            out.append(rows)
    return out


def save(results, pool):
    """Write the legal ones into the pool, skipping any already there."""
    pool.mkdir(parents=True, exist_ok=True)
    keys = set()
    for path in sorted(
        Path(__file__).resolve().parents[1].glob("candidates*/cand_*.json")
    ):
        grid, is_choc, _ = rv.load(path)
        keys.add(canon.key(grid, is_choc))
    n = 1 + max(
        (int(f.stem.split("_")[1]) for f in pool.glob("cand_*.json")), default=-1
    )
    written = 0
    for row in (r for r in results if r["verdict"] == "LEGAL"):
        grid = {(r, c): int(row["grid"][r][c]) for r in range(N) for c in range(N)}
        is_choc = {
            (r, c): row["shading"][r][c] == "C" for r in range(N) for c in range(N)
        }
        bad = rv.check(grid, is_choc)
        if bad:
            print(f"REFUSED on the second look: {bad[0]}", flush=True)
            continue
        key = canon.key(grid, is_choc)
        if key in keys:
            continue
        keys.add(key)
        (pool / f"cand_{n:03d}.json").write_text(
            json.dumps(
                {
                    "objective": "two-circled-rectangles",
                    "value": len(rc.circle_cells(grid, is_choc)),
                    "seed": "recycled-shading-search",
                    "grid": row["grid"],
                    "shading": row["shading"],
                    "circles": rc.circle_cells(grid, is_choc),
                    "profile": rc.profile(grid, is_choc),
                },
                indent=1,
            )
            + "\n"
        )
        print(f"wrote {pool / f'cand_{n:03d}.json'}", flush=True)
        n += 1
        written += 1
    return written


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("proof", type=Path, nargs="+", help="proof.jsonl from a harvest")
    ap.add_argument("--procs", type=int, default=20)
    ap.add_argument("--seconds", type=float, default=240.0)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument(
        "--pool",
        type=Path,
        default=Path("docs/research/renbanana/candidates-two-circles"),
    )
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)

    grids = hits_from(a.proof)
    print(f"{len(grids)} distinct grids from hits; re-solving the shading", flush=True)
    log = a.out / "recycled.jsonl"
    tally, results = {}, []
    with ProcessPoolExecutor(max_workers=a.procs) as pool:
        for row in pool.map(work, [(g, a.seconds) for g in grids], chunksize=1):
            tally[row["verdict"]] = tally.get(row["verdict"], 0) + 1
            results.append(row)
            with log.open("a") as handle:
                handle.write(json.dumps(row) + "\n")
            if row["verdict"] == "LEGAL":
                print("LEGAL: " + " ".join(row["grid"]), flush=True)
    written = save(results, a.pool)
    print(f"{tally}; {written} new grids in {a.pool}", flush=True)
    if written:
        build_lineup.main()


if __name__ == "__main__":
    main()
