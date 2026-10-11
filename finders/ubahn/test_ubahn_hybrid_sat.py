"""The hybrid's PySAT engines against the exhaustive 4x4 answers (#784,
#785).

`test_ubahn_brute.py` pins what the brute force finds on the whole 4x4 board:
18 valid hybrid grids, 8 with the blank strip, 8 with exactly 2 crosses in r2,
and the class of seven circle conditions. Each engine must list the same
grids and classify each condition the same way. The class words and counts
below are the decision log's table, § Hybrid, written out again; the grids
are the brute force's, judged by the solver-free rule reader. Listing the 18
is also where connectivity is seen at work: the lazy engine adds connectivity
cuts, and the propagator engine raises conflicts on partial assignments.

No 4x4 grid has a circle in an odd region, so the circle rule is then held to
the rule reader on larger boards: every 5x5 grid with each cell circled
alone, and grids the engine found at 7x7 and 10x10, where a number cell can
be circled in an odd region.

One CaDiCaL thread; about seventeen seconds.

    uv run finders/ubahn/test_ubahn_hybrid_sat.py
"""

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import brute
import hybrid
import hybrid_sat
import network
from pysat.solvers import Cadical195

TIME_LIMIT = 10.0
TWO_CROSSES = network.Exactly.parse("2:cross:r2")
ENGINES = (hybrid_sat.LAZY, hybrid_sat.PROPAGATOR)

ok = True


def check(name, cond):
    global ok
    status = "ok" if cond else "FAIL"
    if not cond:
        ok = False
    print(f"{status}: {name}")


def agrees(engine, name, conditions, want):
    """The engine lists the wanted grids exactly. It is asked for one more
    than that, so an engine that has lost a rule stops at its first extra
    grid."""
    got = hybrid_sat.listing(
        conditions, engine, cap=len(want) + 1, time_limit=TIME_LIMIT
    )
    grids = set(got.grids)
    check(
        f"{engine}, {name}: the brute-force grids exactly, {len(want)} of them, "
        f"each once ({len(grids - want)} or more extra, {len(want - grids)} missing)",
        not got.timed_out and grids == want and len(got.grids) == len(want),
    )
    return got


def agrees_with_reader(engine, name, side, count):
    """The engine lists `count` grids of a square board with no condition,
    and the rule reader passes every one. Returns them."""
    got = hybrid_sat.listing(
        hybrid.Conditions(side, side), engine, cap=count + 1, time_limit=TIME_LIMIT
    )
    refused = [g for g in got.grids if hybrid.why_not_hybrid(g, side, side)]
    check(
        f"{engine}, {name}: {count} grids, each once, all passed by the rule "
        f"reader ({len(got.grids)} listed, {len(refused)} refused)",
        not got.timed_out
        and len(set(got.grids)) == len(got.grids) == count
        and not refused,
    )
    return got.grids


def cells(*names):
    return frozenset(hybrid.parse_cell(name) for name in names)


grids = brute.hybrid_grids(4, 4)
with_blank = brute.hybrid_grids(4, 4, blank_strip=True)
two_crosses = {g for g in grids if TWO_CROSSES.holds(g, 4, 4)}
check("4x4, no condition: the brute force counts 18", len(grids) == 18)
check("4x4 with the blank strip: the brute force counts 8", len(with_blank) == 8)
check("4x4 with exactly 2 crosses in r2: it counts 8", len(two_crosses) == 8)

