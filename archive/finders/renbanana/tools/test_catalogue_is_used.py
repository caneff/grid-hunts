"""The #377 catalogue is not optional: every chocolate question the generator
asks must be answered from it rather than re-searched.

    uv run --with ortools python finders/renbanana/tools/test_catalogue_is_used.py

Five call sites, one check each, plus the soundness check that licenses them:
the catalogue is layer B (the rectangle and the boxes, nothing outside), so a
real grid can only narrow its answers, never contradict them.
"""

import contextlib
import json
import sys
from pathlib import Path

CODE_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(CODE_ROOT))
DATA_ROOT = CODE_ROOT.parent / "docs" / "research" / "renbanana"

import renbanana_cpsat as R
import renbanana_verify as rv
from ortools.sat.python import cp_model as cp

FAIL = []


@contextlib.contextmanager
def poisoned(name, replacement):
    """Swap one catalogue reader for the duration of a run. A call site that
    reads the catalogue changes its answer; one that does not keeps it."""
    real = getattr(R, name)
    setattr(R, name, replacement)
    try:
        yield
    finally:
        setattr(R, name, real)


def pool_shading():
    path = sorted(DATA_ROOT.glob("candidates*/cand_*.json"))[0]
    return rv.load(path)[1]


def solve_status(model):
    s = cp.CpSolver()
    s.parameters.max_time_in_seconds = 30
    s.parameters.num_workers = 1
    return s.status_name(s.solve(model))


def stage_1_forbids_dead_placements():
    """Pinning a placement the catalogue calls dead must be refused, and the
    same pin on a live placement must not be."""
    live = (2, 2, 3, 3)
    real_fillings = R.fillings_at
    assert R.fillings_at(2, 2, 0, 0)
    got = {}
    for label, patch in (
        ("real", R.fillings_at),
        (
            "2x2 dead",
            lambda a, b, ro, co: 0 if (a, b) == (2, 2) else real_fillings(a, b, ro, co),
        ),
    ):
        with poisoned("fillings_at", patch):
            model = R.Shadings(lemmas=False)
            model.m.add_bool_or([model.spot(*live)])
            got[label] = solve_status(model.m)
    check(
        "stage 1 forbids catalogue-dead placements",
        got["real"] in ("OPTIMAL", "FEASIBLE") and got["2x2 dead"] == "INFEASIBLE",
        str(got),
    )


def stage_1_circleable_spots_follow_the_catalogue():
    model = R.Shadings(lemmas=False)
    every = len(model._spots(2, 2))
    want = sum(
        1 for r in range(8) for c in range(8) if R.circle_cells_at(2, 2, r % 3, c % 3)
    )
    got = len(model._spots(2, 2, circleable=True))
    check(
        "stage 1 places circled shapes only where a circle is possible",
        got == want and 0 < got < every,
        f"{got} of {every} 2x2 spots",
    )


def stage_3_domains_and_circles_come_from_the_catalogue():
    is_choc = pool_shading()
    status, _, _ = R.fill_digits(is_choc, 30, 1)
    with poisoned(
        "support_at",
        lambda a, b, ro, co: (
            tuple(tuple(frozenset() for _ in range(b)) for _ in range(a))
            if max(a, b) <= 8
            else None
        ),
    ):
        poisoned_status, _, _ = R.fill_digits(is_choc, 30, 1)
    check(
        "stage 3 takes cell domains from the catalogue",
        status == cp.OPTIMAL and poisoned_status == cp.INFEASIBLE,
        f"{status} vs {poisoned_status}",
    )
    _, _, real = R.fill_digits(is_choc, 30, 1, objective="circles")
    with poisoned("circle_cells_at", lambda a, b, ro, co: ()):
        _, _, none = R.fill_digits(is_choc, 30, 1, objective="circles")
    check(
        "stage 3 scores circles only on catalogue circle cells",
        real and real > 0 and none == 0,
        f"{real} vs {none}",
    )


def whisper_holds():
    """Stage 3 keeps the whisper gap on the pool shading's first chocolate
    pair. 2/9 and 8/1 are rejected only because the neighbours of the pair
    cannot keep the gap to them -- they pass if the gap is dropped -- and 1/6
    is a legal pin that must solve."""
    is_choc = pool_shading()
    p, q = next((p, q) for p, q in R.ADJACENT if is_choc[p] and is_choc[q])
    got = {}
    for pin in ((2, 9), (8, 1), (1, 6)):
        m, d, _ = R.digit_model(is_choc)
        m.add(d[p] == pin[0])
        m.add(d[q] == pin[1])
        got[pin] = solve_status(m)
    return (
        got[2, 9] == "INFEASIBLE"
        and got[8, 1] == "INFEASIBLE"
        and got[1, 6] in ("OPTIMAL", "FEASIBLE")
    )


def check(name, ok, detail=""):
    print(f"{'ok  ' if ok else 'FAIL'}  {name}{'  ' + detail if detail else ''}")
    if not ok:
        FAIL.append(name)


def main():
    check(
        "SHAPES drops shapes no grid can hold",
        len(R.SHAPES) == 34,
        f"{len(R.SHAPES)} of 64",
    )
    stage_1_forbids_dead_placements()
    stage_1_circleable_spots_follow_the_catalogue()
    stage_3_domains_and_circles_come_from_the_catalogue()
    check("stage 3 states the whisper gap", whisper_holds())

    # Soundness: nothing the catalogue rules out appears in a grid we accepted.
    cells = dead = circles = unpredicted = 0
    for f in sorted(DATA_ROOT.glob("candidates*/cand_*.json")):
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
        "the candidate pool is not empty -- an empty glob would pass every check below vacuously",
        cells > 0,
        f"DATA_ROOT={DATA_ROOT}",
    )
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
