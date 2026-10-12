"""The Banabner model reads the difference-4 rectangle catalogue at both call
sites (#761), as `finders/renbanana/tools/test_catalogue_is_used.py` checks
for Renbanana.

    uv run finders/banabner/test_catalogue_is_used.py

Each check pins the known grid's leading copy (the one the lex-leader keeps)
and poisons one half of the catalogue: a call
site that reads it turns the pinned grid INFEASIBLE, one that dropped it
leaves the grid FEASIBLE and fails the check. The known grid's one 2x2 is the
rectangle poisoned.
"""

import copy
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import banabner_finder as bf
import banabner_model as bm

KNOWN = json.loads((HERE / "known_grid.json").read_text())
FAIL = []


def check(name, ok, detail=""):
    print(f"{'ok  ' if ok else 'FAIL'}  {name}{'  ' + detail if detail else ''}")
    if not ok:
        FAIL.append(name)


def status_with(catalogue):
    real = bm.CATALOGUE
    bm.CATALOGUE = catalogue
    try:
        model = bm.Model()
    finally:
        bm.CATALOGUE = real
    model.pin(*bf.to_maps(bf.leader(bf.Candidate(KNOWN["grid"], KNOWN["shading"]))))
    status, _, _ = model.solve(30, 1)
    return status.name


def poisoned(field, value):
    """The catalogue with every 2x2 box offset's `field` set to `value`."""
    out = copy.deepcopy(bm.CATALOGUE)
    for entry in out["2x2"]["B"].values():
        entry[field] = value
    return out


def main():
    real = status_with(bm.CATALOGUE)
    check("the real catalogue accepts the known grid", real == "OPTIMAL", real)
    dead = status_with(poisoned("count", 0))
    check(
        "the shading side forbids a placement the catalogue calls dead",
        dead == "INFEASIBLE",
        dead,
    )
    # The known grid's 2x2 holds 1, 2, 6 and 8, none of them a 5.
    narrow = status_with(poisoned("support", [[[5], [5]], [[5], [5]]]))
    check(
        "the digit side takes cell domains from the catalogue",
        narrow == "INFEASIBLE",
        narrow,
    )

    print(f"\n{len(FAIL)} failing" if FAIL else "\nall checks pass")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