for engine in ENGINES:
    listed = agrees(engine, "4x4, no condition", hybrid.Conditions(4, 4), grids)
    # The board has fillings that break no rule but connectivity, and listing
    # every grid makes the solver propose them: each is refused by a cut, and
    # the list is still the brute force's.
    if engine == hybrid_sat.LAZY:
        lazy_cuts = listed.cuts
        check(
            f"{engine}, 4x4, no condition: connectivity cuts were added "
            f"({listed.cuts}), and no conflict on a partial assignment",
            listed.cuts > 0 and listed.conflicts == 0,
        )
    # The propagator refuses them before the grid is full: it raises a
    # conflict while some edge is still undecided, so fewer full grids in
    # several parts are left to cut.
    if engine == hybrid_sat.PROPAGATOR:
        check(
            f"{engine}, 4x4, no condition: conflicts were raised on partial "
            f"assignments ({listed.conflicts}), and fewer cuts added than the "
            f"lazy engine's {lazy_cuts} ({listed.cuts})",
            listed.conflicts > 0 and listed.cuts < lazy_cuts,
        )
    # The blank strip is off unless asked for, and changes the answer when on.
    agrees(
        engine,
        "4x4 with the blank strip",
        hybrid.Conditions(4, 4, blank_strip=True),
        with_blank,
    )

    # The pinned circle conditions (decision log, § Hybrid): the engine's
    # grids are the brute force's, and its classification is the table's word.
    for names, word, count in (
        ((), "not_unique", 18),
        (("r2c2",), "not_unique", 4),
        (("c1:turn", "r2c4"), "unique", 1),
        (("r1:turn", "r4c2"), "unique", 1),
        (("r2c2", "r2c4"), "infeasible", 0),
        (("c4:turn", "r4:turn"), "infeasible", 0),
        (("r1c1",), "infeasible", 0),
    ):
        label = f"4x4 circles {' '.join(names) or 'none'}"
        conditions = hybrid.Conditions(4, 4, cells(*names))
        want = {g for g in grids if not hybrid.why_not_hybrid(g, 4, 4, cells(*names))}
        check(f"{label}: the brute force counts {count}", len(want) == count)
        agrees(engine, label, conditions, want)
        classify = hybrid_sat.Engine(engine).classify
        got = classify(conditions, time_limit=TIME_LIMIT, workers=1)
        check(
            f"{engine}, {label}: classified {word} (got {got.status})",
            got.status == word,
        )
        check(
            f"{engine}, {label}: the classification's grid is one of them, or "
            f"None for none",
            got.network in want if want else got.network is None,
        )
        # A limit reached is a timeout whatever the true answer is.
        for limit in (0, -1):
            late = classify(conditions, time_limit=limit, workers=1)
            check(
                f"{engine}, {label}: a time limit of {limit} reads timeout "
                f"(got {late.status})",
                late == hybrid.Classified("timeout", None),
            )

    # The piece-count condition, alone and together with circles.
    agrees(
        engine,
        "4x4 with exactly 2 crosses in r2",
        hybrid.Conditions(4, 4, exactly=TWO_CROSSES),
        two_crosses,
    )
    for names, count in ((("r4c2",), 4), (("r2c4",), 0), (("c1:turn", "c4:turn"), 2)):
        label = f"4x4 with exactly 2 crosses in r2, circles {' '.join(names)}"
        want = {
            g for g in two_crosses if not hybrid.why_not_hybrid(g, 4, 4, cells(*names))
        }
        check(f"{label}: the brute force counts {count}", len(want) == count)
        agrees(engine, label, hybrid.Conditions(4, 4, cells(*names), TWO_CROSSES), want)
    # Conditions that "at least" would answer differently: of the 18 grids, 5
    # have no cross in r2 and 5 have one, and 11 have 2 turns in r1.
    for text, count in (("0:cross:r2", 5), ("1:cross:r2", 5), ("2:turn:r1", 11)):
        exactly = network.Exactly.parse(text)
        want = {g for g in grids if exactly.holds(g, 4, 4)}
        check(f"4x4 with {text}: the brute force counts {count}", len(want) == count)
        agrees(
            engine, f"4x4 with {text}", hybrid.Conditions(4, 4, exactly=exactly), want
        )
    # A count past the row's length has no grid.
    agrees(
        engine,
        "4x4 with exactly 5 turns in r1",
        hybrid.Conditions(4, 4, exactly=network.Exactly.parse("5:turn:r1")),
        set(),
    )

    try:
        hybrid_sat.listing(
            hybrid.Conditions(4, 4, frozenset({(-1, -1)})),
            engine,
            cap=1,
            time_limit=TIME_LIMIT,
        )
        check(f"{engine}: a circle on an icon cell is refused", False)
    except ValueError as e:
        check(
            f"{engine}: a circle on an icon cell is refused", "off the board" in str(e)
        )

    # One grid for a seed: a brute-force grid that meets the conditions, the
    # same one on every run of the seed, and not the same one for every seed.
    grid = hybrid_sat.Engine(engine).grid
    conditions = hybrid.Conditions(4, 4, cells("r2c2"))
    want = {g for g in grids if not hybrid.why_not_hybrid(g, 4, 4, cells("r2c2"))}
    sampled = [
        grid(conditions, random.Random(seed), time_limit=TIME_LIMIT)
        for seed in range(12)
    ]
    check(
        f"{engine}, a grid for a seed: found, and one of the brute-force grids",
        all(s.status == "found" and s.network in want for s in sampled),
    )
    check(
        f"{engine}, a grid for a seed: the same grid when the seed runs again",
        grid(conditions, random.Random(3), time_limit=TIME_LIMIT) == sampled[3],
    )
    check(
        f"{engine}, a grid for a seed: the seeds reach more than one grid "
        f"({len({s.network for s in sampled})})",
        len({s.network for s in sampled}) > 1,
    )
    check(
        f"{engine}, a grid for a seed: conditions with no grid read infeasible",
        grid(hybrid.Conditions(4, 4, cells("r1c1")), random.Random(0), time_limit=10)
        == hybrid.Sampled("infeasible", None),
    )
    for limit in (0, -1):
        check(
            f"{engine}, a grid for a seed: a time limit of {limit} reads timeout",
            grid(conditions, random.Random(0), time_limit=limit)
            == hybrid.Sampled("timeout", None),
        )

