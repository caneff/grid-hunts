"""PROTOTYPE for #36 -- halver_between as a query Board. Throwaway.

Keys: ("d", r, c) the digit, ("h", r, c) 1 on a halver. The adapter is the
whole cost of putting a static-model finder on the driver.
"""

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "halver_between"))
sys.path.insert(0, str(HERE))

import rules
from ortools.sat.python import cp_model
from query import All, Any_, Eq, Found, Infeasible, Timeout, cpsat_literal
from sudoku_kit import cpsat


class HalverBoard:
    def __init__(self, lines):
        self.clues = list(lines)
        self.rm = rules.RuleModel(lines)

    def without(self, clue):
        return HalverBoard([line for line in self.clues if line != clue])

    def solve(self, require, forbid, time_limit):
        m = self.rm.model.clone()
        x = {c: m.GetIntVarFromProtoIndex(v.Index()) for c, v in self.rm.x.items()}
        h = {c: m.GetBoolVarFromProtoIndex(v.Index()) for c, v in self.rm.h.items()}

        def var_of(key):
            kind, r, c = key
            return (x if kind == "d" else h)[r, c]

        keys = [("d", *c) for c in x] + [("h", *c) for c in x]
        for cond in require:
            m.AddBoolOr([cpsat_literal(m, var_of, cond)])
        for i, sol in enumerate(forbid):
            cpsat.forbid(m, {k: var_of(k) for k in keys}, sol, tag=str(i))
        solver = cpsat.solver(time_limit)
        status = solver.Solve(m)
        if status in cpsat.SOLVED:
            return Found({k: solver.Value(var_of(k)) for k in keys})
        if status == cp_model.INFEASIBLE:
            return Infeasible()
        if status == cpsat.UNKNOWN:
            return Timeout()
        raise ValueError(f"solver status {solver.StatusName(status)}")

    def show(self, sol):
        return "\n".join(
            " ".join(
                f"{sol['d', r, c]}{'*' if sol['h', r, c] else ' '}" for c in range(9)
            )
            for r in range(9)
        )


def mark_condition(mark):
    """A marks.json entry as a driver condition."""
    cell = rules.parse_cell(mark["cell"]) if "cell" in mark else None
    cells = [rules.parse_cell(n) for n in mark.get("cells", [])]
    match mark["kind"]:
        case "digit":
            return Eq(("d", *cell), mark["digit"])
        case "candidates":
            return Any_(tuple(Eq(("d", *cell), d) for d in mark["digits"]))
        case "digit_in":
            return Any_(tuple(Eq(("d", *c), mark["digit"]) for c in cells))
        case "halver":
            return Eq(("h", *cell), 1)
        case "halver_digit_in":
            return Any_(
                tuple(
                    All((Eq(("h", *c), 1), Eq(("d", *c), mark["digit"]))) for c in cells
                )
            )
    raise ValueError(f"unknown mark kind {mark['kind']!r}")
