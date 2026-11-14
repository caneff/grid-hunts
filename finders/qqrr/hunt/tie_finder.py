"""The 7-digit seeing-tie hunt on the shared hunt protocol (#491): the first
real finder built on finders/hunt/.

One seed is one CP-SAT solve of chan_big.py's model for one (hunt, QR-10
window, corner) -- the tie pair and slot pattern left as decisions, `tables`
on, the hunt's seed grid as a hint, `--q34` adding the 34-36 criterion.
`--warm-from DIR...` (#643) swaps the seed grid for the nearest known grid: the hits
in those hunt output directories' examples.jsonl, same hunt, nearest window and
corner first, criterion-passing first (chan_big's `warm` order), never a grid the
run forbids. run.json records the grid the run started from, each example the grid
its solve was hinted with.

The seed sets the solver's random seed. Every grid an earlier seed returned is
forbidden (the finder's state), so a later seed finds a new grid or proves
there is none. A capped solve comes back `Empty("timeout")`, a proof
`Empty("infeasible with <k> grids forbidden")`. `verify` re-reads the grid with the
oracle, never the model: sudoku, the rule `hunt_common` holds (the cage's QQRR, the
corner's QQRR, the bounded cell, QR at the window), a tie, and the criterion.

    uv run finders/qqrr/hunt/tie_finder.py --out DIR --seeds 0:3 \\
        --hunt r1c5 --ten r7c7 --corner bl --timeout 600 --q34 --warm-from DIR...
    uv run finders/qqrr/hunt/tie_finder.py verify DIR

The driver's flags (`--out`, `--seeds`, `--workers`, ...) are its own
(finders/hunt/driver.py); `--workers` is the solver's worker count.
"""

import argparse
import hashlib
import re
import sys
from pathlib import Path
from typing import NamedTuple

import hunt_common as hc

# isort: split
import chan_big
import checker
import oracle
from ortools.sat.python import cp_model
from sudoku_kit import cpsat

sys.path.insert(0, str(hc.ROOT / "finders" / "hunt"))
# isort: split
import hunt_files
from dedupe import IDENTITY
from driver import run
from protocol import Empty, Verdict

N = 9


class Candidate(NamedTuple):
    """A found grid, flat row-major, with the search it answers."""

    grid: tuple
    hunt: str
    ten: str
    corner: str
    q34: bool
    warm: str = None  # the grid its solve was hinted with, when --warm-from gave one


def flat_rows(grid):
    """The flat row-major grid as nine lists."""
    return [list(grid[r * N : (r + 1) * N]) for r in range(N)]


def read_warm_hits(dirs, hunt):
    """(ten, corner, grid) for every example of `hunt` in the hunt output
    directories `dirs`, in the order read."""
    hits = []
    for d in dirs:
        path = Path(d) / "examples.jsonl"
        # The hunt-files reader: a last line cut short by a kill is dropped, any other
        # unreadable line or a missing file raises HuntFileError naming its line. Blank lines
        # do not count, so a bad example is named by its record number, not a line number.
        _, records = hunt_files.read_log(path)
        for k, rec in enumerate(records, 1):
            try:
                if rec["hunt"] == hunt:
                    ten, corner, grid = rec["ten"], rec["corner"], rec["grid"]
                    if not re.fullmatch(r"\d{9}(/\d{9}){8}", grid):
                        raise ValueError(grid)
                    hits.append((ten, corner, grid))
            except (ValueError, KeyError, TypeError, AttributeError):
                raise hunt_files.HuntFileError(
                    f"{path} record {k} is not a hunt example"
                ) from None
    return hits


def is_sudoku(rows):
    want = set(range(1, N + 1))
    cols = [[rows[r][c] for r in range(N)] for c in range(N)]
    boxes = [
        [rows[br + r][bc + c] for r in range(3) for c in range(3)]
        for br in range(0, N, 3)
        for bc in range(0, N, 3)
    ]
    return all(set(house) == want for house in (*rows, *cols, *boxes))