# A circle in an odd region, which no 4x4 grid has. On this 5x5 grid, worked
# by hand in `test_ubahn_hybrid_model.py`, r1c2 is a branch in a bent region
# of three.
BENT_THREE = network.from_drawing(["┌┬─┬┐", "├┼┬┤│", "│├┘├┤", "├┴┬┼┘", "└─┴┘ "])
check(
    "5x5 bent three: the rule reader passes it with r1c2 circled",
    hybrid.failures(BENT_THREE, 5, 5, cells("r1c2")) == [],
)
for engine in ENGINES:
    # Every 5x5 grid, which no brute force reaches: the rule reader must pass
    # each one, and the count is the CP-SAT engine's own (decision log,
    # § Hybrid: the CP-SAT finder).
    every = set(agrees_with_reader(engine, "5x5, no condition", 5, 31))
    # Then a cell of the board circled alone. A circle only ever rules a
    # grid out, so the rule reader says which of the 31 each circle keeps.
    # Every cell on the lazy engine; the propagator engine runs the same
    # clauses, so r1c2 and every fifth cell.
    board = sorted(hybrid.values(BENT_THREE, 5, 5))
    kept = {
        cell: {g for g in every if not hybrid.why_not_hybrid(g, 5, 5, [cell])}
        for cell in (board if engine == hybrid_sat.LAZY else [(0, 1), *board[::5]])
    }
    check("5x5: r1c2 circled keeps the bent three alone", kept[0, 1] == {BENT_THREE})
    wrong = [
        hybrid.cell_name(cell)
        for cell, want in kept.items()
        if set(
            hybrid_sat.listing(
                hybrid.Conditions(5, 5, frozenset({cell})),
                engine,
                cap=len(want) + 1,
                time_limit=TIME_LIMIT,
            ).grids
        )
        != want
    ]
    check(
        f"{engine}, 5x5: each of {len(kept)} cells circled alone keeps the "
        f"grids the rule reader keeps (wrong: {wrong})",
        not wrong,
    )


def takes(conditions, net):
    """Whether the engines' rules for these conditions allow this grid."""
    clauses, edge, _ = hybrid_sat.rules(conditions)
    with Cadical195(bootstrap_with=clauses) as solver:
        return solver.solve(
            assumptions=[var if e in net else -var for e, var in edge.items()]
        )


