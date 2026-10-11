"""The hybrid finder's `links` command (#795), black-box: a hunt's output
directory in, given circles and given numbers as flags, a Penpa+ link file per
example out, decoded back to its parts with `penpa_decode.py`.

A short 4x4 hunt (one CP-SAT worker, a few seconds) supplies real hybrid
grids. For each link the test reads the board size, the circles and the
printed numbers back, and checks that nothing else is drawn; that the answer
part is the plain link's for the same network; that a circle which is not
valid is refused by name; and that the rules text is the one Chris pasted.

    uv run finders/ubahn/test_ubahn_hybrid_links.py
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "hunt"))
import hybrid
import penpa
from penpa_decode import Decoded, edges_of, parameter
from subprocess_env import success_env

FINDER = HERE / "hybrid_finder.py"

ok = True


def check(name, cond):
    global ok
    status = "ok" if cond else "FAIL"
    if not cond:
        ok = False
    print(f"{status}: {name}")


def run_cli(*args):
    return subprocess.run(
        [sys.executable, str(FINDER), *args],
        capture_output=True,
        text=True,
        env=success_env(),
    )


def read_jsonl(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line]


def network_of(rec):
    net = set()
    for r, bits in enumerate(rec["h"]):
        net |= {((r, c), (r, c + 1)) for c, bit in enumerate(bits) if bit == "1"}
    for r, bits in enumerate(rec["v"]):
        net |= {((r, c), (r + 1, c)) for c, bit in enumerate(bits) if bit == "1"}
    return frozenset(net)


def table_index(decoded, strips, cell):
    """Index of a cell of the board in the decoded table, worked out here
    from the layout: strip k of a row's number cells is k columns in from the
    grid's left, the first grid cell sits 2 + strips in."""
    r, c = cell
    g = 2 + strips
    return (g + c) + (g + r) * (decoded.nx + 4)


def hunt(tmp, name, *flags):
    out = Path(tmp) / name
    r = run_cli(
        *("--rows", "4", "--cols", "4", "--timeout", "10", "--engine", "cpsat"),
        *flags,
        *("--out", str(out), "--seeds=0:6", "--workers", "1"),
    )
    assert r.returncode == 0, r.stderr[-300:]
    return out


RULES = (
    "U-Bahn:\n"
    "Draw in the dotted grid a single connected network of lines going "
    "through the centers of some orthogonally adjacent cells, which may "
    "branch or turn, but may not have any dead ends.\n"
    "Cells above and to the left of the grid have a value that indicates "
    "how many times a given tile (i.e. a blank, cross, branch, straight "
    "line, or turn), including its rotations, will appear in that row or "
    "column.\n"
    "Choco-Banana:\n"
    "Assign each grid cell a digit from 0 to 4 as follows: empty cell = 0, "
    "corner = 1, straight line = 2, branch = 3, cross = 4.\n"
    "Among both grid cells and clue cells, every group of orthogonally "
    "connected cells with even values is a rectangle (chocolate), and every "
    "group of orthogonally connected cells with odd values is not a "
    "rectangle (banana). Note: squares are rectangles.\n"
    "A digit in a circle counts the number of cells of the chocolate or "
    "banana region that circle lies in."
)

