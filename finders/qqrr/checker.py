"""Read the QQRR opener, run the model on it, and say what it found.

`load_opener` turns the decoded link (`opener.json`) into an `Opener`, the
classification `OPENER_NOTES.md` records: a circled rank mark is a clue, an
uncircled one a hypothesis, an entered digit a hypothesis, the cage a clue.
`run` builds the model for one corner and one hypothesis setting, then
solves, forbids and solves again up to `count` times; every grid it returns
has been re-ranked by `oracle.py` and matched against the model's own rank
variables. With `tie` it also requires the 7-digit tie of #601 and reports
the pair, rechecked against `oracle.seven_digit_ties`. `render_solution` is a
grid with all three tables; `render` is the one-line verdict.
"""

import json
import sys
import time
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import model
import oracle
from ortools.sat.python import cp_model

from examples._shared import cpsat

CORNERS = {"tl": (0, 0), "tr": (0, 8), "bl": (8, 0), "br": (8, 8)}
CORNER_RANK = 5  # Chris: a QQRR clue of 5 sits in one corner, corner undecided.
CIRCLES = "QR Circles"
WINDOW_MARKS = "QR Ranks"
CELL_CAGES = "QQRR Ranks"


@dataclass
class Opener:
    n: int
    window_clues: dict  # window top-left (row, col) -> (lo, hi) rank band
    cell_clues: dict  # cell (row, col) -> QQRR value
    window_hypotheses: dict  # window top-left -> (lo, hi), fixed only with --hypotheses
    digit_hypotheses: dict  # cell -> digit, fixed only with --hypotheses


@dataclass
class Solution:
    grid: list
    window_ranks: list
    cell_numbers: list
    cell_ranks: list
    tie: tuple | None = None  # an `oracle.seven_digit_ties` entry, on a tie run
    tie_touches: list | None = None  # clued cells sharing a window with a tied cell


@dataclass
class Report:
    status: str  # infeasible | unique | multiple | timeout
    solutions: list
    seconds: float
    corner: str | None
    hypotheses: bool
    count: int
    note: str = ""
    tie: bool = False


def parse_band(text, top):
    """'10' -> (10, 10); '51-56' -> (51, 56); '58+' -> (58, top)."""
    text = text.strip()
    if text.endswith("+"):
        return int(text[:-1]), top
    if "-" in text:
        lo, hi = text.split("-")
        return int(lo), int(hi)
    return int(text), int(text)


def load_opener(path):
    doc = json.loads(Path(path).read_text())["puzzle"]
    cells = doc["cells"]
    n = int(len(cells) ** 0.5)
    assert n * n == len(cells)
    top = (n - 1) ** 2
    by_name = {c.get("name"): c for c in doc["constraints"]}
    circled = {(y, x) for x, y, *_ in by_name[CIRCLES]["symbols"]}
    marks = by_name[WINDOW_MARKS]
    window_clues, window_hypotheses = {}, {}
    for x, y, *rest in marks["symbols"]:
        text = marks["params"][rest[0] if rest else 0]["text"]
        band = parse_band(text, top)
        if not (1 <= band[0] <= band[1] <= top):
            raise ValueError(f"window mark {text!r} at [{x}, {y}] is outside 1..{top}")
        if not (1 <= y <= n - 1 and 1 <= x <= n - 1):
            raise ValueError(
                f"window mark {text!r} at [{x}, {y}] sits on a border intersection "
                "with no window around it"
            )
        # The symbol sits on the grid intersection at (x, y); the window it
        # marks is the four cells around that point, top-left (y - 1, x - 1).
        (window_clues if (y, x) in circled else window_hypotheses)[(y - 1, x - 1)] = (
            band
        )
    cell_clues = {}
    for cage in by_name[CELL_CAGES]["cages"]:
        if len(cage["cells"]) != 1:
            raise ValueError(f"a QQRR cage must hold one cell, got {cage['cells']}")
        (i,) = cage["cells"]
        value = int(cage["value"])
        if not 1 <= value <= n * n:
            raise ValueError(f"QQRR cage value {value} is outside 1..{n * n}")
        cell_clues[divmod(i, n)] = value
    digit_hypotheses = {
        divmod(i, n): c["value"]
        for i, c in enumerate(cells)
        if "value" in c and not c.get("given")
    }
    return Opener(n, window_clues, cell_clues, window_hypotheses, digit_hypotheses)


