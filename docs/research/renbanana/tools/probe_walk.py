"""Plateau walk across shadeable grids, to find out if the inverted pipeline's
output is diverse or inbred.

`INVERSION.md` established that one symmetry move off a known-good grid lands
on another shadeable grid about 3% of the time, against 0 in 200 for uniform
random grids -- roughly 25x cheaper per candidate than the shading-first hunt.
That saving is only worth having if the grids it produces are actually new. A
walk that never leaves its parent's neighbourhood would be cheap and useless.

So: start at a grid we know is legal, propose one symmetry move at a time, and
step onto any neighbour that is still shadeable. Every accepted step is written
out as a candidate, verified from the rules by `renbanana_verify`, with the
distance back to the grid it started from recorded on it.

    uv run --with ortools docs/research/renbanana/tools/probe_walk.py \
        --source docs/research/renbanana/candidates/cand_00.json \
        --budget 900 --out docs/research/renbanana/walk

One worker per process. The driver decides how many processes run at once, and
that is what has to stay inside the core budget (AGENTS.md).
"""

import argparse
import contextlib
import json
import random
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import canon
import renbanana_cpsat as rc
import renbanana_verify as rv
from probe_inverted import CELLS, N, Shadings
from probe_neighbourhood import perturb

MIN_DISTANCE = 12  # the pool's own rule for "different enough"

# Row and column swaps inside a band move the shading by a cell or three, which
# is how ten hours of walking produced only recolourings: every grid it found
# sat 0 to 3 cells from one already held. Band and stack swaps move twenty-seven
# cells of context at once, so they carry the weight here; the small moves stay
# in the mix because they are what refines a grid once the walk is somewhere
# new, and digit swaps stay because they sometimes bridge to it.
MOVES = ("bands", "bands", "stacks", "stacks", "rows", "cols", "digits")


def hamming(a, b):
    return sum(a[p] != b[p] for p in CELLS)


def hamming_rows(a, b):
    return sum(
        x != y for ra, rb in zip(a, b, strict=True) for x, y in zip(ra, rb, strict=True)
    )


def rows_of(grid):
    return ["".join(str(grid[r, c]) for c in range(N)) for r in range(N)]


def shading_rows(is_choc):
    return ["".join("C" if is_choc[r, c] else "b" for c in range(N)) for r in range(N)]


def circled_targets(grid, is_choc, want):
    """How many chocolate rectangles of a wanted shape carry their own circle.

    A circle holds its group's size, so a 2x3 is circled when one of its six
    cells holds a 6. This is the quantity the targeted walk climbs: diversity
    alone lets a step throw a circled 2x3 away for nothing, which is why 55
    walked grids produced none.
    """
    n = 0
    for g in rv.components(is_choc, True):
        rows, cols = rv.shape(g)
        if tuple(sorted((rows, cols))) not in want:
            continue
        r0, c0 = min(g)
        # Only the cells the #377 catalogue says can carry a circle at this box
        # offset are worth testing -- it enumerated them, so re-deriving which
        # cell of a 2x3 could hold a 6 would be doing the work twice.
        sites = rc.circle_cells_at(rows, cols, r0 % 3, c0 % 3)
        if any(grid[r0 + dr, c0 + dc] == len(g) for dr, dc in sites):
            n += 1
    return n


def small_bananas(is_choc, cap):
    """Banana groups holding at most `cap` cells.

    A renban of k cells holds the run [m, m+k-1], so a group of 5 or more
    always contains its own size whatever its digits -- its circle is forced
    and tells a solver nothing. Informative banana circles live in the small
    groups, and a grid whose bananas are all large barely presses its digits at
    all: the run is nearly the whole of 1..9 and says little about any one
    cell. So more small groups is a better puzzle, not just a different one.
    """
    return sum(1 for g in rv.components(is_choc, False) if len(g) <= cap)


def parse_want(text):
    out = set()
    for bit in text.split(","):
        bit = bit.strip()
        if not bit:
            continue
        a, b = (int(x) for x in bit.lower().split("x"))
        out.add(tuple(sorted((a, b))))
    return out


