"""A Penpa+ link read back, for the tests of `penpa.py` (#774, #795).

Written from the note's § 1.2 (docs/research/2026-10-10-u-bahn-penpa-link.md)
and sharing no code with `penpa.py`: it inflates a link, undoes the
abbreviation table in reverse order and reads the layers. Standard library
only; no check runs on import.
"""

import base64
import json
import re
import zlib

# The note's § 1.2 table, plain side then token, in application order. Typed
# out again here on purpose: the encoder's copy is checked against it by the
# published links decoding at all.
TABLE = [
    ("z", "zZ"),
    ('"qa"', "z9"),
    ('"pu_q"', "zQ"),
    ('"pu_a"', "zA"),
    ('"grid"', "zG"),
    ('"edit_mode"', "zM"),
    ('"surface"', "zS"),
    ('"line"', "zL"),
    ('"lineE"', "zE"),
    ('"wall"', "zW"),
    ('"cage"', "zC"),
    ('"number"', "zN"),
    ('"symbol"', "zY"),
    ('"special"', "zP"),
    ('"board"', "zB"),
    ('"command_redo"', "zR"),
    ('"command_undo"', "zU"),
    ('"command_replay"', "z8"),
    ('"numberS"', "z1"),
    ('"freeline"', "zF"),
    ('"freelineE"', "z2"),
    ('"thermo"', "zT"),
    ('"arrows"', "z3"),
    ('"direction"', "zD"),
    ('"squareframe"', "z0"),
    ('"polygon"', "z5"),
    ('"deletelineE"', "z4"),
    ('"killercages"', "z6"),
    ('"nobulbthermo"', "z7"),
    ('"__a"', "z_"),
    ("null", "zO"),
]


def inflate(text):
    padded = text + "=" * (-len(text) % 4)
    return zlib.decompress(base64.b64decode(padded), -15).decode("utf-8")


def unabbreviate(text):
    for plain, token in reversed(TABLE):
        text = text.replace(token, plain)
    return text


def unescape(field):
    """A header field's `%2C`, `%2D`, `%2E` and `%2F` read back as the comma,
    newline, ampersand and equals sign they stand for (§ 1.3)."""
    for plain, escaped in ((",", "%2C"), ("\n", "%2D"), ("&", "%2E"), ("=", "%2F")):
        field = field.replace(escaped, plain)
    return field


def parameter(url, name):
    match = re.search(rf"[?#&]{name}=([^&]*)", url)
    return match.group(1) if match else None


class Decoded:
    """A link read back: the payload's lines, the header fields, the question
    layer, the centerlist and the answer's edge strings."""

    def __init__(self, url):
        self.url = url
        self.lines = unabbreviate(inflate(parameter(url, "p"))).split("\n")
        self.header = self.lines[0].split(",")
        self.nx, self.ny, self.size = (int(v) for v in self.header[1:4])
        self.canvas = (int(self.header[7]), int(self.header[8]))
        self.center = (int(self.header[9]), int(self.header[10]))
        self.space = json.loads(self.lines[1])
        self.layer = json.loads(self.lines[3])
        self.number = {int(k): v for k, v in self.layer["number"].items()}
        self.symbol = {int(k): v for k, v in self.layer["symbol"].items()}
        self.flags = json.loads(self.lines[7])
        self.title = unescape(self.header[15]).removeprefix("Title: ")
        self.rules = unescape(self.header[18])
        deltas = json.loads(self.lines[5])
        self.centerlist = [deltas[0]]
        for step in deltas[1:]:
            self.centerlist.append(self.centerlist[-1] + step)
        answer = parameter(url, "a")
        self.answer = json.loads(inflate(answer)) if answer else None

    @property
    def grid_style(self):
        """The grid line's three settings, read from payload line 2 only
        when asked for: a published link may be shorter than the encoder's."""
        return json.loads(self.lines[2].split("~")[0])

    @property
    def mode(self):
        """The `mode` object, payload line 11, read when asked for."""
        return json.loads(self.lines[11])

    @property
    def nx0(self):
        return self.nx + 4

    def xy(self, index):
        """Padded (x, y) of a cell-centre index; the first real cell is 2, 2."""
        return index % self.nx0, index // self.nx0


def edges_of(decoded, strips):
    """The answer's edges as ((r, c), (r2, c2)), counted from the grid's
    first cell, which sits `strips` cells in from the board's corner."""
    edges = set()
    for entry in decoded.answer[1]:
        a, b, style = entry.split(",")
        assert style == "1", entry
        (xa, ya), (xb, yb) = decoded.xy(int(a)), decoded.xy(int(b))
        g = 2 + strips
        edges.add(tuple(sorted(((ya - g, xa - g), (yb - g, xb - g)))))
    return frozenset(edges)


def numbers_of(decoded, strips, rows, cols):
    """(per row, per column) lists of the outside numbers as written: for
    each strip from the outside in, the number beside the grid, None where
    the cell holds none. A row reads the strips that are columns of numbers,
    a column the strips that are rows."""
    g = 2 + strips

    def num(x, y):
        cell = decoded.number.get(x + y * decoded.nx0)
        return int(cell[0]) if cell and cell[0].isdigit() else None

    by_row = [[num(2 + j, g + r) for j in range(strips)] for r in range(rows)]
    by_col = [[num(g + c, 2 + j) for j in range(strips)] for c in range(cols)]
    return by_row, by_col
