"""Minting a SudokuMaker short link from a document (#90).

grid-hunts keeps no full link (`AGENTS.md` § Puzzle links): a writer calls
`mint(doc)` and writes the `https://sudokumaker.app/p/<id>` it returns.

A test keeps off the network inside `with fake_mint() as fake_dir:`, which
sets `FAKE_DIR_ENV` (subprocesses inherit it) to a directory: `mint` then answers an id fixed by the document and keeps the
full link in `<dir>/<id>.txt`, and `fake_doc(dir, short)` rebuilds the
document from it.
"""

import contextlib
import hashlib
import os
import tempfile
from pathlib import Path

from sudoku_kit.link_codec import decode_puzzle, encode_link, shorten_link

FAKE_DIR_ENV = "GRID_HUNTS_FAKE_MINT_DIR"
FAKE_PREFIX = "https://sudokumaker.app/p/"


def mint(doc):
    """The short link of the SudokuMaker document `doc`."""
    full = encode_link(doc)
    fake = os.environ.get(FAKE_DIR_ENV)
    if not fake:
        return shorten_link(full)
    link_id = "fake" + hashlib.sha1(full.encode()).hexdigest()[:12]
    (Path(fake) / f"{link_id}.txt").write_text(full + "\n")
    return FAKE_PREFIX + link_id


def fake_doc(fake_dir, short):
    """The document behind a short link `mint` made offline into `fake_dir`."""
    assert short.startswith(FAKE_PREFIX), short
    full = (Path(fake_dir) / f"{short[len(FAKE_PREFIX) :]}.txt").read_text().strip()
    return decode_puzzle(full)


@contextlib.contextmanager
def fake_mint():
    """Offline minting for the block: yields the directory `fake_doc` reads."""
    with tempfile.TemporaryDirectory() as fake_dir:
        before = os.environ.get(FAKE_DIR_ENV)
        os.environ[FAKE_DIR_ENV] = fake_dir
        try:
            yield fake_dir
        finally:
            if before is None:
                del os.environ[FAKE_DIR_ENV]
            else:
                os.environ[FAKE_DIR_ENV] = before
