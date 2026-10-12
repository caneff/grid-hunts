"""Renbanana puzzle rules as CP-SAT constraints, shared by the hunt and probes.

The rules are in `renbanana/FEASIBILITY.md`. The encodings below live here
once, so a fix reaches every user: `renbanana_cpsat` (the hunt) and the probes
`probe_inverted`, `prove_pair`, `probe_circle_pattern` and `max_house_circles`
import them and keep only what they do differently. The counting and hunting
scripts (`count_circled_pairs`, `count_circled_sets`, `hunt_circled_pair`) do
not use this module yet and carry their own sudoku and whisper code.

The rule-5 pieces (`whisper`, `whisper_on_shading`, `whisper_on_digits`) take
the chocolate `difference` (default 5, Renbanana). Nothing here encodes the
banana rule: the callers do, and `renbanana_verify.check` takes it as
`banana_rule`. Encodings that assume a difference of 5 (the high/low
checkerboard, no 5 in a chocolate group of two or more) stay in the renban
callers and are not offered for nabner.

An encoding is either exact or a relaxation (never excludes a legal grid), and
its docstring says which: an INFEASIBLE from a model built of these is a proof
only while every piece is one of those two.

`renbanana/tools/test_renbanana_model.py` pins each one to a small board.
"""

import json
from pathlib import Path

from renbanana_verify import neighbours

N = 9
CELLS = [(r, c) for r in range(N) for c in range(N)]
IDX = {p: i for i, p in enumerate(CELLS)}
ADJACENT = [(p, q) for p in CELLS for q in neighbours(*p) if IDX[q] > IDX[p]]
MAX_BANANA = 9  # a renban group holds distinct consecutive digits, so <= 9 cells
PLACEMENTS = [
    (h, w, r0, c0)
    for h in range(1, N + 1)
    for w in range(1, N + 1)
    for r0 in range(N - h + 1)
    for c0 in range(N - w + 1)
]


# --------------------------------------------------------------- catalogue

CATALOGUE_DIR = Path(__file__).resolve().parent.parent / "docs/research/renbanana"


def load_catalogue(difference=5):
    """The chocolate rectangle catalogue for one chocolate difference, as
    `finders/renbanana/tools/build_rectangle_catalogue.py` wrote it."""
    name = "rectangle-catalogue" + ("" if difference == 5 else f"-d{difference}")
    return json.loads((CATALOGUE_DIR / f"{name}.json").read_text())


def catalogue_fact(catalogue, a, b, ro, co):
    """Layer B of `catalogue` for an `a` by `b` rectangle whose top-left cell
    sits at box offset (ro, co), turned to that orientation: `count` (0 when
    the shape or offset is absent), `support` (per-cell digit lists, or None)
    and `circle_cells` ((i, j) offsets).

    The catalogue stores a <= b only. Transposing swaps rows and columns, and
    the 3x3 boxes are symmetric under it, so the offset swaps too.
    """
    flip = a > b
    if flip:
        a, b, ro, co = b, a, co, ro
    entry = catalogue.get(f"{a}x{b}", {}).get("B", {}).get(f"{ro},{co}", {})
    support = entry.get("support")
    if not support or not support[0]:
        support = None
    elif flip:  # stored rows are the other orientation's columns
        support = [[support[j][i] for j in range(a)] for i in range(b)]
    circles = entry.get("circle_cells", [])
    return {
        "count": entry.get("count", 0),
        "support": support,
        "circle_cells": [(c, r) if flip else (r, c) for r, c in circles],
    }


# ------------------------------------------------------------------ digits


def sudoku(m, d):
    """Normal sudoku on the digit variables `d`."""
    for i in range(N):
        m.add_all_different([d[i, c] for c in range(N)])
        m.add_all_different([d[r, i] for r in range(N)])
    for br in range(3):
        for bc in range(3):
            m.add_all_different(
                [d[br * 3 + r, bc * 3 + c] for r in range(3) for c in range(3)]
            )


def whisper(m, d, choc, difference=5):
    """Rule 5, shading and digits both free: two adjacent chocolate cells
    differ by `difference` or more. Exact.

    The magnitude gets its own variable and `far` is a genuine reification of
    it -- enforcing one branch on `far` and the other on its negation would
    demand every adjacent pair differ by 5, chocolate or not, which no sudoku
    satisfies.
    """
    for p, q in ADJACENT:
        mag = m.new_int_var(0, 8, f"m{p}{q}")
        m.add_abs_equality(mag, d[p] - d[q])
        far = m.new_bool_var(f"far{p}{q}")
        m.add(mag >= difference).only_enforce_if(far)
        m.add(mag <= difference - 1).only_enforce_if(far.negated())
        m.add_bool_or([choc[p].negated(), choc[q].negated(), far])


def whisper_on_shading(m, d, is_choc, difference=5):
    """Rule 5 on a fixed shading: each chocolate adjacency differs by
    >= `difference`."""
    for p, q in ADJACENT:
        if is_choc[p] and is_choc[q]:
            mag = m.new_int_var(0, 8, f"a{p}{q}")
            m.add_abs_equality(mag, d[p] - d[q])
            m.add(mag >= difference)


