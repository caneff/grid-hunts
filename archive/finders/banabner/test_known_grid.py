"""The pinned Banabner grid is accepted by the model and the checker, and a
broken copy is rejected by both (#761).

    uv run finders/banabner/test_known_grid.py

The model accepts a grid when, with every variable pinned to it, it is
FEASIBLE. The model's lex-leader keeps one copy of each grid under the board's
8 symmetries, so it is the known grid's leading copy that must be accepted,
and every other distinct copy rejected. Broken copies, made from the leader:
one digit changed (the ticket's own), which breaks sudoku as well as a
Banabner rule; and two digit swaps that keep sudoku, each breaking only one
Banabner rule. The 5/7 swap witnesses the model's gap. The 8/9 swap puts an 8
in a 5-cell banana, which the speedups' odd-digit fact rejects before the
nabner table is asked, so the table is witnessed on the model without
speedups.

A rejection is INFEASIBLE: a solve that ran out of time proves nothing and
fails the check.
"""

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parent / "hunt"))
import banabner_finder as bf
import banabner_model as bm
import renbanana_verify as rv
from dedupe import d4_cell_maps
from ortools.sat.python import cp_model as cp

KNOWN = json.loads((HERE / "known_grid.json").read_text())
# A second legal grid, accepted only: a 3x3 chocolate holding a 5.
SECOND = json.loads((HERE / "known_grid_3x3.json").read_text())
FAIL = []


def check(name, ok, detail=""):
    print(f"{'ok  ' if ok else 'FAIL'}  {name}{'  ' + detail if detail else ''}")
    if not ok:
        FAIL.append(name)


def model_status(candidate, speedups=True):
    model = bm.Model(speedups=speedups)
    model.pin(*bf.to_maps(candidate))
    status, _, _ = model.solve(30, 1)
    return status


def model_accepts(candidate):
    return model_status(candidate) in (cp.OPTIMAL, cp.FEASIBLE)


def model_rejects(candidate, speedups=True):
    return model_status(candidate, speedups) == cp.INFEASIBLE


def with_digit(candidate, r, c, digit):
    rows = list(candidate.grid)
    rows[r] = rows[r][:c] + str(digit) + rows[r][c + 1 :]
    return bf.Candidate(tuple(rows), candidate.shading)


def swapped(candidate, a, b):
    table = str.maketrans({str(a): str(b), str(b): str(a)})
    return bf.Candidate(
        tuple(row.translate(table) for row in candidate.grid), candidate.shading
    )


def main():
    # 4 L-trominoes, 16 non-rectangular tetrominoes, 61 non-I pentominoes.
    sizes = [len(s) for s in bm.BANANA_SHAPES]
    check(
        "the banana shapes are the fixed non-rectangular 3-5 polyominoes",
        [sizes.count(k) for k in (3, 4, 5)] == [4, 16, 61],
    )
    check(
        "the nabner tables hold 35 3-sets, 15 4-sets and {1,3,5,7,9}",
        [len(bm.NABNER_SETS[k]) for k in (3, 4, 5)] == [35, 15, 1]
        and bm.NABNER_SETS[5] == [(1, 3, 5, 7, 9)],
    )
    pinned = bf.Candidate(tuple(KNOWN["grid"]), tuple(KNOWN["shading"]))
    known = bf.leader(pinned)
    check("the checker accepts the known grid", bf.check(pinned) == [])
    check("the model accepts the known grid's leading copy", model_accepts(known))
    second = bf.Candidate(tuple(SECOND["grid"]), tuple(SECOND["shading"]))
    check("the checker accepts the 3x3 grid", bf.check(second) == [])
    check(
        "the model accepts the 3x3 grid's leading copy",
        model_accepts(bf.leader(second)),
    )
    others = {
        bf.from_key(tuple(bf.BanabnerFinder.key(known)[i] for i in image))
        for image in d4_cell_maps(9)
    } - {known}
    check(
        "the model rejects the 7 other copies",
        len(others) == 7 and all(model_rejects(c) for c in others),
        f"{len(others)} distinct",
    )

    # Give a banana cell a digit consecutive with another of its group's.
    grid, is_choc = bf.to_maps(known)
    (r, c), q = rv.components(is_choc, False)[0][:2]
    one = with_digit(known, r, c, grid[q] + 1 if grid[q] < 9 else 8)
    bad = bf.check(one)
    check(
        "the checker rejects the one-digit copy on rule 6",
        any(line.startswith("rule 6") for line in bad),
        bad[0] if bad else "accepted",
    )
    check("the model rejects the one-digit copy", model_rejects(one))

    # Two swaps keep sudoku and break one Banabner rule each: 5 and 7 only the
    # Dutch Chocolate gap, 8 and 9 only nabner.
    for (a, b), rule in (((5, 7), "rule 5"), ((8, 9), "rule 6")):
        copy = swapped(known, a, b)
        rules = {line.split(":")[0] for line in bf.check(copy)}
        check(f"the checker rejects the {a}/{b} swap on {rule} only", rules == {rule})
        check(f"the model rejects the {a}/{b} swap", model_rejects(copy))
    check(
        "the nabner table alone rejects the 8/9 swap",
        model_rejects(swapped(known, 8, 9), speedups=False),
    )

    print(f"\n{len(FAIL)} failing" if FAIL else "\nall checks pass")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
