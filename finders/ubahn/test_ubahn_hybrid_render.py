"""The hybrid grid's picture (#791), read back by pixel.

The grid is the decision log's one 4x4 grid with `c1:turn` and `r2c4`
circled (§ Hybrid), drawn above `GRID` below with its regions worked out by
hand. Then the `render` command, black-box, over a hunt directory written
here by hand. The same grid has three checkerboard windows, so it is also
where the checkerboard symbol is read back (spec #20, #23). A ring is drawn
on a circle that is a condition and on no other valid circle (#31). No solver
runs;
about six seconds, a dozen and a half subprocess starts.

    uv run finders/ubahn/test_ubahn_hybrid_render.py
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "hunt"))
import hybrid
import hybrid_render
import network
from subprocess_env import success_env

FINDER = HERE / "hybrid_finder.py"

ok = True


def check(name, cond):
    global ok
    status = "ok" if cond else "FAIL"
    if not cond:
        ok = False
    print(f"{status}: {name}")


# The board, number cells and all (cross, branch, straight, turn from the
# outside in):
#
#              0  1  0  0
#              1  1  4  0
#              0  1  0  2
#              2  1  0  2
#  0  1  1  2  ┌─────┬──┐
#  0  3  1  0  ├──┬──┤  │
#  1  1  1  1  └──┼──┤  │
#  0  1  0  2     └──┴──┘
#
# Its two bananas: column 2's four number cells with c1:branch (5 cells), and
# the 20 cells around r1c1. r1c2, a straight on its own, is a chocolate of 1.
GRID = network.from_drawing(["┌─┬┐", "├┬┤│", "└┼┤│", " └┴┘"])
GIVEN = [hybrid.parse_cell(name) for name in ("c1:turn", "r2c4")]


def cell(name):
    return hybrid.parse_cell(name)


def fill(picture, name):
    """The colour a cell is filled with: a pixel just inside its corner,
    clear of its number, a ring and the network through its centre."""
    x0, y0, _, _ = picture.box(cell(name))
    return picture.image.getpixel((x0 + 8, y0 + 8))


picture = hybrid_render.Picture(GRID, 4, 4, GIVEN)

check(
    "a chocolate cell is filled with the chocolate colour, grid cell and "
    "number cell alike",
    fill(picture, "r1c2") == hybrid_render.CHOCOLATE
    and fill(picture, "c3:branch") == hybrid_render.CHOCOLATE,
)
check(
    "a banana cell's fill is not the chocolate's",
    fill(picture, "r1c1") != hybrid_render.CHOCOLATE
    and fill(picture, "c2:turn") != hybrid_render.CHOCOLATE,
)
check(
    "two cells of one banana share a tint, grid cell and number cell alike",
    fill(picture, "r1c1") == fill(picture, "r3:turn")
    and fill(picture, "c2:turn") == fill(picture, "c1:branch"),
)
check(
    "two separate bananas have different tints",
    fill(picture, "r1c1") != fill(picture, "c2:turn"),
)
check(
    "the corner above and left of the strips is off the board: background",
    picture.image.getpixel((hybrid_render.MARGIN + 8, hybrid_render.MARGIN + 8))
    == hybrid_render.BACKGROUND,
)


def count(picture, name, colour):
    """How many of a cell's pixels are this colour."""
    x0, y0, x1, y1 = picture.box(cell(name))
    return sum(
        picture.image.getpixel((x, y)) == colour
        for x in range(x0, x1)
        for y in range(y0, y1)
    )


def centre(picture, name):
    x0, y0, x1, y1 = picture.box(cell(name))
    return (x0 + x1) // 2, (y0 + y1) // 2


# The valid circles, by hand from the board above: c1:turn (2) shares a
# chocolate of 2 with c1:straight (0); r1:turn (2) one of 2 with r2:turn (0);
# r2c4 and r3c4, both straights (2), are a chocolate of 2. No other cell's
# value is its region's size: the bananas hold 5 and 20 cells, and no number
# reaches either.
VALID = ["c1:turn", "r1:turn", "r2c4", "r3c4"]
check(
    "the rule reader's valid circles are the four worked out by hand",
    sorted(map(hybrid.cell_name, hybrid.valid_circles(picture.board))) == VALID,
)


def ring(picture, name):
    """The colours where a ring runs through a cell, a set: the four points
    on the ring's line that lie on the cell's diagonals, clear of its number,
    the network through its centre and a symbol on its corner."""
    x, y = centre(picture, name)
    return {
        picture.image.getpixel((x + dx, y + dy)) for dx in (-18, 18) for dy in (-18, 18)
    }


def ringed(picture):
    """The names of the cells with a ring in the given colour, sorted."""
    return sorted(
        hybrid.cell_name(c)
        for c in picture.board
        if count(picture, hybrid.cell_name(c), hybrid_render.GIVEN_RING) > 200
    )


