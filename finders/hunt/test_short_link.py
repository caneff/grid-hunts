import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import short_link
from sudoku_kit.link_codec import SHORT_LINK, encode_link

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

short_link.shorten_link = lambda link: (_ for _ in ()).throw(
    AssertionError("the network was reached")
)
try:
    with short_link.fake_mint() as tmp:
        assert os.environ[short_link.FAKE_DIR_ENV] == tmp
        link = short_link.mint(DOC)
        assert SHORT_LINK.fullmatch(link), link
        assert short_link.mint(DOC) == link
        assert short_link.mint(OTHER) != link
        assert short_link.fake_doc(tmp, link) == DOC
finally:
    short_link.shorten_link = real
assert short_link.FAKE_DIR_ENV not in os.environ

print("ok")
