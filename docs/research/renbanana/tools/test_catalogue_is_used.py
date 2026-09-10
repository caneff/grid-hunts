"""The #377 catalogue is not optional: every chocolate question the generator
asks must be answered from it rather than re-searched.

    uv run --with ortools python docs/research/renbanana/tools/test_catalogue_is_used.py

Five call sites, one check each, plus the soundness check that licenses them:
the catalogue is layer B (the rectangle and the boxes, nothing outside), so a
real grid can only narrow its answers, never contradict them.
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parent))

import renbanana_cpsat as R
import renbanana_verify as rv

FAIL = []


def check(name, ok, detail=""):
    print(f"{'ok  ' if ok else 'FAIL'}  {name}{'  ' + detail if detail else ''}")
    if not ok:
        FAIL.append(name)


def main():
    src = (ROOT.parent / "renbanana_cpsat.py").read_text()

    check(
        "SHAPES drops shapes no grid can hold",
        len(R.SHAPES) == 34,
        f"{len(R.SHAPES)} of 64",
    )
    check(
        "stage 1 forbids catalogue-dead placements",
        "_forbid_dead_placements" in src and "self._forbid_dead_placements()" in src,
    )
    check(
        "stage 1 places circled shapes only where a circle is possible",
        "circleable=True" in src,
    )
    check(
        "stage 3 takes cell domains from the catalogue",
        "support_at(" in src and "add_allowed_assignments" in src,
    )
    check(
        "stage 3 scores circles only on catalogue circle cells",
        src.count("circle_cells_at(") >= 3,
        f"{src.count('circle_cells_at(')} call sites",
    )
    check(
        "the whisper is stated as the checkerboard it forces",
        "high[p] != high[q]" in src,
    )

    # Soundness: nothing the catalogue rules out appears in a grid we accepted.
    cells = dead = circles = unpredicted = 0
    for f in sorted(ROOT.glob("candidates*/cand_*.json")):
        d = json.loads(f.read_text())
        is_choc = {
            (r, c): ch == "C"
            for r, row in enumerate(d["shading"])
            for c, ch in enumerate(row)
        }
        grid = {
            (r, c): int(ch)
            for r, row in enumerate(d["grid"])
            for c, ch in enumerate(row)
        }
        for g in rv.components(is_choc, True):
            rows, cols = rv.shape(g)
            r0, c0 = min(g)
            if not R.fillings_at(rows, cols, r0 % 3, c0 % 3):
                dead += 1
            sup = R.support_at(rows, cols, r0 % 3, c0 % 3)
            allowed = {
                (r0 + dr, c0 + dc)
                for dr, dc in R.circle_cells_at(rows, cols, r0 % 3, c0 % 3)
            }
            for i in range(rows):
                for j in range(cols):
                    p = (r0 + i, c0 + j)
                    cells += 1
                    if sup is not None and grid[p] not in sup[i][j]:
                        unpredicted += 1
                    if grid[p] == len(g):
                        circles += 1
                        if p not in allowed:
                            unpredicted += 1
    check(
        "no accepted grid holds a placement the catalogue calls dead",
        dead == 0,
        f"{cells} rectangle cells, {circles} circles",
    )
    check("no accepted digit or circle falls outside the catalogue", unpredicted == 0)

    print(f"\n{len(FAIL)} failing" if FAIL else "\nall checks pass")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
