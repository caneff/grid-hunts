"""Regression: the inverted model must never hand back an illegal shading.

It did once.

A walk printed `rule 6: banana group at (0, 8) is not consecutive:
[1, 8, 7, 6, 5, 9]` three times on one seed, meaning the inverted model handed
back a shading its own renban encoding should have forbidden. The cause was label sharing: a label is only pinned to be at most the least
cell index in its component, so two disjoint components could pick the same
one, and renban then landed on their union -- a gap in one component plugged by
a digit from the other. `Shadings.offenders` now cuts a non-renban banana group
the same way it cuts a rectangular one, so the solve loop returns only a
shading that survives every rule.

This hammers the exact case that failed: neighbours of that seed, full model,
every returned shading checked from the rules.

    uv run --with ortools docs/research/renbanana/tools/repro_renban_bug.py

One worker.
"""

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import renbanana_verify as rv
from probe_inverted import Shadings
from probe_neighbourhood import perturb

SOURCE = "docs/research/renbanana/candidates-multi2/cand_02.json"


def main():
    grid, _, _ = rv.load(SOURCE)
    rng = random.Random(0)
    found = illegal = 0
    for t in range(1, 61):
        cand = perturb(grid, rng)
        model = Shadings(cand)
        _, is_choc = model.solve(20.0, 1, t)
        if is_choc is None:
            print(f"try {t}: no shading", flush=True)
            continue
        found += 1
        bad = rv.check(cand, is_choc)
        if bad:
            illegal += 1
            print(f"try {t}: ILLEGAL — {bad[0]}", flush=True)
            print(
                "  grid    "
                + " ".join(
                    "".join(str(cand[r, c]) for c in range(9)) for r in range(9)
                ),
                flush=True,
            )
            print(
                "  shading "
                + " ".join(
                    "".join("C" if is_choc[r, c] else "b" for c in range(9))
                    for r in range(9)
                ),
                flush=True,
            )
        else:
            print(f"try {t}: legal", flush=True)
    print(f"DONE {found} shadings found, {illegal} illegal", flush=True)
    print("PASS" if illegal == 0 else "FAIL", flush=True)
    sys.exit(0 if illegal == 0 else 1)


if __name__ == "__main__":
    main()