def run(
    op, *, corner, hypotheses, count, workers, timeout, on_solution=None, tie=False
):
    """Solve the opener under one corner pin and one hypothesis setting.

    `corner` is a CORNERS key or None. With `hypotheses` the entered digits
    and uncircled marks are fixed; without it they are solution hints. Stops
    at `count` solutions, or when CP-SAT proves there is no next one, or when
    `timeout` seconds have elapsed across the whole loop. With `tie`, every
    grid must hold the 7-digit tie (`model.add_seeing_tie`).
    """
    if count < 1:
        raise ValueError(f"count must be at least 1, got {count}")
    if workers < 1:
        raise ValueError(f"workers must be at least 1, got {workers}")
    n = op.n
    ranked = list(op.cell_clues)
    if corner is not None:
        pinned = CORNERS[corner]
        if op.cell_clues.get(pinned, CORNER_RANK) != CORNER_RANK:
            raise ValueError(
                f"corner {corner} already carries QQRR {op.cell_clues[pinned]}; it cannot also be {CORNER_RANK}"
            )
        if pinned not in ranked:
            ranked.append(pinned)
    q = model.build(n, ranked_cells=ranked)
    m = q.m
    pairs = model.add_seeing_tie(q) if tie else None
    for (wr, wc), (lo, hi) in op.window_clues.items():
        m.AddLinearConstraint(q.rank[wr][wc], lo, hi)
        # Pre-prune the top-left digit from the leading-digit band (speed item 5).
        m.AddAllowedAssignments(
            [q.x[wr][wc]], [(d,) for d in model.leading_digits(n, lo, hi)]
        )
    for cell, value in op.cell_clues.items():
        m.Add(q.q[cell] == value)
    if corner is not None:
        m.Add(q.q[CORNERS[corner]] == CORNER_RANK)
    if hypotheses:
        for (r, c), d in op.digit_hypotheses.items():
            m.Add(q.x[r][c] == d)
        for (wr, wc), (lo, hi) in op.window_hypotheses.items():
            m.AddLinearConstraint(q.rank[wr][wc], lo, hi)
    else:
        for (r, c), d in op.digit_hypotheses.items():
            m.AddHint(q.x[r][c], d)
        for (wr, wc), (lo, hi) in op.window_hypotheses.items():
            if lo == hi:
                m.AddHint(q.rank[wr][wc], lo)

    cells = {(r, c): q.x[r][c] for r in range(n) for c in range(n)}
    start = time.monotonic()
    deadline = start + timeout
    solutions = []
    status = None
    while len(solutions) < count:
        s = cpsat.solver(max(deadline - time.monotonic(), 0.0), reproducible=False)
        s.parameters.num_workers = workers
        result = s.Solve(m)
        if result == cpsat.UNKNOWN:
            status = "timeout"
            break
        if result == cp_model.INFEASIBLE:
            if not solutions:
                status = "infeasible"
            elif len(solutions) == 1:
                status = "unique"
            else:
                status = "multiple"
            break
        if result not in cpsat.SOLVED:
            raise RuntimeError(f"CP-SAT returned {s.StatusName(result)}; no verdict")
        sol = _extract(s, q, ranked, pairs, op.cell_clues)
        solutions.append(sol)
        if on_solution:
            on_solution(sol, len(solutions))
        cpsat.forbid(
            m,
            cells,
            {rc: sol.grid[rc[0]][rc[1]] for rc in cells},
            tag=str(len(solutions)),
        )
    if status is None:
        status = "multiple"
    note = ""
    if status == "multiple" and len(solutions) == count:
        note = f"at least {count} solutions (count capped at {count})"
    elif status == "multiple":
        note = f"exactly {len(solutions)} solutions"
    elif status == "timeout":
        note = f"{len(solutions)} solutions found before the {timeout:.0f}s ceiling; no verdict"
    return Report(
        status,
        solutions,
        time.monotonic() - start,
        corner,
        hypotheses,
        count,
        note,
        tie,
    )


