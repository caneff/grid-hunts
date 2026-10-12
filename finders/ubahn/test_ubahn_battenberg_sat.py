"""Battenberg markings on the hybrid's PySAT engines (spec #20, #22), held
to the brute force on 4x4 and to the solver-free rule reader on 5x5.

On 4x4 each engine must list the brute force's grids for every row of the
decision log's table, § Hybrid: Battenberg markings, the 4x4 answers, and
classify it in the table's word. Only two 4x4 grids have a checkerboard
window, so the condition is then held to the rule reader on 5x5, where every
grid has one: a marking only ever rules a grid out, so the grids an engine
lists under markings must be exactly the listed no-condition grids the
reader accepts for them, with and without the negative constraint.

With the blank strip on, its cells are board cells. No grid has a
checkerboard window that touches the blank strip below 7x7, so that case is
read there: a marking on such a window, and the negative constraint with
that window marked and with it left unmarked.

One CaDiCaL thread; about twenty seconds.

    uv run finders/ubahn/test_ubahn_battenberg_sat.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import brute
import hybrid
import hybrid_model
import hybrid_sat

TIME_LIMIT = 10.0
ENGINES = (hybrid_sat.LAZY, hybrid_sat.PROPAGATOR)

ok = True


def check(name, cond):
    global ok
    status = "ok" if cond else "FAIL"
    if not cond:
        ok = False
    print(f"{status}: {name}")


def kept(grids, side, marked, only):
    """The grids of `grids` the rule reader accepts under these markings."""
    return {
        g
        for g in grids
        if not hybrid.why_not_hybrid(
            g, side, side, battenberg=marked, battenberg_only=only
        )
    }


def listed(engine, side, marked, only, cap):
    """The grids the engine lists under these markings, up to `cap`, or None
    on a time limit reached."""
    got = hybrid_sat.listing(
        hybrid.Conditions(side, side, battenberg=marked, battenberg_only=only),
        engine,
        cap=cap,
        time_limit=TIME_LIMIT,
    )
    return None if got.timed_out or len(set(got.grids)) != len(got.grids) else got.grids


grids = brute.hybrid_grids(4, 4)
ONE_GRID = ("c1:turn", "c2:turn", "r3c1", "r1:turn", "r2:turn", "r1c3")
TABLE = (
    ((), False, "not_unique", 18),
    ((), True, "not_unique", 16),
    *(((name,), False, "unique", 1) for name in ONE_GRID),
    (("c1:turn", "c2:turn", "r3c1"), True, "unique", 1),
    (("r1:turn", "r2:turn", "r1c3"), True, "unique", 1),
    (("c1:turn",), True, "infeasible", 0),
    (("c1:turn", "r1:turn"), False, "infeasible", 0),
    (("r1c1",), False, "infeasible", 0),
)
for engine in ENGINES:
    for names, only, word, count in TABLE:
        label = (
            f"{engine}, 4x4 markings {' '.join(names) or 'none'}"
            f"{', negative constraint' if only else ''}"
        )
        marked = hybrid.parse_windows(" ".join(names), 4, 4)
        want = kept(grids, 4, marked, only)
        got = listed(engine, 4, marked, only, len(want) + 1)
        check(
            f"{label}: the brute force's {count} grids exactly "
            f"(listed {None if got is None else len(got)})",
            len(want) == count and got is not None and set(got) == want,
        )
        classified = hybrid_sat.Engine(engine).classify(
            hybrid.Conditions(4, 4, battenberg=marked, battenberg_only=only),
            time_limit=TIME_LIMIT,
            workers=1,
        )
        check(
            f"{label}: classified {word} (got {classified.status})",
            classified.status == word,
        )

    # A marking and a circle in one set of conditions: r2c4 is a valid
    # circle in the one grid that has the marking r3c1, and r4c2 is not.
    for circle, count in (("r2c4", 1), ("r4c2", 0)):
        circles = frozenset({hybrid.parse_cell(circle)})
        marked = hybrid.parse_windows("r3c1", 4, 4)
        want = {
            g
            for g in grids
            if not hybrid.why_not_hybrid(g, 4, 4, circles, battenberg=marked)
        }
        got = hybrid_sat.listing(
            hybrid.Conditions(4, 4, circles, battenberg=marked),
            engine,
            cap=2,
            time_limit=TIME_LIMIT,
        )
        check(
            f"{engine}, 4x4 marking r3c1 with {circle} circled: the brute "
            f"force's {count} ({len(got.grids)} listed)",
            len(want) == count and not got.timed_out and set(got.grids) == want,
        )

    try:
        hybrid_sat.rules(hybrid.Conditions(4, 4, battenberg=frozenset({(3, 3)})))
        check(f"{engine}: a window off the board is refused", False)
    except ValueError as e:
        check(
            f"{engine}: a window off the board is refused, naming r4c5 ({e})",
            "r4c4" in str(e) and "r4c5 is off the board" in str(e),
        )

# 5x5: every grid, which no brute force reaches. The count is the engines'
# own (decision log, § Hybrid: the PySAT engines), and the reader passes each.
every = listed(hybrid_sat.LAZY, 5, frozenset(), False, 32)
check(
    "5x5, no condition: 31 grids, all passed by the rule reader",
    every is not None
    and len(every) == 31
    and not any(hybrid.why_not_hybrid(g, 5, 5) for g in every),
)
every = set(every or ())
by_grid = {g: hybrid.checkerboard_windows(hybrid.values(g, 5, 5)) for g in every}
board_windows = hybrid.windows(hybrid.values(next(iter(every)), 5, 5))
check(
    f"5x5: a board has 48 windows, and every grid has a checkerboard window "
    f"(fewest: {min(map(len, by_grid.values()))})",
    len(board_windows) == 48 and all(by_grid.values()),
)
full_sets = {frozenset(found) for found in by_grid.values()}
alone = [marked for marked in full_sets if len(kept(every, 5, marked, True)) == 1]
check(
    f"5x5: the grids hold {len(full_sets)} different sets of checkerboard "
    f"windows, {len(alone)} of them one grid's alone",
    len(full_sets) == 13 and len(alone) == 7,
)
for engine in ENGINES:
    # Every window marked alone on the lazy engine; the propagator engine
    # runs the same clauses, so every fifth. Then each grid's full set of
    # checkerboard windows, and no marking at all, which the negative
    # constraint leaves no 5x5 grid for.
    singles = board_windows if engine == hybrid_sat.LAZY else board_windows[::5]
    cases = [frozenset({window}) for window in singles]
    cases += [*sorted(full_sets, key=sorted), frozenset()]
    wrong = []
    for marked in cases:
        for only in (False, True):
            want = kept(every, 5, marked, only)
            got = listed(engine, 5, marked, only, len(want) + 1)
            if got is None or set(got) != want:
                wrong.append((sorted(map(hybrid.cell_name, marked)), only))
    check(
        f"{engine}, 5x5: under each of {len(cases)} sets of markings, with and "
        f"without the negative constraint, the grids listed are the ones the "
        f"rule reader keeps (wrong: {wrong[:3]})",
        not wrong,
    )
    got = listed(engine, 5, frozenset(), True, 1)
    check(
        f"{engine}, 5x5: no marking under the negative constraint has no grid",
        got == () and not kept(every, 5, frozenset(), True),
    )


def blank_listed(marked, only, engine, cap):
    """The 7x7 blank-strip grids the engine lists under these markings, or
    None when the listing is not whole: a time limit, or `cap` reached."""
    got = hybrid_sat.listing(
        hybrid.Conditions(
            7, 7, blank_strip=True, battenberg=marked, battenberg_only=only
        ),
        engine,
        cap=cap,
        time_limit=TIME_LIMIT,
    )
    return None if got.timed_out or len(got.grids) >= cap else set(got.grids)


def blank_accepts(grid, marked, only):
    return not hybrid.why_not_hybrid(
        grid, 7, 7, blank_strip=True, battenberg=marked, battenberg_only=only
    )


# 7x7 with the blank strip: the smallest board where a checkerboard window
# touches the blank strip. One grid is taken that has such a window; its
# full set of checkerboard windows under the negative constraint must list
# it, and the same set with the blank-strip window left unmarked must not,
# which only the clause forbidding that window can bring about.
for engine in ENGINES:
    found = None
    for window in hybrid.windows(hybrid.board_cells(7, 7, blank_strip=True)):
        if not any(min(cell) == -5 for cell in hybrid.window_cells(window)):
            continue
        one = hybrid_sat.listing(
            hybrid.Conditions(7, 7, blank_strip=True, battenberg=frozenset({window})),
            engine,
            cap=1,
            time_limit=TIME_LIMIT,
        )
        if one.grids:
            found = (window, one.grids[0])
            break
    check(
        f"{engine}, 7x7 blank strip: a marking on a window that touches the "
        f"blank strip has a grid, and the rule reader accepts it",
        found is not None and blank_accepts(found[1], frozenset({found[0]}), False),
    )
    if found is None:
        continue
    window, grid = found
    full = frozenset(
        hybrid.checkerboard_windows(hybrid.values(grid, 7, 7, blank_strip=True))
    )
    marked = blank_listed(full, True, engine, 200)
    check(
        f"{engine}, 7x7 blank strip: the grid's full set of checkerboard "
        f"windows under the negative constraint lists it, and every grid "
        f"listed passes the rule reader",
        marked is not None
        and grid in marked
        and all(blank_accepts(g, full, True) for g in marked),
    )
    unmarked = blank_listed(full - {window}, True, engine, 200)
    check(
        f"{engine}, 7x7 blank strip: with {hybrid.cell_name(window)} left "
        f"unmarked the negative constraint rules that grid out",
        unmarked is not None
        and grid not in unmarked
        and all(blank_accepts(g, full - {window}, True) for g in unmarked),
    )

# The cpsat engine has no model of the condition and says so itself, for a
# caller that does not come through the finder's flags.
for name, conditions in (
    ("a marking", hybrid.Conditions(4, 4, battenberg=frozenset({(0, 2)}))),
    ("the negative constraint", hybrid.Conditions(4, 4, battenberg_only=True)),
):
    try:
        hybrid_model.build(conditions)
        refused = "no error"
    except ValueError as e:
        refused = str(e)
    check(
        f"the cpsat model refuses {name} by name ({refused!r})",
        "Battenberg markings are on the PySAT engines only" in refused,
    )

sys.exit(0 if ok else 1)