check(
    "a circle that is a condition has a whole ring in the given colour, "
    "heavier than a symbol's outline",
    all(
        ring(picture, name) == {hybrid_render.GIVEN_RING}
        and count(picture, name, hybrid_render.GIVEN_RING) > 600
        for name in ("c1:turn", "r2c4")
    ),
)
check(
    f"a ring is drawn on those two cells and on no other ({ringed(picture)})",
    ringed(picture) == ["c1:turn", "r2c4"],
)
check(
    "a valid circle that is no condition has no ring: where one would run, "
    "the cell's own fill",
    all(
        ring(picture, name) == {fill(picture, name)}
        and not count(picture, name, hybrid_render.GIVEN_RING)
        for name in ("r1:turn", "r3c4")
    ),
)
bare = hybrid_render.Picture(GRID, 4, 4)
check(
    "with no condition no cell has a ring, the four valid circles included",
    ringed(bare) == []
    and all(ring(bare, name) == {fill(bare, name)} for name in VALID),
)

# Checkerboard windows (#23), by hand from the board above: c1:turn is 2 1
# over 1 2, c2:turn is 1 0 over 2 1, both across the turn strip and the
# grid, and r3c1 is 1 4 over 0 3, on the grid. Each has a small checkerboard
# symbol at its centre, the corner its four cells share: the symbol's
# top-left and bottom-right quarters in the symbol's colour, the other two
# white.
WINDOWS = ["c1:turn", "c2:turn", "r3c1"]
check(
    "the rule reader's checkerboard windows are the three worked out by hand",
    [hybrid.cell_name(w) for w in hybrid.checkerboard_windows(picture.board)]
    == WINDOWS,
)


def symbol(picture, corner, image=None):
    """The colour of the checkerboard symbol at the bottom-right corner of
    the cell `corner`, or None when none is drawn there: a symbol's top-left
    and bottom-right quarters share a colour and its other two are white.
    Read from `image`, a decoded file of the same layout, when one is given,
    else from the picture's own."""
    _, _, x, y = picture.box(corner)
    quarters = [
        (image or picture.image).getpixel((x + dx, y + dy))
        for dx, dy in ((-4, -4), (3, 3), (3, -4), (-4, 3))
    ]
    white = hybrid_render.BACKGROUND
    if quarters[0] == quarters[1] != white and quarters[2:] == [white, white]:
        return quarters[0]
    return None


def weight(picture, name, colour):
    """How many pixels of the symbol at this window's centre are `colour`."""
    _, _, x, y = picture.box(cell(name))
    return sum(
        picture.image.getpixel((x + dx, y + dy)) == colour
        for dx in range(-16, 16)
        for dy in range(-16, 16)
    )


def symbols(picture, depth=4, image=None):
    """{the name of a cell: the colour of the symbol at its bottom-right
    corner}, over every corner inside the picture, the icon cells' and the
    corner off the board included. Read from `image` when one is given."""
    return {
        hybrid.cell_name((r, c)) if (r, c) in picture.board else str((r, c)): colour
        for r in range(-depth, 4)
        for c in range(-depth, 4)
        if (colour := symbol(picture, (r, c), image)) is not None
    }


check(
    f"a symbol sits at the centre of each checkerboard window and nowhere "
    f"else, plain when no window is a condition ({symbols(picture)})",
    symbols(picture) == dict.fromkeys(WINDOWS, hybrid_render.WINDOW),
)
marked = hybrid_render.Picture(GRID, 4, 4, GIVEN, battenberg=[cell("c1:turn")])
check(
    "a window that is a condition has its symbol in the given colour, the "
    f"others stay plain ({symbols(marked)})",
    symbols(marked)
    == {
        "c1:turn": hybrid_render.GIVEN_RING,
        "c2:turn": hybrid_render.WINDOW,
        "r3c1": hybrid_render.WINDOW,
    },
)
plain_weight = weight(marked, "c2:turn", hybrid_render.WINDOW)
check(
    f"and it is the heavier of the two ({plain_weight} pixels plain, "
    f"{weight(marked, 'c1:turn', hybrid_render.GIVEN_RING)} as a condition)",
    plain_weight > 50
    and weight(marked, "c1:turn", hybrid_render.GIVEN_RING) > 1.5 * plain_weight,
)
check(
    "the rings are the same with a marking: the two conditions ringed in the "
    "given colour, the other two valid circles bare",
    all(
        ring(marked, name) == {hybrid_render.GIVEN_RING} for name in ("c1:turn", "r2c4")
    )
    and all(ring(marked, name) == {fill(marked, name)} for name in ("r1:turn", "r3c4")),
)
try:
    hybrid_render.Picture(GRID, 4, 4, battenberg=[cell("r1c1")])
    check("a marking on a window that is no checkerboard is refused", False)