# The circle rule where no enumeration reaches, on three grids an engine found:
# the rules must take a circle exactly where the rule reader says the cell's
# value is its region's size. Per grid: every such cell, each alone and all at
# once, and every seventh of the others. The 7x7 and the 10x10 grid hold what
# smaller boards do not, a number cell that can be circled in an odd region:
# c1:branch in one of 3 cells, r8:straight in one of 5.
BRANCH_OF_3 = [
    "┌┬┬┬─┐ ",
    "├┘├┼┐├┐",
    "├─┼┴┘││",
    "│┌┴┬┐└┤",
    "├┼┬┤└┐│",
    "└┴┤├┬┤│",
    "  └┘└┴┘",
]
STRAIGHT_OF_5 = [
    "┌┬┬┬─┐┌┐┌┐",
    "├┼┼┤┌┤│└┘│",
    "│├┴┴┤├┼┬┬┤",
    "│├─┐│└┼┤││",
    "│└─┴┴─┴┼┴┘",
    "├┐┌┐┌─┬┼┬┐",
    "├┼┴┼┼┐└┴┴┘",
    "│└┐││└┬──┐",
    "├┐└┤├┐│┌┐│",
    "└┴─┘└┴┘└┴┘",
]
# r6c4 is a cross, worth 4, at one end of an even region of 5 cells in a row
# or column: the 4 cells nearest it are all the cells within 3 steps, so only
# a count that looks one step further tells this region from one of 4.
CROSS_AT_AN_END = [
    "┌┐ ┌─┬┐",
    "├┴┐│┌┴┘",
    "├┐├┼┤  ",
    "└┘└┼┤┌┐",
    "┌─┐│└┼┤",
    "│┌┴┼┐├┘",
    "└┴─┴┴┘ ",
]
refused, wrongly_taken, odd_regions = [], [], {}
for drawn in (BRANCH_OF_3, STRAIGHT_OF_5, CROSS_AT_AN_END):
    side, found = len(drawn), network.from_drawing(drawn)
    check(
        f"{side}x{side} {drawn[0]}: the rule reader passes the grid",
        hybrid.failures(found, side, side) == [],
    )
    board = hybrid.values(found, side, side)
    size = {cell: len(region) for region in hybrid.regions(board) for cell in region}
    can = {cell for cell in board if board[cell] == size[cell]}
    odd_regions.update(
        {hybrid.cell_name(cell): board[cell] for cell in can if board[cell] % 2}
    )
    refused += [
        (drawn[0], sorted(circles))
        for circles in [can, *({cell} for cell in can)]
        if not takes(hybrid.Conditions(side, side, frozenset(circles)), found)
    ]
    wrongly_taken += [
        (drawn[0], cell)
        for cell in sorted(set(board) - can)[::7]
        if takes(hybrid.Conditions(side, side, frozenset({cell})), found)
    ]
check(
    f"7x7 and 10x10: number cells can be circled in odd regions of 3 and of 5 "
    f"({odd_regions})",
    odd_regions == {"c1:branch": 3, "r1:branch": 3, "r2:branch": 3, "r8:straight": 5},
)
check(
    f"7x7 and 10x10: the rules take every circle the rule reader does "
    f"(refused: {refused})",
    not refused,
)
check(
    f"7x7 and 10x10: the rules refuse a circle the rule reader refuses "
    f"(taken: {wrongly_taken})",
    not wrongly_taken,
)
found = network.from_drawing(CROSS_AT_AN_END)
check(
    "7x7, a cross at an end of 5 even cells: the rule reader refuses its circle",
    hybrid.failures(found, 7, 7, cells("r6c4"))
    == ["circle at r6c4: value 4, region of 5 cells"],
)
check(
    "7x7, a cross at an end of 5 even cells: the rules refuse its circle",
    not takes(hybrid.Conditions(7, 7, cells("r6c4")), found),
)

sys.exit(0 if ok else 1)
