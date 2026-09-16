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

DEFAULT_WORKERS = 3


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

    `workers` is set by the driver from `--workers` (default `DEFAULT_WORKERS`)
    before the first seed runs (#488) -- a finder that solves with CP-SAT
    reads `self.workers` for its own solver's worker count, so a hunt
    started without `--workers` still leaves cores for the rest of the box.
    """

    symmetry: Any = D4
    workers: int = DEFAULT_WORKERS

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

    # Optional -- a finder with no expensive cuts to remember skips both.
    # The driver calls `save_state` after every seed and `load_state` once,
    # before a resumed hunt's first seed, round-tripping through state.json
    # (#487) so a resumed hunt doesn't relearn what it already knew.

    def save_state(self) -> Any:
        """JSON-serialisable state to persist to state.json."""
        ...

    def load_state(self, state: Any) -> None:
        """Restore state a prior run's `save_state` wrote."""
        ...

    # Optional -- `hunt verify DIR` (#489) needs a candidate to hand
    # `verify`, not the JSON `record()` wrote. A finder whose record() *is*
    # already verify-able skips this; `hunt verify` then hands `verify` the
    # parsed record line unchanged.

    def candidate_from_record(self, record: dict) -> Any:
        """Rebuild the candidate `verify` can check from a line `record()`
        wrote to examples.jsonl."""
        ...

    # Optional -- a finder with no picture to draw skips this. The driver
    # calls `render` right after an accepted example is written, and saves
    # the returned image to renders/<seed>.png (#490). Build the image with
    # `render.GridCanvas`.

    def render(self, candidate: Any):
        """A picture of this candidate (a `PIL.Image.Image`), or omit this
        method entirely for a finder with nothing to draw."""
        ...
