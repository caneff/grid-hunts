"""The finder contract every hunt drives (#483/#484).

A finder states only its rule and its search; `driver.run` supplies the
output directory, dedupe and the CLI. See `finders/AGENTS.md` for the
pointer from a new finder to this package.
"""

import sys
from pathlib import Path
from typing import Any, NamedTuple, Protocol

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dedupe import D4


class Verdict(NamedTuple):
    """The result of `Finder.verify`: ok, plus why not when it isn't."""

    ok: bool
    reason: str = ""


class Finder(Protocol):
    """A finder rule: propose a candidate, verify it, say how to record it.

    `symmetry` is the group `key()`'s grid dedupes under: `dedupe.D4`,
    `dedupe.IDENTITY`, or a custom list of cell maps (see dedupe.py). A
    finder that leaves `symmetry` unset gets `dedupe.D4` from the driver --
    the common, square-board case needs no code.
    """

    symmetry: Any = D4

    def propose(self, rng) -> Any | None:
        """One candidate for this seed's rng, or None if this seed found
        nothing."""
        ...

    def verify(self, candidate: Any) -> Verdict:
        """Whether a proposed candidate actually satisfies the finder's
        rule."""
        ...

    def record(self, candidate: Any) -> dict:
        """The JSON-serialisable line written to examples.jsonl."""
        ...

    def key(self, candidate: Any) -> Any:
        """The flat tuple of cell values dedupe canonicalizes under
        `symmetry`."""
        ...
