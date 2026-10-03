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


class Empty(NamedTuple):
    """What `Finder.propose` may return in place of None when a seed found
    nothing and can say why (#491) -- a solver's timeout and its proof of
    infeasibility mean opposite things. The driver writes the reason to
    that seed's progress event as `empty_reason`. The reason is required:
    a seed with nothing to say returns None."""

    reason: str


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

    `config` is the finder's own knobs, JSON-serialisable (#491), the flags it
    parses itself and the driver's argv does not name. Optional: the driver
    reads it with `getattr(finder, "config", None)`, run.json records it, and a
    resume under a different config refuses.
    """

    symmetry: Any = D4
    workers: int = DEFAULT_WORKERS
    config: Any = None

    def propose(self, rng) -> Any | None:
        """One candidate for this seed's rng, or None (or `Empty(reason)`)
        if this seed found nothing."""
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
    #
    # A stateful finder (has `load_state`) that also has `render` needs this
    # hook, and `save_state`, for render repair on resume (#538); without
    # them a failed render stays missing and a stray render is never deleted.

    def candidate_from_record(self, record: dict) -> Any:
        """Rebuild the candidate, as `propose` produced it, from a line
        `record()` wrote to examples.jsonl: everything `verify` *and*
        `render` read, not only what `verify` reads. The driver does not
        check that. It should not change the finder's state, and the driver
        snapshots the state before the call and restores it after, so a
        hook that does never reaches state.json."""
        ...

    # Optional -- a finder with no picture to draw skips this. The driver
    # calls `render` right after an accepted example is written, and saves
    # the returned image to renders/<seed>.png (#490). Build the image with
    # `render.GridCanvas`. On resume the driver re-renders a missing or
    # undecodable picture (#537, #538): a stateless finder is re-proposed; a
    # stateful one is never re-proposed -- its picture is rebuilt from the
    # examples.jsonl record with `candidate_from_record` (above).

    def render(self, candidate: Any):
        """A picture of this candidate (a `PIL.Image.Image`), or omit this
        method entirely for a finder with nothing to draw."""
        ...
