"""The hybrid rules (U-Bahn with Choco-Banana over grid cells and number
cells, #782) read off hand-made grids, with no solver.

    uv run finders/ubahn/test_ubahn_hybrid.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import hybrid
import network

ok = True


def check(name, cond):
    global ok
    status = "ok" if cond else "FAIL"
    if not cond:
        ok = False
    print(f"{status}: {name}")


def ring(top, left, bottom, right):
    """The edges of the rectangular loop with these corner rows and columns."""
    edges = set()
    for c in range(left, right):
        edges |= {((top, c), (top, c + 1)), ((bottom, c), (bottom, c + 1))}
    for r in range(top, bottom):
        edges |= {((r, left), (r + 1, left)), ((r, right), (r + 1, right))}
    return frozenset(edges)


# A number cell's value is read from the network. The loop round a 3x3 board:
# four turns at the corners, a straight in the middle of each side, a blank
# centre. Row 1 and row 3 hold 2 turns and 1 straight, row 2 holds 2 straights
# and 1 blank; the columns read the same.
LOOP3 = ring(0, 0, 2, 2)
values = hybrid.values(LOOP3, 3, 3)
check(
    "3x3 loop: grid cells are worth turn 1, straight 2, blank 0",
    [[values[r, c] for c in range(3)] for r in range(3)]
    == [[1, 2, 1], [2, 0, 2], [1, 2, 1]],
)
# Strips from the inside out: turn at -1, straight at -2, branch at -3, cross
# at -4. (r, -k) is row r's number cell, (-k, c) column c's.
check(
    "3x3 loop: row 1's number cells read turn 2, straight 1, branch 0, cross 0",
    [values[0, -k] for k in (1, 2, 3, 4)] == [2, 1, 0, 0],
)
check(
    "3x3 loop: column 2's number cells read turn 0, straight 2, branch 0, cross 0",
    [values[-k, 1] for k in (1, 2, 3, 4)] == [0, 2, 0, 0],
)
check(
    "3x3 loop: the board is 9 grid cells and 4 strips of 3 on two sides",
    len(values) == 9 + 2 * 4 * 3,
)
check(
    "no blank strip unless asked for",
    (0, -5) not in values and (-5, 0) not in values,
)

# The blank strip is a fifth strip outside the cross, and it changes the
# board the rules run on.
with_blank = hybrid.values(LOOP3, 3, 3, blank_strip=True)
check(
    "blank strip on: 4 strips become 5",
    len(with_blank) == 9 + 2 * 5 * 3,
)
check(
    "blank strip on: row 2's blank number cell reads 1, row 1's reads 0",
    with_blank[1, -5] == 1 and with_blank[0, -5] == 0,
)

# A banana that is a rectangle, and nothing else wrong. The loop of a 2x2
# board is four turns, a 2x2 block of 1s. Every number cell is even (2 turns
# per row and column, 0 of the rest), so each side's strips are one even
# rectangle, 2x4 on the left and 4x2 above.
LOOP2 = ring(0, 0, 1, 1)
check(
    "2x2 loop: the only failure is its odd 2x2 block",
    hybrid.failures(LOOP2, 2, 2) == ["banana at r1c1 is a 2x2 rectangle"],
)
check(
    "why_not_hybrid gives the first failure",
    hybrid.why_not_hybrid(LOOP2, 2, 2) == "banana at r1c1 is a 2x2 rectangle",
)
check(
    "a set of edges that is no network fails as the plain reader says",
    hybrid.failures(frozenset(), 2, 2) == ["no edge is on"],
)


def cells(*names):
    return [hybrid.parse_cell(name) for name in names]


from_drawing = network.from_drawing


def value_rows(net, rows, cols, blank_strip=False):
    """The board's values as digits, one string per board row, a space
    where no cell is."""
    board = hybrid.values(net, rows, cols, blank_strip)
    depth = hybrid.strips(blank_strip)
    return [
        "".join(str(board.get((r, c), " ")) for c in range(-depth, cols))
        for r in range(-depth, rows)
    ]


check(
    "a cell's name reads back as the cell",
    all(
        hybrid.parse_cell(hybrid.cell_name(cell)) == cell
        for cell in [(0, 0), (3, 2), (1, -1), (0, -4), (-2, 3), (-5, 0)]
    ),
)
check(
    "r2c3, r2:turn and c3:cross name a grid cell and two number cells",
    cells("r2c3", "r2:turn", "c3:cross") == [(1, 2), (1, -1), (-4, 2)],
)
for bad in ("r2", "x1:turn", "r0c1", "r1:loop", "r1c1:turn"):
    try:
        hybrid.parse_cell(bad)
        check(f"{bad!r} names no cell", False)
    except ValueError:
        check(f"{bad!r} names no cell", True)

# A valid hybrid grid, checked by hand: four loops joined by a 2x2 block of
# crosses. Every number cell is even, so each side's strips are one 4x4 even
# rectangle; the crosses are a 2x2 even rectangle; the 12 odd cells are the
# ring of turns round them, which is no rectangle.
FOUR_LOOPS = from_drawing(["┌┐┌┐", "└┼┼┘", "┌┼┼┐", "└┘└┘"])
check(
    "four loops: the board's values as worked by hand",
    value_rows(FOUR_LOOPS, 4, 4)
    == [
        "    0220",  # crosses per column
        "    0000",  # branches
        "    0000",  # straights
        "    4224",  # turns
        "00041111",
        "20021441",
        "20021441",
        "00041111",
    ],
)
check("four loops: a valid hybrid grid", hybrid.failures(FOUR_LOOPS, 4, 4) == [])
check(
    "four loops: why_not_hybrid is empty", hybrid.why_not_hybrid(FOUR_LOOPS, 4, 4) == ""
)

# A circled cell's value is its region's size. A cross is worth 4 and the
# block of crosses is 4 cells; a turn is worth 1 in a region of 12; row 1's
# turn number is 4 in a region of 16.
check(
    "four loops: all four crosses can be circled",
    hybrid.failures(FOUR_LOOPS, 4, 4, cells("r2c2", "r2c3", "r3c2", "r3c3")) == [],
)
check(
    "four loops: a circled turn breaks only the circle rule",
    hybrid.failures(FOUR_LOOPS, 4, 4, cells("r1c1"))
    == ["circle at r1c1: value 1, region of 12 cells"],
)
check(
    "four loops: a circled number cell is held to the same rule",
    hybrid.failures(FOUR_LOOPS, 4, 4, cells("r2c2", "r1:turn"))
    == ["circle at r1:turn: value 4, region of 16 cells"],
)
check(
    "a circle on an icon cell or off the board is refused",
    hybrid.failures(FOUR_LOOPS, 4, 4, [(-1, -1), (0, -5)])
    == ["circle off the board: (-1, -1)", "circle off the board: (0, -5)"],
)

# A chocolate that is not a rectangle, and nothing else wrong, checked by
# hand. Above the grid the straights' row is all 0 and the turns' row is
# 2 1 1 2: the 0s and the two 2s make a U of 6 cells. The crosses' corner 0s
# stand alone, the left strips are one 3x4 even rectangle, r2's two crosses
# are a 1x2, and both bananas are bent.
U_SHAPE = from_drawing(["┌┐┌┐", "├┼┼┤", "└┴┴┘"])
check(
    "U shape: the board's values as worked by hand",
    value_rows(U_SHAPE, 3, 4)
    == [
        "    0110",
        "    1111",
        "    0000",
        "    2112",
        "00041111",
        "22003443",
        "02021331",
    ],
)
check(
    "U shape: the only failure is the chocolate that is no rectangle",
    hybrid.failures(U_SHAPE, 3, 4)
    == ["chocolate at c1:straight is not a rectangle: 6 cells in a 2x4 box"],
)

# A region that would need an icon cell, and nothing else wrong, checked by
# hand. r1c1 is blank, so it joins column 1's turn number above it (2) to row
# 1's turn number on its left (2), and through them every even number cell of
# both sides. The icon cell between those two numbers is a wall: the region
# bends round it and cannot be a rectangle. The one banana (the turns'
# numbers of columns 2 and 3 and the ten pieces under them) is bent too.
ROUND_THE_ICON = from_drawing([" ┌┐ ", "┌┤├┐", "└┴┴┘"])
check(
    "round the icon: the board's values as worked by hand",
    value_rows(ROUND_THE_ICON, 3, 4)
    == [
        "    0000",
        "    0220",
        "    0000",
        "    2112",
        "00020110",
        "02021331",
        "02021331",
    ],
)
check(
    "round the icon: the only failure names the icon cell",
    hybrid.failures(ROUND_THE_ICON, 3, 4)
    == ["chocolate at c1:cross would need an icon cell"],
)

# The blank strip changes the board. Without it this grid is valid: the left
# strips are two 1x4 even rectangles (rows 1 and 4) with odd rows between.
# With it, every row holds 0 blanks, so a fifth column of 0s joins the two
# into a C of 12 cells.
C_SHAPE = from_drawing(["┌┐┌┐", "└┼┤│", "┌┼┤│", "└┘└┘"])
check(
    "C shape: the left strips as worked by hand",
    [row[:4] for row in value_rows(C_SHAPE, 4, 4)[4:]]
    == ["0004", "1111", "1111", "0004"],
)
check("C shape: valid with no blank strip", hybrid.failures(C_SHAPE, 4, 4) == [])
check(
    "C shape: the blank strip joins two rectangles into a C",
    hybrid.failures(C_SHAPE, 4, 4, blank_strip=True)
    == ["chocolate at r1:blank is not a rectangle: 12 cells in a 4x5 box"],
)
check(
    "four loops: still valid with the blank strip",
    hybrid.failures(FOUR_LOOPS, 4, 4, blank_strip=True) == [],
)
check(
    "a blank number cell can be circled only with the blank strip on",
    hybrid.failures(FOUR_LOOPS, 4, 4, cells("r1:blank"))
    == ["circle off the board: (0, -5)"]
    and hybrid.failures(FOUR_LOOPS, 4, 4, cells("r1:blank"), blank_strip=True)
    == ["circle at r1:blank: value 0, region of 20 cells"],
)

# The drawing: number cells as digits, icon cells as their pieces, the
# network as box characters, a circled cell in brackets.
check(
    "four loops drawn with a circled cross and a circled number cell",
    hybrid.drawing(FOUR_LOOPS, 4, 4, cells("r2c2", "c1:turn"))
    == [
        "          ┼  0  2  2  0",
        "          ┬  0  0  0  0",
        "          ─  0  0  0  0",
        " ┼  ├  │  ┌ (4) 2  2  4",
        " 0  0  0  4  ┌──┐  ┌──┐",
        " 2  0  0  2  └─(┼)─┼──┘",
        " 2  0  0  2  ┌──┼──┼──┐",
        " 0  0  0  4  └──┘  └──┘",
    ],
)
check(
    "the blank strip is drawn outermost, under a hollow square",
    hybrid.drawing(LOOP3, 3, 3, blank_strip=True)
    == [
        "             □  0  1  0",
        "             ┼  0  0  0",
        "             ┬  0  0  0",
        "             ─  1  2  1",
        " □  ┼  ├  │  ┌  2  0  2",
        " 0  0  0  1  2  ┌─────┐",
        " 1  0  0  2  0  │     │",
        " 0  0  0  1  2  └─────┘",
    ],
)


sys.exit(0 if ok else 1)