with tempfile.TemporaryDirectory() as tmp:
    out = hunt(tmp, "plain")
    records = read_jsonl(out / "examples.jsonl")
    seeds = [
        e["seed"]
        for e in read_jsonl(out / "progress.jsonl")
        if e.get("outcome") == "example"
    ]
    check(f"the hunt found examples ({len(records)})", len(records) >= 2)
    # The first example with a valid circle on a grid cell and on a number cell.
    for rec, seed in zip(records, seeds, strict=True):  # noqa: B007
        net = network_of(rec)
        board = hybrid.values(net, 4, 4)
        valid = hybrid.valid_circles(board)
        grid_valid = [c for c in valid if min(c) >= 0]
        number_valid = [c for c in valid if min(c) < 0]
        if grid_valid and number_valid:
            break
    check(
        f"an example has a valid circle on a grid cell and on a number "
        f"cell ({len(grid_valid)}, {len(number_valid)})",
        grid_valid and number_valid,
    )
    circle_grid, circle_number = grid_valid[0], number_valid[0]
    circled = [circle_grid, circle_number]
    given = [c for c in board if min(c) < 0 and c not in circled][:3]
    wanted_circles = [hybrid.cell_name(c) for c in circled]
    wanted_numbers = [hybrid.cell_name(c) for c in given]

    # One flag set names the same cells for every example, so the circles
    # are checked on a hunt directory holding the one example they are valid on.
    r = run_cli("links", str(out))
    names = sorted(p.name for p in (out / "links").glob("*.txt"))
    check(
        "with no flags, one link file per example, named by seed, no link printed",
        r.returncode == 0
        and names == sorted(f"{s}.txt" for s in seeds)
        and len(r.stdout) + len(r.stderr) < 500
        and "penpa-edit" not in r.stdout + r.stderr,
    )
    out = Path(tmp) / "one"
    out.mkdir()
    (out / "examples.jsonl").write_text(json.dumps(rec) + "\n")
    (out / "progress.jsonl").write_text(
        json.dumps({"seed": seed, "outcome": "example"}) + "\n"
    )
    r = run_cli(
        "--circles",
        " ".join(wanted_circles),
        "--numbers",
        " ".join(wanted_numbers),
        "links",
        str(out),
    )
    check(f"`links` exits 0 ({r.stderr[-300:]})", r.returncode == 0)
    check(
        "`links` prints no link",
        len(r.stdout) + len(r.stderr) < 500 and "penpa-edit" not in r.stdout + r.stderr,
    )
    text = (out / "links" / f"{seed}.txt").read_text().strip()
    d = Decoded(text)
    check("the board is 4x4 plus four strips each way", (d.nx, d.ny) == (8, 8))
    got_circles = {i for i, v in d.symbol.items() if v[1] == "circle_L"}
    check(
        "the circles sit on exactly the asked cells",
        got_circles == {table_index(d, 4, c) for c in circled},
    )
    check(
        "a circle is the plain white one in the first layer",
        all(d.symbol[i] == [1, "circle_L", 1] for i in got_circles),
    )
    digits = {i: v[0] for i, v in d.number.items() if v[0].isdigit()}
    check(
        "the printed numbers are exactly the given ones, with their values",
        digits == {table_index(d, 4, c): str(board[c]) for c in given},
    )
    check(
        "no other number cell holds any text",
        len(d.number) == len(given),
    )
    hidden = [c for c in circled if min(c) < 0]
    check(
        "a circled number cell that is not given has a circle and no digit",
        hidden
        and all(
            table_index(d, 4, c) in got_circles and table_index(d, 4, c) not in d.number
            for c in hidden
        ),
    )
    check("the answer decodes to the record's edges", edges_of(d, 4) == net)
    check("the rules text is the pasted one", d.rules == RULES)
    check(
        "the grid is drawn dotted, in the payload and in the mode object",
        d.grid_style[0] == "2" and d.mode["grid"][0] == "2",
    )
    check(
        "the answer check is lines only",
        [k for k, v in d.flags.items() if v] == ["sol_loopline"],
    )
    plain = penpa.link(4, 4, net)
    check(
        "the answer part is the plain link's for the same network",
        parameter(text, "a") == parameter(plain, "a")
        and Decoded(plain).flags == d.flags,
    )

    # A given number that is also circled: both drawn.
    both = circle_number
    r = run_cli(
        "--circles",
        hybrid.cell_name(both),
        "--numbers",
        hybrid.cell_name(both),
        "links",
        str(out),
    )
    d = Decoded((out / "links" / f"{seed}.txt").read_text().strip())
    i = table_index(d, 4, both)
    check(
        "a circled given number shows the circle and its number",
        r.returncode == 0
        and i in d.symbol
        and d.number.get(i, [None])[0] == str(board[both]),
    )

    # Default: nothing given, nothing circled.
    r = run_cli("links", str(out))
    d = Decoded((out / "links" / f"{seed}.txt").read_text().strip())
    check(
        "with no flags no circle and no number is drawn",
        r.returncode == 0
        and not [v for v in d.symbol.values() if v[1] == "circle_L"]
        and not d.number,
    )

    # A circle that is not valid is refused by name; no file is touched.
    invalid = next(c for c in board if c not in valid)
    before = (out / "links" / f"{seed}.txt").read_text()
    (out / "links" / "999.txt").write_text("stale\n")
    r = run_cli("--circles", hybrid.cell_name(invalid), "links", str(out))
    check(
        "an invalid circle exits 2 and names the cell and its value",
        r.returncode == 2
        and hybrid.cell_name(invalid) in r.stderr
        and f"value {board[invalid]}" in r.stderr,
    )
    check(
        "a refused run leaves the link set as it was: the stale file stays "
        "and the seed's link is unchanged",
        (out / "links" / "999.txt").exists()
        and (out / "links" / f"{seed}.txt").read_text() == before,
    )
    r = run_cli("links", str(out))
    check(
        "a rerun replaces the link set",
        r.returncode == 0 and not (out / "links" / "999.txt").exists(),
    )

    # A circle off the board is refused by its name, not as a raw tuple.
    r = run_cli("--circles", "r9c9", "links", str(out))
    check(
        "a circle off the board is refused by name",
        r.returncode == 2 and "circle r9c9 is off the 4x4 board" in r.stderr,
    )
    r = run_cli("--numbers", "r1:turn", "classify", "--rows", "4", "--cols", "4")
    check(
        "--numbers outside `links` is refused, not ignored",
        r.returncode == 2 and "--numbers is for `links` only" in r.stderr,
    )
    # A given number must be a number cell.
    r = run_cli("--numbers", "r1c1", "links", str(out))
    check(
        "a grid cell as a given number is refused by name",
        r.returncode == 2 and "r1c1" in r.stderr,
    )
    # No blank strip on this board: a blank number cell is off it.
    r = run_cli("--numbers", "r1:blank", "links", str(out))
    check(
        "a blank number cell on a four-strip board is refused",
        r.returncode == 2 and "r1:blank" in r.stderr,
    )
    r = run_cli("links", str(Path(tmp) / "nowhere"))
    check(
        "a missing directory exits 2 as not a hunt directory",
        r.returncode == 2 and "not a hunt directory" in r.stderr,
    )

    # --blank-strip on a four-strip record draws the fifth strip when the grid
    # is still a hybrid grid with it, and is refused by name when it is not.
    for k, (rec_k, seed_k) in enumerate(zip(records, seeds, strict=True)):
        one_k = Path(tmp) / f"strip-{k}"
        one_k.mkdir()
        (one_k / "examples.jsonl").write_text(json.dumps(rec_k) + "\n")
        (one_k / "progress.jsonl").write_text(
            json.dumps({"seed": seed_k, "outcome": "example"}) + "\n"
        )
        net_k = network_of(rec_k)
        why = hybrid.why_not_hybrid(net_k, 4, 4, (), True)
        r = run_cli("--blank-strip", "links", str(one_k))
        if why:
            good = r.returncode == 2 and why in r.stderr
            good = good and not (one_k / "links").exists()
        else:
            d_k = Decoded((one_k / "links" / f"{seed_k}.txt").read_text().strip())
            good = r.returncode == 0 and (d_k.nx, d_k.ny) == (9, 9)
        check(f"--blank-strip on a four-strip record {k}: {why or 'drawn'}", good)

    # --blank-strip: the fifth strip is drawn, and a hunt's own strip is kept.
    five = hunt(tmp, "five", "--blank-strip")
    r = run_cli("--numbers", "r1:blank", "links", str(five))
    seed5 = next(
        e["seed"]
        for e in read_jsonl(five / "progress.jsonl")
        if e.get("outcome") == "example"
    )
    d5 = Decoded((five / "links" / f"{seed5}.txt").read_text().strip())
    rec5 = read_jsonl(five / "examples.jsonl")[
        [
            e["seed"]
            for e in read_jsonl(five / "progress.jsonl")
            if e.get("outcome") == "example"
        ].index(seed5)
    ]
    value5 = hybrid.values(network_of(rec5), 4, 4, True)[0, -5]
    check(
        "a hunt with the blank strip links a nine-wide board with the blank "
        "number printed, and it is the grid's blank count",
        r.returncode == 0
        and (d5.nx, d5.ny) == (9, 9)
        and {i: v[0] for i, v in d5.number.items() if v[0].isdigit()}
        == {table_index(d5, 5, (0, -5)): str(value5)},
    )

sys.exit(0 if ok else 1)