def whisper_on_digits(m, choc, grid, difference=5):
    """Rule 5 with the digits fixed: an adjacent pair differing by less than
    `difference` cannot both be chocolate. A plain clause, and exact."""
    for p, q in ADJACENT:
        if abs(grid[p] - grid[q]) < difference:
            m.add_bool_or([choc[p].negated(), choc[q].negated()])


# ----------------------------------------------------------------- shading


def rectangle_lemma(m, choc):
    """Rule 3: connected, and no 2x2 window holding exactly three chocolate
    cells, means every chocolate group is a rectangle. Exact.
    """
    for r in range(N - 1):
        for c in range(N - 1):
            m.add(sum(choc[r + i, c + j] for i in range(2) for j in range(2)) != 3)


def inside_of(h, w, r0, c0):
    return [(r0 + i, c0 + j) for i in range(h) for j in range(w)]


def border_of(h, w, r0, c0):
    return border_of_cells(inside_of(h, w, r0, c0))


def border_of_cells(cells):
    """The cells outside `cells` that touch one of them orthogonally."""
    inside = set(cells)
    return sorted({q for p in inside for q in neighbours(*p) if q not in inside})


def maximal_chocolate_lits(choc, h, w, r0, c0):
    """Literals whose conjunction says this `h` by `w` rectangle is a maximal
    chocolate group: every cell chocolate, every bordering cell banana."""
    return [choc[p] for p in inside_of(h, w, r0, c0)] + [
        choc[q].negated() for q in border_of(h, w, r0, c0)
    ]


def chocolate_spot(m, choc, h, w, r0, c0, name):
    """One bool that is true only if that rectangle is a maximal chocolate
    group. Implication one way, so the shading never forces it true."""
    here = m.new_bool_var(name)
    for lit in maximal_chocolate_lits(choc, h, w, r0, c0):
        m.add_implication(here, lit)
    return here


def forbid_dead_chocolate(m, choc, is_dead):
    """Forbid every placement `is_dead(h, w, r0, c0)` calls dead as a maximal
    chocolate rectangle. What is dead is the caller's catalogue question
    (`renbanana_cpsat.fillings_at`); the clause is the same everywhere.
    Returns how many placements it forbade."""
    count = 0
    for h, w, r0, c0 in PLACEMENTS:
        if is_dead(h, w, r0, c0):
            m.add_bool_or(
                [lit.negated() for lit in maximal_chocolate_lits(choc, h, w, r0, c0)]
            )
            count += 1
    return count


def forbid_banana_group(m, choc, group):
    """Cut one pattern: these cells banana with a fully chocolate border. No
    legal grid contains a rectangular banana group, so it holds for good."""
    group = set(group)
    border = {q for p in group for q in neighbours(*p) if q not in group}
    m.add_bool_or([choc[p] for p in group] + [choc[q].negated() for q in border])


def forbid_banana_rectangles(m, choc):
    """Rule 4 outright: one clause per rectangle placement forbidding it as a
    maximal banana group (2025 on a 9x9). Exact, with no cut loop."""
    for h, w, r0, c0 in PLACEMENTS:
        forbid_banana_group(m, choc, inside_of(h, w, r0, c0))


def banana_labels(m, choc, pin=True):
    """A label per banana cell, for grouping bananas without a search.

    Each banana cell carries exactly one label `ell`, an index no greater than
    its own; chocolate carries none; adjacent banana cells share theirs. So a
    banana component has one label, at most its least cell index. Returns
    `lab[p, ell]`.

    `pin` adds: the cell whose index is `ell` carries label `ell` whenever any
    cell does. The label of a component is then exactly the
    least index of *some* component carrying it. That is not "exactly its own":
    two disjoint banana components can still share a label, and then a per-label
    rule (renban's "distinct and consecutive") lands on their union, a gap in
    one plugged by a digit from the other. Neither setting closes that. The
    callers that need it closed do it themselves: `probe_circle_pattern` with a
    rank chain to the owner, `probe_inverted` with lazy cuts on the solved
    shading (`Shadings.offenders`). `prove_pair` leaves it open and re-checks
    each hit with `renbanana_verify.check`, so its INFEASIBLE is a proof and
    its hits are candidates. A component can always take its own least index, so no
    legal grid is excluded and an INFEASIBLE stays a proof.
    """
    lab = {
        (p, ell): m.new_bool_var(f"l{p}_{ell}")
        for p in CELLS
        for ell in range(IDX[p] + 1)
    }
    for p in CELLS:
        m.add(sum(lab[p, ell] for ell in range(IDX[p] + 1)) == 1 - choc[p])
    for p, q in ADJACENT:
        lo, hi = (p, q) if IDX[p] < IDX[q] else (q, p)
        for ell in range(IDX[lo] + 1):
            # both banana and `lo` labelled ell  =>  `hi` labelled ell
            m.add_bool_or([choc[p], choc[q], lab[lo, ell].negated(), lab[hi, ell]])
        for ell in range(IDX[lo] + 1, IDX[hi] + 1):
            # a label above `lo`'s index cannot be shared with it
            m.add_bool_or([choc[p], choc[q], lab[hi, ell].negated()])
    if pin:
        for ell in range(len(CELLS)):
            owner = CELLS[ell]
            for p in CELLS:
                if IDX[p] >= ell and p != owner:
                    m.add_implication(lab[p, ell], lab[owner, ell])
    return lab
