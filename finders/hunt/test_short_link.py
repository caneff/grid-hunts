"""`short_link.mint` (#90): a SudokuMaker document in, a short link out.

- Live, it hands `shorten_link` the document's full link and returns what
  it answers.
- With `GRID_HUNTS_FAKE_MINT_DIR` set (the way a subprocess test keeps off
  the network), it mints `https://sudokumaker.app/p/<id>` offline, the id
  fixed by the document, and keeps the full link in that directory so the
  test can rebuild the document with `fake_doc`.

    uv run finders/hunt/test_short_link.py
"""

import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import short_link
from sudoku_kit.link_codec import encode_link

DOC = {
    "formatVersion": "1.6.0",
    "puzzle": {
        "name": "",
        "author": "",
        "type": "custom",
        "width": 2,
        "height": 2,
        "minDigit": 1,
        "maxDigit": 2,
        "cells": [{"value": 1}, {}, {}, {"value": 2}],
        "constraints": [],
    },
}
OTHER = {**DOC, "puzzle": {**DOC["puzzle"], "cells": [{}, {}, {}, {}]}}

# Live: the full link goes to shorten_link, its answer comes back.
os.environ.pop(short_link.FAKE_DIR_ENV, None)
sent = []
real = short_link.shorten_link
short_link.shorten_link = lambda link: (
    sent.append(link) or "https://sudokumaker.app/p/abc"
)
try:
    assert short_link.mint(DOC) == "https://sudokumaker.app/p/abc"
finally:
    short_link.shorten_link = real
assert sent == [encode_link(DOC)], sent

# Offline: a short link, stable per document, and the document comes back.
short_link.shorten_link = lambda link: (_ for _ in ()).throw(
    AssertionError("the network was reached")
)
try:
    with short_link.fake_mint() as tmp:
        assert os.environ[short_link.FAKE_DIR_ENV] == tmp
        link = short_link.mint(DOC)
        assert re.fullmatch(r"https://sudokumaker\.app/p/[A-Za-z0-9_-]+", link), link
        assert short_link.mint(DOC) == link
        assert short_link.mint(OTHER) != link
        assert short_link.fake_doc(tmp, link) == DOC
finally:
    short_link.shorten_link = real
assert short_link.FAKE_DIR_ENV not in os.environ

print("ok")
