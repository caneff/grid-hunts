"""The between finder's entry for board questions (spec #65, #94):
`finders/query/query.py halver_between BOARD QUESTION... --out DIR`.

BOARD is a decoded SudokuMaker document whose between lines (type 403) are
the board's clues, as `board.json` is, or a JSON list of lines, each a list
of cell names from end to end, as `unique_9x9.json` is; a list's links are
`board.json` with its between lines replaced by the list's. A board that
holds anything beside its between lines (a given digit, another constraint
type) or is not 9x9 is refused by name (`halver_rules.lines_alone`), as the
lockout entry refuses through `check.read_board`. The lines are drawn grey.
"""

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "halver"))

import rules

# isort: split
from halver_query import HalverQuery
from halver_rules import parse_cell

LINE_COLOR = (150, 150, 150)


def load(board_path):
    doc = json.loads(board_path.read_text())
    if isinstance(doc, list):
        doc = doc_of(doc)
    return HalverQuery(rules.post_between, rules.lines_alone(doc), doc, LINE_COLOR)


def doc_of(names):
    doc = json.loads((HERE / "board.json").read_text())
    (group,) = [
        c for c in doc["puzzle"]["constraints"] if c.get("type") == rules.BETWEEN_LINE
    ]
    n = round(len(doc["puzzle"]["cells"]) ** 0.5)
    group["lines"] = [[r * n + c for r, c in map(parse_cell, line)] for line in names]
    return doc