class TieFinder:
    # The cage, the bounded cell and the corner pin fix cells: no symmetry of
    # the board maps the search onto itself.
    symmetry = IDENTITY

    def __init__(
        self, hunt=None, ten=None, corner=None, timeout=None, q34=False, warm_dirs=None
    ):
        self.config = {
            "hunt": hunt,
            "ten": ten,
            "corner": corner,
            "timeout": timeout,
            "q34": q34,
        }
        self.found = []
        self.warm = read_warm_hits(warm_dirs, hunt) if warm_dirs else []
        if warm_dirs:
            first = self.warm_hits()
            self.config["warm_from"] = {
                "dirs": list(warm_dirs),
                "grid": first[0][2] if first else None,
                "ten": first[0][0] if first else None,
                "corner": first[0][1] if first else None,
                # the whole order, so a source edited below the top refuses a resume
                "order": hashlib.sha256(
                    "\n".join(h[2] for h in first).encode()
                ).hexdigest()[:12],
            }

    def warm_hits(self):
        """The known grids to hint from, best first: not a grid this run forbids,
        nearest window and corner first, criterion-passing first."""
        c = self.config
        forbidden = set(self.found)
        left = [h for h in self.warm if h[2].replace("/", "") not in forbidden]
        crit = ["q34"] if c["q34"] else []
        return chan_big.criterion_first(
            chan_big.nearest_first(left, c["ten"], c["corner"]), crit
        )

    def propose(self, rng):
        c = self.config
        flags = {"tables", "hint"} | ({"criteria=q34"} if c["q34"] else set())
        hits = None
        if self.warm:
            flags.add("warm")
            hits = self.warm_hits()
        q, warm_from, _ = chan_big.build(
            c["hunt"], c["ten"], c["corner"], flags, hits=hits
        )
        cells = {(r, col): q.x[r][col] for r in range(N) for col in range(N)}
        for g in self.found:
            cpsat.forbid(
                q.m,
                cells,
                {rc: int(g[rc[0] * N + rc[1]]) for rc in cells},
            )
        s = cpsat.solver(c["timeout"], reproducible=False, seed=rng.randrange(2**31))
        s.parameters.num_workers = self.workers
        res = s.Solve(q.m)
        if res == cpsat.UNKNOWN:
            return Empty("timeout")
        if res == cp_model.INFEASIBLE:
            return Empty(f"infeasible with {len(self.found)} grids forbidden")
        if res not in cpsat.SOLVED:
            raise RuntimeError(s.StatusName(res))
        grid = tuple(s.Value(q.x[r][col]) for r in range(N) for col in range(N))
        self.found.append("".join(map(str, grid)))
        warm = warm_from[2] if warm_from else None
        return Candidate(grid, c["hunt"], c["ten"], c["corner"], c["q34"], warm)

    def verify(self, candidate):
        rows = flat_rows(candidate.grid)
        if not is_sudoku(rows):
            return Verdict(False, "not a sudoku")
        cage, target, _ = hc.HUNTS[candidate.hunt]
        pin = checker.CORNERS[candidate.corner]
        ten = chan_big.parse_ten(candidate.ten)
        ranks, _nums, cr = oracle.rank_grid(rows)
        why = []
        if cr[cage[0]][cage[1]] != hc.CAGE_QQRR:
            why.append(f"cage QQRR {cr[cage[0]][cage[1]]}, not {hc.CAGE_QQRR}")
        if cr[pin[0]][pin[1]] != hc.CORNER_RANK:
            why.append(f"corner QQRR {cr[pin[0]][pin[1]]}, not {hc.CORNER_RANK}")
        if rows[target[0]][target[1]] > hc.BOUND_MAX:
            why.append(f"bounded cell {rows[target[0]][target[1]]} > {hc.BOUND_MAX}")
        if ranks[ten[0]][ten[1]] != hc.WINDOW_RANK:
            why.append(
                f"QR {ranks[ten[0]][ten[1]]} at {candidate.ten}, not {hc.WINDOW_RANK}"
            )
        if not oracle.seven_digit_ties(ranks):
            why.append("no 7-digit seeing tie")
        if candidate.q34 and not hc.q34_accept(ranks, cr):
            why.append("no clean QQRR 34-36 cell")
        return Verdict(not why, "; ".join(why))

    def record(self, candidate):
        rows = flat_rows(candidate.grid)
        ranks, _nums, cr = oracle.rank_grid(rows)
        rec = {
            "grid": hc.grid_text(rows),
            "hunt": candidate.hunt,
            "ten": candidate.ten,
            "corner": candidate.corner,
            "q34": candidate.q34,
            "ties": [
                f"r{a[0] + 1}c{a[1] + 1}=r{b[0] + 1}c{b[1] + 1} {num}"
                for a, b, num, *_ in oracle.seven_digit_ties(ranks)
            ],
        }
        if candidate.warm:
            rec["warm"] = candidate.warm
        if candidate.q34:
            rec["q34_cells"] = [
                f"r{r + 1}c{c + 1}={cr[r][c]}" for r, c in hc.q34_accept(ranks, cr)
            ]
        return rec

    def key(self, candidate):
        return candidate.grid

    def candidate_from_record(self, record):
        return Candidate(
            tuple(d for row in hc.grid_rows(record["grid"]) for d in row),
            record["hunt"],
            record["ten"],
            record["corner"],
            record["q34"],
            record.get("warm"),
        )

    def save_state(self):
        return {"found": self.found}

    def load_state(self, state):
        self.found = list(state["found"])


def main(argv):
    parser = argparse.ArgumentParser(prog="tie_finder", add_help=False)
    parser.add_argument("--hunt", choices=sorted(hc.HUNTS))
    # A window's top-left cell: rows and columns 1..8 on the 9x9 board.
    windows = [f"r{r}c{c}" for r in range(1, N) for c in range(1, N)]
    parser.add_argument("--ten", choices=windows, metavar="rXcY")
    parser.add_argument("--corner", choices=sorted(checker.CORNERS))
    parser.add_argument("--timeout", type=float)
    parser.add_argument("--q34", action="store_true")
    parser.add_argument("--warm-from", nargs="+", metavar="DIR")
    own, rest = parser.parse_known_args(argv)
    if rest[:1] == ["verify"]:
        return run(TieFinder(), rest)
    missing = [
        f"--{k}"
        for k in ("hunt", "ten", "corner", "timeout")
        if getattr(own, k) is None
    ]
    if missing:
        print(f"tie_finder: a hunt needs {' '.join(missing)}", file=sys.stderr)
        return 2
    try:
        finder = TieFinder(
            own.hunt, own.ten, own.corner, own.timeout, own.q34, own.warm_from
        )
    except hunt_files.HuntFileError as error:
        print(f"tie_finder: --warm-from: {error}", file=sys.stderr)
        return 2
    if own.warm_from and not finder.warm:
        # a warm source with nothing to hint from is the cold start, silently
        print(f"tie_finder: --warm-from holds no {own.hunt} grid", file=sys.stderr)
        return 2
    return run(finder, rest)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
