"""Toy finder for the board-question driver's own suite (spec #65, #94): one
row of distinct digits.

Not a real finder rule: it exists so `test_query.py` can drive `query.py` end
to end on a model small enough to reason about by hand. The board file is
JSON:

    {"width": 3, "clues": [[0, 1]], "hold_after_builds": 1}

A row of `width` cells, each 1..width, all different; each clue `[i, d]`
pins cell i to digit d. `hold_after_builds` (optional) makes every `build`
after that many sleep for a minute, so a test can kill a run between two
questions. A marked clue's cell is shaded. The toy has no `link` hook.
"""

import json
import time

from ortools.sat.python import cp_model

MARKED_TINT = (120, 200, 255)


class ToyRow:
    def __init__(self, board):
        self.width = board["width"]
        self.clues = [tuple(clue) for clue in board["clues"]]
        self.size = (1, self.width)
        self._hold_after = board.get("hold_after_builds")
        self._builds = 0

    def build(self, clues):
        self._builds += 1
        if self._hold_after is not None and self._builds > self._hold_after:
            time.sleep(60)
        m = cp_model.CpModel()
        cells = {
            f"c{i}": m.NewIntVar(1, self.width, f"c{i}") for i in range(self.width)
        }
        m.AddAllDifferent(cells.values())
        for i, digit in clues:
            m.Add(cells[f"c{i}"] == digit)
        return m, cells

    def cell_of(self, name):
        return 0, int(name.removeprefix("c"))

    def draw(self, canvas, solution, marked=()):
        for k in marked:
            canvas.shade_cell(0, self.clues[k][0], MARKED_TINT)
        canvas.box_lines(1, self.width)
        if solution is not None:
            for i in range(self.width):
                canvas.digit(0, i, solution[f"c{i}"])


def load(board_path):
    return ToyRow(json.loads(board_path.read_text()))
