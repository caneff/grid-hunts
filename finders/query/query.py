"""Board questions (spec #65, #94): ask a fixed board whether it has any
solution and whether it has exactly one, for any CP-SAT finder.

    uv run finders/query/query.py FINDER BOARD QUESTION... --out DIR [--time-limit S]

FINDER is a finder's name, read as `finders/<name>/query_finder.py`, or the
path of a `.py` file. Each QUESTION is `feasible` or `unique`, answered in
order, each solve capped at `--time-limit` seconds (10 unless given). Run it
under `job-run`: it never opens a window.

The finder module's `load(board_path)` reads BOARD and returns the finder:

    clues                       the board's clue list
    size                        (rows, columns) of its picture
    build(clues)                a fresh CP-SAT model and its variables by
                                name, {name: IntVar}
    cell_of(name)               the (row, column) a variable belongs to
    draw(canvas, solution)      the board's clues and, unless `solution` is
                                None, its values, onto a `GridCanvas`
    link(solution)              optional: a SudokuMaker short link of the
                                board with `solution`, None for the board alone

A solution is a {name: value} dict. Each answer is written the moment it is
found: its picture `DIR/<k>-<question>.png`, its links (when the finder has
the hook) one per line in `DIR/<k>-<question>.txt`, then its line of
`DIR/answers.jsonl`, so a line is on disk only with its picture and links;
each file is renamed into place whole, so a killed run leaves none half
written.
A line carries the question, its status, its label, its solutions and the
names of its picture and links. The label is `complete` when the status is
a verdict and `capped` when a solve reached its time limit: a timeout is
never read as feasible, infeasible or unique.

- feasible: `feasible` with one solution, or `infeasible`; the picture is
  that solution, or the board alone.
- unique: the five statuses of `sudoku_kit.uniqueness` (an `invalid` model
  raises); on `not_unique` the picture is both solutions side by side with
  the cells that differ shaded.

The last line printed is `pictures: <path> ...`, one path per answer.
"""

import argparse
import importlib.util
import json
import os
import sys
from pathlib import Path

from ortools.sat.python import cp_model
from PIL import Image
from sudoku_kit import cpsat
from sudoku_kit.uniqueness import check_uniqueness

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "hunt"))

# isort: split
from render import GridCanvas

QUESTIONS = ("feasible", "unique")
DEFAULT_TIME_LIMIT = 10.0
VERDICTS = {"feasible", "infeasible", "unique", "not_unique"}
CELL = 64
MARGIN = 24  # around each board, and between two boards side by side
DIFF_TINT = (255, 90, 90)
DIFF_ALPHA = 0.45


def load_finder(name, board_path):
    """The finder FINDER names, loaded on BOARD."""
    path = Path(name)
    if path.suffix != ".py":
        path = HERE.parent / name / "query_finder.py"
    if not path.is_file():
        raise ValueError(f"no finder {name!r}: {path} is not a file")
    spec = importlib.util.spec_from_file_location(f"query_finder_{path.stem}", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.load(board_path)


def feasible(finder, time_limit):
    model, variables = finder.build(finder.clues)
    solver = cpsat.solver(time_limit)
    status = solver.Solve(model)
    if status in cpsat.SOLVED:
        return "feasible", [{k: solver.Value(v) for k, v in variables.items()}]
    if status == cp_model.INFEASIBLE:
        return "infeasible", []
    if status == cpsat.UNKNOWN:
        return "timeout", []
    raise ValueError(f"feasible got solver status {solver.StatusName(status)}")


def unique(finder, time_limit):
    model, variables = finder.build(finder.clues)
    result = check_uniqueness(model, variables, time_limit=time_limit, workers=1)
    if result.status == "invalid":
        raise ValueError("unique: the finder's model is invalid")
    return result.status, [s for s in (result.first, result.second) if s]


ASK = {"feasible": feasible, "unique": unique}


def board_image(finder, solution, shaded=()):
    rows, cols = finder.size
    canvas = GridCanvas(rows, cols, cell=CELL, margin=MARGIN)
    finder.draw(canvas, solution)
    tint = Image.new("RGB", (CELL, CELL), DIFF_TINT)
    for r, c in shaded:
        x, y = MARGIN + c * CELL, MARGIN + r * CELL
        cell = canvas.image.crop((x, y, x + CELL, y + CELL))
        canvas.image.paste(Image.blend(cell, tint, DIFF_ALPHA), (x, y))
    return canvas.image


def picture(finder, solutions):
    """One board, or two side by side with the cells that differ shaded."""
    if len(solutions) < 2:
        return board_image(finder, solutions[0] if solutions else None)
    first, second = solutions
    differ = {finder.cell_of(k) for k in first if first[k] != second[k]}
    left = board_image(finder, first, differ)
    right = board_image(finder, second, differ)
    image = Image.new("RGB", (2 * left.width + MARGIN, left.height), "white")
    image.paste(left, (0, 0))
    image.paste(right, (left.width + MARGIN, 0))
    return image


def write_answer(out, k, question, status, solutions, finder, time_limit):
    """Picture, links, then the answers.jsonl line; the picture's path."""
    stem = f"{k}-{question}"
    picture_path = out / f"{stem}.png"
    partial = out / f"{stem}.partial.png"
    picture(finder, solutions).save(partial)
    partial.replace(picture_path)
    line = {
        "question": question,
        "status": status,
        "label": "complete" if status in VERDICTS else "capped",
        "time_limit": time_limit,
        "solutions": solutions,
        "picture": picture_path.name,
    }
    link = getattr(finder, "link", None)
    if link is not None:
        links = [link(s) for s in solutions] or [link(None)]
        links_path = out / f"{stem}.txt"
        partial = out / f"{stem}.partial.txt"
        partial.write_text("".join(f"{x}\n" for x in links))
        partial.replace(links_path)
        line["links"] = links_path.name
    with (out / "answers.jsonl").open("a") as f:
        f.write(json.dumps(line) + "\n")
        f.flush()
        os.fsync(f.fileno())
    return picture_path


def positive(text):
    value = float(text)
    if not value > 0:
        raise argparse.ArgumentTypeError(f"--time-limit must be above 0, got {text}")
    return value


def main(argv):
    parser = argparse.ArgumentParser(
        prog="query.py", description=__doc__.split("\n\n")[0]
    )
    parser.add_argument("finder")
    parser.add_argument("board", type=Path)
    parser.add_argument("questions", nargs="+", choices=QUESTIONS, metavar="question")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--time-limit", type=positive, default=DEFAULT_TIME_LIMIT)
    args = parser.parse_args(argv)
    if (args.out / "answers.jsonl").exists():
        parser.error(f"{args.out / 'answers.jsonl'} exists: give a fresh --out")
    try:
        finder = load_finder(args.finder, args.board)
    except ValueError as error:
        parser.error(str(error))
    args.out.mkdir(parents=True, exist_ok=True)
    pictures = []
    for k, question in enumerate(args.questions, 1):
        status, solutions = ASK[question](finder, args.time_limit)
        print(f"{question}: {status}", flush=True)
        pictures.append(
            write_answer(
                args.out, k, question, status, solutions, finder, args.time_limit
            )
        )
    print("pictures: " + " ".join(map(str, pictures)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
