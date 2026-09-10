"""The inverted probe must find a shading for every grid we already know is
legal. Its verdicts are proofs — an INFEASIBLE says a solved grid carries no
Renbanana shading at all — so a bug here would silently discard real grids.

    uv run --with ortools docs/research/renbanana/tools/test_probe_finds_known_grids.py

Run it from the repo root, after touching probe_inverted.py.
"""

import sys
from pathlib import Path

sys.path.insert(0, "docs/research/renbanana/tools")
sys.path.insert(0, "docs/research")
import renbanana_verify as rv
from ortools.sat.python import cp_model as cp
from probe_inverted import Shadings

ok = True
for path in sorted(Path("docs/research/renbanana").glob("candidates*/cand_*.json")):
    grid, is_choc, _ = rv.load(path)
    m = Shadings(grid)
    st, found = m.solve(30.0, 1, 0)
    name = cp.CpSolver().status_name(st).lower()
    same = found == is_choc if found else False
    ok = ok and found is not None
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

print("PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)