def shapes_of(is_choc):
    return sorted("x".join(map(str, rv.shape(g))) for g in rv.components(is_choc, True))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", type=Path, required=True)
    ap.add_argument("--budget", type=float, default=900.0, help="wall seconds")
    ap.add_argument("--seconds", type=float, default=20.0, help="per shading solve")
    ap.add_argument("--workers", type=int, default=1)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument(
        "--refresh",
        type=float,
        default=60.0,
        help="seconds between re-reads of the shared key set",
    )
    ap.add_argument(
        "--want",
        default="",
        help="shapes whose circled count the walk climbs, e.g. 2x2,2x3",
    )
    ap.add_argument(
        "--climb",
        choices=("circled", "small", "both"),
        default="circled",
        help="what the walk hill-climbs: circled wanted shapes, small banana "
        "groups, or both with circles ranked first",
    )
    ap.add_argument(
        "--small-max",
        type=int,
        default=4,
        help="a banana group this size or under counts as small",
    )
    ap.add_argument(
        "--floor",
        type=int,
        default=0,
        help="record only steps holding at least this many circled wanted shapes",
    )
    ap.add_argument(
        "--patience",
        type=int,
        default=40,
        help="consecutive dead moves before jumping out of a spent neighbourhood",
    )
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()

    a.out.mkdir(parents=True, exist_ok=True)
    origin, origin_shading, _ = rv.load(a.source)
    name = f"{a.source.parent.name}_{a.source.stem}"
    rng = random.Random(a.seed)

    # Never solve a grid twice. Legality survives every rotation and
    # reflection, so a grid whose image we have already tested tells us nothing
    # new -- and the pool's own grids are, by definition, already found.
    #
    # The set is shared. A dozen walkers drifting from nearby seeds land on each
    # other's grids constantly, and a walker that only reads the pool at startup
    # is blind to every find its siblings make while it runs. Each appends its
    # keys to its own file in a shared directory and re-reads the lot on a
    # timer: append-only, one writer per file, so no locking is needed.
    shared = a.out / "keys"
    shared.mkdir(parents=True, exist_ok=True)
    mine = shared / f"{name}.keys"
    mine_legal = shared / f"{name}.legal"

    pool_paths = sorted(Path("docs/research/renbanana").glob("candidates*/cand_*.json"))
    pool = [rv.load(p) for p in pool_paths]
    seen = {canon.key_grid(g) for g, _, _ in pool}
    # Tested and *legal* is a different set from merely tested. A grid we have
    # already shaded is nothing new to record, but it is still a legal place to
    # stand, so the walk may step onto it for free and carry on from there.
    # Without that, a walker parks the moment its own neighbourhood is spent --
    # one spun through 1.7 million instant skips in a quarter of an hour.
    legal = set(seen)
    held = len(seen)

    # What counts as worth recording: the pool's own diversity rule, applied
    # here so the walk stops writing rows the converter would only discard.
    known = [(shading_rows(is_choc), shapes_of(is_choc)) for _, is_choc, _ in pool]

    def refresh():
        for path in sorted(shared.glob("*.keys")):
            if path != mine:
                # a sibling mid-write; the next pass picks it up
                with contextlib.suppress(OSError):
                    seen.update(path.read_text().split())
        for path in sorted(shared.glob("*.legal")):
            if path != mine_legal:
                with contextlib.suppress(OSError):
                    found_keys = path.read_text().split()
                    seen.update(found_keys)
                    legal.update(found_keys)

    want = parse_want(a.want)

    def score_of(grid, is_choc):
        """One number to climb. Circles outrank small groups by a factor no
        realistic count of small groups can bridge, so a run climbing both
        never trades a circle away for bananas."""
        n = 0
        if a.climb in ("circled", "both") and want:
            n += 100 * circled_targets(grid, is_choc, want)
        if a.climb in ("small", "both"):
            n += small_bananas(is_choc, a.small_max)
        return n

    score_here = score_of(origin, origin_shading)

    here = origin
    found = tries = skipped = dull = kicks = downhill = 0
    stuck = 0
    deadline = time.monotonic() + a.budget
    next_refresh = time.monotonic() + a.refresh
    log = a.out / f"{name}.jsonl"

    while time.monotonic() < deadline:
        if time.monotonic() >= next_refresh:
            refresh()
            next_refresh = time.monotonic() + a.refresh
        if stuck >= a.patience:
            # Every move from here has been tried. Jump: a run of moves taken
            # without testing any of them, which lands somewhere far enough out
            # to have untested neighbours again.
            for _ in range(rng.randint(3, 8)):
                here = perturb(here, rng)
            stuck = 0
            kicks += 1
        # Row and column swaps move the shading; a digit swap moves 18 grid
        # cells and usually none, so it is in the mix for reach, not for yield.
        candidate = perturb(here, rng, MOVES)
        tries += 1
        k = canon.key_grid(candidate)
        if k in seen:
            skipped += 1
            stuck += 1
            if k in legal:  # already shaded once; still a legal place to stand
                here = candidate
                stuck = 0
            continue
        seen.add(k)
        stuck = 0
        with mine.open("a") as f:
            f.write(k + "\n")
        model = Shadings(candidate)
        _, is_choc = model.solve(
            min(a.seconds, deadline - time.monotonic()), a.workers, tries
        )
        if is_choc is None:
            continue
        bad = rv.check(candidate, is_choc)
        if bad:
            print(f"{name}: REJECTED an illegal shading: {bad[0]}", flush=True)
            continue
        # Climb, when there is something to climb. A move that loses a circled
        # wanted shape is a step backwards, and the walk refuses it rather than
        # drifting off the feature it was sent to find; equal scores are still
        # taken, so it can cross a plateau.
        score_new = score_of(candidate, is_choc)
        circ_new = circled_targets(candidate, is_choc, want) if want else 0
        if score_new < score_here:
            downhill += 1
            continue

        # Every legal shading gets written, without exception.
        #
        # This used to filter first and write second, to keep the file free of
        # rows the converter would discard anyway. That threw away 107 legal
        # grids across one overnight run and left nothing on disk to show for
        # 22,452 solves. The trade was backwards: a line of JSONL is free and
        # can be re-judged forever, a solve costs seconds and cannot be
        # recovered. Whether a grid is worth keeping is the converter's
        # decision, made once, downstream, where the threshold can change
        # without re-running the search.
        here = candidate
        score_here = score_new
        legal.add(k)
        with mine_legal.open("a") as f:
            f.write(k + "\n")
        rows_new = shading_rows(is_choc)
        shapes_new = shapes_of(is_choc)
        novel = circ_new >= a.floor and all(
            hamming_rows(rows_new, s) >= MIN_DISTANCE or shapes_new != sh
            for s, sh in known
        )
        if novel:
            known.append((rows_new, shapes_new))
            found += 1
        else:
            dull += 1
        row = {
            "source": str(a.source),
            "step": found,
            "novel_when_found": novel,
            "tries": tries,
            "grid": rows_of(candidate),
            "shading": shading_rows(is_choc),
            "shapes": shapes_of(is_choc),
            "grid_distance_from_origin": hamming(candidate, origin),
            "shading_distance_from_origin": hamming(is_choc, origin_shading),
            "chocolate": sum(is_choc.values()),
            "circled_wanted": circ_new,
            "small_bananas": small_bananas(is_choc, a.small_max),
            "score": score_new,
        }
        with log.open("a") as f:
            f.write(json.dumps(row) + "\n")
        print(
            f"{name}: {'step' if novel else 'kept (not novel)'} "
            f"{found} after {tries} tries — "
            f"grid {row['grid_distance_from_origin']} cells from origin, "
            f"shading {row['shading_distance_from_origin']}"
            + f", circled {circ_new}, small bananas {row['small_bananas']}",
            flush=True,
        )

    print(
        f"{name}: DONE {found + dull} legal shadings written "
        f"({found} novel, {dull} not) in {tries} tries, "
        f"{skipped} skipped as already tested, {downhill} refused as "
        f"downhill, {kicks} kicks (pool held {held})",
        flush=True,
    )


if __name__ == "__main__":
    main()