def _extract(s, q, ranked, pairs=None, clued=()):
    """Read the grid back and assert the model's ranks are the oracle's.

    With `pairs` (from `model.add_seeing_tie`), the first pair the model set
    true must be one the oracle finds; that entry is the solution's `tie`, and
    `tie_touches` lists the `clued` cells sharing a window with it.
    """
    n = q.n
    grid = [[s.Value(q.x[r][c]) for c in range(n)] for r in range(n)]
    ranks, numbers, cranks = oracle.rank_grid(grid)
    got_ranks = [[s.Value(v) for v in row] for row in q.rank]
    got_numbers = [[s.Value(v) for v in row] for row in q.num]
    got_q = {cell: s.Value(v) for cell, v in q.q.items()}
    if got_ranks != ranks:
        raise AssertionError(
            f"model window ranks disagree with the oracle:\n{got_ranks}\n{ranks}"
        )
    if got_numbers != numbers:
        raise AssertionError(
            f"model cell numbers disagree with the oracle:\n{got_numbers}\n{numbers}"
        )
    for (r, c), v in got_q.items():
        if v != cranks[r][c]:
            raise AssertionError(
                f"model cell rank at {(r, c)} is {v}, oracle says {cranks[r][c]}"
            )
    tie = touches = None
    if pairs is not None:
        chosen = next(k for k, p in pairs.items() if s.Value(p))
        tie = next((t for t in oracle.seven_digit_ties(ranks) if t[:2] == chosen), None)
        if tie is None:
            raise AssertionError(
                f"model tie pair {chosen} is not a tie the oracle finds"
            )
        touches = _touching(n, tie, clued)
    return Solution(grid, ranks, numbers, cranks, tie, touches)


def _touching(n, tie, clued):
    """The clued cells that share a window with either cell of the tie."""
    wins = {w for cell in tie[:2] for w in model.windows_of(n, *cell)}
    return [cell for cell in clued if wins & set(model.windows_of(n, *cell))]


def _cell(rc):
    return f"r{rc[0] + 1}c{rc[1] + 1}"


def _table(rows, width):
    return "\n".join(" ".join(str(v).rjust(width) for v in row) for row in rows)


def render_solution(sol, index):
    head = [f"solution {index}"]
    if sol.tie:
        a, b, number, la, lb = sol.tie
        line = (
            f"tie: {_cell(a)} {'|'.join(map(str, la))} = {_cell(b)} {'|'.join(map(str, lb))}, "
            f"number {number}, QQRR {sol.cell_ranks[a[0]][a[1]]}"
        )
        if sol.tie_touches:
            line += " -- touches the QQRR cage at " + ", ".join(
                map(_cell, sol.tie_touches)
            )
        head.append(line)
    return "\n".join(
        [
            *head,
            _table(sol.grid, 1),
            "window ranks (by top-left cell)",
            _table(sol.window_ranks, 2),
            "cell numbers",
            _table(sol.cell_numbers, 8),
            "cell ranks",
            _table(sol.cell_ranks, 2),
        ]
    )


def render(report):
    """The one-line verdict."""
    head = (
        f"{report.status}: corner={report.corner or 'none'} hypotheses={'on' if report.hypotheses else 'off'} "
        f"tie={'on' if report.tie else 'off'} count<={report.count} {report.seconds:.1f}s"
    )
    return head + (f" -- {report.note}" if report.note else "")
