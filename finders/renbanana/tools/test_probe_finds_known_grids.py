"""The inverted probe must find a shading for every grid we already know is
legal. Its verdicts are proofs — an INFEASIBLE says a solved grid carries no
Renbanana shading at all — so a bug here would silently discard real grids.

    uv run --with ortools finders/renbanana/tools/test_probe_finds_known_grids.py [--cover]

Run it from the repo root, after touching probe_inverted.py. `--cover` (in
`just check`, about 25s) solves only the five grids that between them hold
every chocolate rectangle shape and banana group size the pool holds; the
full run (`just test-finders-slow`, about 15 minutes) solves them all. The
key is what each grid's known shading holds, but the probe may return another
shading of the same grid, so the subset is a broad guard against an
over-constrained model, not proof that every keyed shape is exercised. Box
offset is not in the key: keying on it takes 30 grids, about two minutes.
"""

import sys
from pathlib import Path

sys.path.insert(0, "finders/renbanana/tools")
sys.path.insert(0, "finders")
import renbanana_verify as rv
from ortools.sat.python import cp_model as cp
from probe_inverted import Shadings

CANDIDATES = sorted(Path("docs/research/renbanana").glob("candidates*/cand_*.json"))


def shape_keys(path):
    """What a grid's known shading exercises in the probe's model: each
    chocolate rectangle's shape (the catalogue's dead-placement clauses) and
    each banana group's size (the renban label encoding)."""
    _, is_choc, _ = rv.load(path)
    keys = set()
    for g in rv.components(is_choc, True):
        rows, cols = sorted({r for r, _ in g}), sorted({c for _, c in g})
        keys.add(("chocolate", len(rows), len(cols)))
    for g in rv.components(is_choc, False):
        keys.add(("banana", len(g)))
    return keys


def covering_grids():
    """A few grids that between them hold every key the pool holds."""
    keys = {p: shape_keys(p) for p in CANDIDATES}
    need = set().union(*keys.values())
    picked = []
    while need:
        best = max(CANDIDATES, key=lambda p: len(keys[p] & need))
        picked.append(best)
        need -= keys[best]
    return picked


def check(path):
    grid, is_choc, _ = rv.load(path)
    m = Shadings(grid)
    st, found = m.solve(30.0, 1, 0)
    name = cp.CpSolver().status_name(st).lower()
    same = found == is_choc if found else False
    ok = found is not None
    if found is not None:
        violations = rv.check(grid, found)
        ok = ok and not violations
        if violations:
            print(f"  ILLEGAL: {violations[0]}")
    print(
        f"{path.parent.name}/{path.name}: {name} cuts={m.cuts} matches_original={same}"
        + (
            ""
            if found is None
            else f" choc={sum(found.values())} (orig {sum(is_choc.values())})"
        )
    )
    return ok


if __name__ == "__main__":
    assert len(CANDIDATES) >= 200, f"{len(CANDIDATES)} known grids: pool missing?"
    paths = covering_grids() if "--cover" in sys.argv[1:] else CANDIDATES
    ok = True
    for path in paths:
        ok = check(path) and ok
    print("PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)
