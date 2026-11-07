"""Conditions on a board's solutions (spec #65, #95), compiled onto any CP-SAT
model, so a finder writes no compiler.

A condition is one of five small tuples over the finder's variable names:
`Eq(key, value)` and `Gt(key, value)` on one variable, `Not(cond)`, and
`All(conds)` and `Any_(conds)` over a tuple of conditions. `literal(model,
variables, cond)` puts a Bool literal on `model` that is true exactly when
`cond` holds, `variables` being the finder's {name: IntVar}. `keys(cond)` is
every variable name a condition reads, and `require(variables, keys)`
refuses a name the model lacks.

A condition file is JSON, one object per condition:

    {"eq": ["r1c1", 5]}     {"gt": ["r1c1", 5]}     {"not": COND}
    {"all": [COND, ...]}    {"any": [COND, ...]}

`from_json` reads that form and `to_json` writes it.
"""

from typing import Any, NamedTuple


class Eq(NamedTuple):
    key: Any
    value: int


class Gt(NamedTuple):
    key: Any
    value: int


class Not(NamedTuple):
    cond: Any


class All(NamedTuple):
    conds: tuple


class Any_(NamedTuple):
    conds: tuple


def require(variables, keys):
    """Raises a ValueError naming the first of `keys` not in `variables`."""
    missing = [k for k in keys if k not in variables]
    if missing:
        raise ValueError(f"no variable {missing[0]!r} in the finder's model")


def literal(model, variables, cond):
    """A Bool literal of `model` true exactly when `cond` holds."""
    match cond:
        case Not(inner):
            return literal(model, variables, inner).Not()
        case Eq(key, value) | Gt(key, value):
            require(variables, [key])
            var = variables[key]
            b = model.NewBoolVar("")
            if isinstance(cond, Eq):
                model.Add(var == value).OnlyEnforceIf(b)
                model.Add(var != value).OnlyEnforceIf(b.Not())
            else:
                model.Add(var > value).OnlyEnforceIf(b)
                model.Add(var <= value).OnlyEnforceIf(b.Not())
            return b
        case All(conds) | Any_(conds):
            lits = [literal(model, variables, c) for c in conds]
            b = model.NewBoolVar("")
            if isinstance(cond, All):
                model.AddBoolAnd(lits).OnlyEnforceIf(b)
                model.AddBoolOr([lit.Not() for lit in lits]).OnlyEnforceIf(b.Not())
            else:
                model.AddBoolOr(lits).OnlyEnforceIf(b)
                model.AddBoolAnd([lit.Not() for lit in lits]).OnlyEnforceIf(b.Not())
            return b
    raise ValueError(f"unknown condition {cond!r}")


def keys(cond):
    """Every variable name `cond` reads, in order, once each."""
    match cond:
        case Eq(key, _) | Gt(key, _):
            return [key]
        case Not(inner):
            return keys(inner)
        case All(conds) | Any_(conds):
            return list(dict.fromkeys(k for c in conds for k in keys(c)))
    raise ValueError(f"unknown condition {cond!r}")


def from_json(obj):
    """The condition the JSON form `obj` names."""
    if isinstance(obj, dict) and len(obj) == 1:
        ((kind, arg),) = obj.items()
        if kind in ("eq", "gt") and isinstance(arg, list) and len(arg) == 2:
            key, value = arg
            if isinstance(value, int) and not isinstance(value, bool):
                return (Eq if kind == "eq" else Gt)(key, value)
        if kind == "not":
            return Not(from_json(arg))
        if kind in ("all", "any") and isinstance(arg, list) and arg:
            conds = tuple(from_json(c) for c in arg)
            return All(conds) if kind == "all" else Any_(conds)
    raise ValueError(f"unknown condition {obj!r}")


def to_json(cond):
    """`cond` in the JSON form `from_json` reads."""
    match cond:
        case Eq(key, value):
            return {"eq": [key, value]}
        case Gt(key, value):
            return {"gt": [key, value]}
        case Not(inner):
            return {"not": to_json(inner)}
        case All(conds):
            return {"all": [to_json(c) for c in conds]}
        case Any_(conds):
            return {"any": [to_json(c) for c in conds]}
    raise ValueError(f"unknown condition {cond!r}")