except ValueError as e:
    check(
        f"a marking on a window that is no checkerboard is refused ({e})",
        "Battenberg marking at r1c1" in str(e),
    )

# The network. r1c1 is a turn with arms east and south, so its outer corner
# is up and to the left of its centre: the notch two butt-ended lines leave.
x, y = centre(picture, "r1c1")
check(
    "a pixel at the outer corner of a turn is the network's colour",
    picture.image.getpixel((x - 3, y - 3)) == hybrid_render.NETWORK,
)
x2, _ = centre(picture, "r1c2")
check(
    "the network runs along an edge that is on, r1c1 to r1c2",
    picture.image.getpixel(((x + x2) // 2, y)) == hybrid_render.NETWORK,
)
_, y2 = centre(picture, "r2c2")
check(
    "and not along one that is off, r1c2 to r2c2",
    picture.image.getpixel((x2, (y + y2) // 2)) != hybrid_render.NETWORK,
)
check(
    "a blank cell, r4c1, has no network in it",
    not count(picture, "r4c1", hybrid_render.NETWORK),
)


# The `render` command. Two records as a hunt writes them, their edge rows
# read off the drawings by hand: GRID under its two circles at seed 3, and at
# seed 7 the grid with every edge on, which is a hybrid grid with four strips
# and with five.
FULL = network.from_drawing(["┌┬┬┐", "├┼┼┤", "├┼┼┤", "└┴┴┘"])
GRID_RECORD = {
    "rows": 4,
    "cols": 4,
    "exactly": None,
    "h": ["111", "110", "110", "011"],
    "v": ["1011", "1111", "0111"],
    "circles": ["c1:turn", "r2c4"],
    "blank_strip": False,
}
FULL_RECORD = {
    "rows": 4,
    "cols": 4,
    "exactly": None,
    "h": ["111", "111", "111", "111"],
    "v": ["1111", "1111", "1111"],
    "circles": [],
    "blank_strip": False,
}


def run_cli(*args):
    return subprocess.run(
        [sys.executable, str(FINDER), *args],
        capture_output=True,
        text=True,
        env=success_env(),
    )


def hunt_dir(parent, name, records):
    """A hunt directory holding these {seed: record}, with a seed that found
    nothing between them, as progress.jsonl pairs them."""
    out = Path(parent) / name
    out.mkdir()
    (out / "examples.jsonl").write_text(
        "".join(json.dumps(record) + "\n" for record in records.values())
    )
    events = [{"seed": 0, "outcome": "empty"}]
    events += [{"seed": seed, "outcome": "example"} for seed in records]
    (out / "progress.jsonl").write_text(
        "".join(json.dumps(event) + "\n" for event in events)
    )
    return out


def decoded(path):
    """(format, image) of the picture file at `path`, decoded in full, or
    (None, None) when there is no such file."""
    if not Path(path).is_file():
        return None, None
    with Image.open(path) as image:
        image.load()
        return image.format, image.convert("RGB")


def same(image, picture):
    return (
        image is not None
        and image.size == picture.image.size
        and image.tobytes() == picture.image.tobytes()
    )


def names(directory):
    return sorted(p.name for p in directory.iterdir())


four = hybrid_render.Picture(FULL, 4, 4)
five = hybrid_render.Picture(FULL, 4, 4, blank_strip=True)
check(
    "the blank strip adds one strip to each side of the picture",
    five.image.size == tuple(side + hybrid_render.CELL for side in four.image.size),
)
check(
    "the fifth strip's number cells are drawn: c1:blank is filled",
    fill(five, "c1:blank") == hybrid_render.CHOCOLATE,
)

with tempfile.TemporaryDirectory() as d:
    out = hunt_dir(d, "hunt", {3: GRID_RECORD, 7: FULL_RECORD})
    (out / "renders").mkdir()
    (out / "renders" / "99.png").write_text("left by an earlier example list")
    r = run_cli("render", str(out))
    check(f"`render DIR` exits 0 (stderr: {r.stderr[-500:]})", r.returncode == 0)
    check(
        "one PNG per example, named by seed, and nothing else: no temporary "
        f"file, no picture of an earlier list ({names(out / 'renders')})",
        names(out / "renders") == ["3.png", "7.png"],
    )
    pictures = {seed: decoded(out / "renders" / f"{seed}.png") for seed in (3, 7)}
    check(
        "each file decodes as a PNG",
        all(kind == "PNG" for kind, _ in pictures.values()),
    )
    check(
        "seed 3's picture is the grid's, its two conditions ringed as given",
        same(pictures[3][1], picture),
    )
    check("seed 7's picture is the other grid's", same(pictures[7][1], four))
    # GRID_RECORD has no `battenberg` field, as a record written before the
    # condition: it is drawn with no markings, a plain symbol on each
    # checkerboard window.
    check(
        "a record older than the condition is drawn with plain symbols only",
        pictures[3][1] is not None
        and set(symbols(picture, image=pictures[3][1]).values())
        == {hybrid_render.WINDOW},
    )
    check(
        "`render` says how many it wrote and where, and prints no link",
        "2 pictures" in r.stdout
        and str(out / "renders") in r.stdout
        and len(r.stdout) + len(r.stderr) < 500
        and "http" not in r.stdout + r.stderr,
    )

    one = Path(d) / "one.png"
    r = run_cli("render", str(out), "--seed", "7", "--png", str(one))
    check(
        f"`render DIR --seed 7 --png FILE` writes that one grid to FILE "
        f"(stderr: {r.stderr[-300:]})",
        r.returncode == 0
        and same(decoded(one)[1], four)
        and names(Path(d)) == ["hunt", "one.png"],
    )
    check(
        "and prints no link",
        len(r.stdout) + len(r.stderr) < 500 and "http" not in r.stdout + r.stderr,
    )

    # The blank strip: by the flag, or by a record of a hunt that had it on.
    r = run_cli("render", str(out), "--seed", "7", "--png", str(one), "--blank-strip")
    check(
        f"`--blank-strip` draws five strips (stderr: {r.stderr[-300:]})",
        r.returncode == 0 and same(decoded(one)[1], five),
    )
    with_blank = hunt_dir(d, "blank", {7: {**FULL_RECORD, "blank_strip": True}})
    r = run_cli("render", str(with_blank))
    check(
        "a record of a hunt with the blank strip on is drawn with five strips",
        r.returncode == 0 and same(decoded(with_blank / "renders" / "7.png")[1], five),
    )

    # A hunt with markings: the record names the windows that are conditions.
    with_markings = hunt_dir(
        d,
        "markings",
        {3: {**GRID_RECORD, "battenberg": ["c1:turn"], "battenberg_only": False}},
    )
    r = run_cli("render", str(with_markings))
    check(
        f"`render` over a hunt with markings draws the marked window as a "
        f"condition (stderr: {r.stderr[-300:]})",
        r.returncode == 0
        and same(decoded(with_markings / "renders" / "3.png")[1], marked)
        and not same(decoded(with_markings / "renders" / "3.png")[1], picture),
    )

    # A grid that is no hybrid grid on the board drawn is refused, and no
    # picture of the directory is touched: GRID breaks on the fifth strip.
    before = {p.name: p.read_bytes() for p in (out / "renders").iterdir()}
    r = run_cli("render", str(out), "--blank-strip")
    check(
        f"`render DIR --blank-strip` refuses seed 3, exit 2, naming the seed "
        f"and the broken rule ({r.stderr.strip()!r})",
        r.returncode == 2
        and "seed 3" in r.stderr
        and "c1:blank" in r.stderr
        and not r.stdout,
    )
    check(
        "and leaves renders/ as it was",
        {p.name: p.read_bytes() for p in (out / "renders").iterdir()} == before,
    )

    # The refused record comes after a good one: nothing is written until
    # every picture is drawn, so the good one leaves no file either.
    dead_end = hunt_dir(
        d,
        "dead-end",
        {1: FULL_RECORD, 2: {**FULL_RECORD, "h": ["011", "111", "111", "111"]}},
    )
    plain = hunt_dir(
        d,
        "plain",
        {1: {k: v for k, v in FULL_RECORD.items() if k != "circles"}},
    )
    for name, args, reason in (
        ("a directory that is no hunt's", [d], "examples.jsonl"),
        (
            "a seed with no example",
            [str(out), "--seed", "0", "--png", str(one)],
            "seed 0",
        ),
        ("--seed with no --png", [str(out), "--seed", "7"], "--png"),
        ("--png with no --seed", [str(out), "--png", str(one)], "--seed"),
        ("a network with a dead end", [str(dead_end)], "dead end"),
        ("a record with no circles, a plain hunt's", [str(plain)], "'circles'"),
    ):
        r = run_cli("render", *args)
        check(
            f"render refuses {name}, exit 2, naming {reason!r} ({r.stderr.strip()[-200:]!r})",
            r.returncode == 2 and reason in r.stderr and not r.stdout,
        )
    check(
        "a grid refused after a good one leaves no renders/ behind",
        not (dead_end / "renders").exists(),
    )

r = run_cli("--help")
check(
    "--help names the render command and its flags",
    r.returncode == 0
    and all(word in r.stdout for word in ("render DIR", "--seed", "--png", "renders/"))
    and "checkerboard symbol" in " ".join(r.stdout.split())
    and "no ring on any other valid circle" in " ".join(r.stdout.split()),
)

sys.exit(0 if ok else 1)
