"""The 7-digit seeing-tie hunt on the shared hunt protocol (#491): the first
real finder built on finders/hunt/.

One seed is one CP-SAT solve of chan_big.py's model for one (hunt, QR-10
window, corner) -- the tie pair and slot pattern left as decisions, `tables`
on, the hunt's seed grid as a hint, `--q34` adding the 34-36 criterion. The
seed sets the solver's random seed. Every grid an earlier seed returned is
forbidden (the finder's state), so a later seed finds a new grid or proves
there is none. A capped solve comes back `Empty("timeout")`, a proof
`Empty("infeasible with <k> grids forbidden")`. `verify` re-reads the grid with the
oracle, never the model: sudoku, the cage's QQRR 33, the corner's QQRR 5,
the bounded cell <= 7, QR 10 at the window, a tie, and the criterion.

    uv run finders/qqrr/hunt/tie_finder.py --out DIR --seeds 0:3 \\
        --hunt r1c5 --ten r7c7 --corner bl --timeout 600 --q34
    uv run finders/qqrr/hunt/tie_finder.py verify DIR

The driver's flags (`--out`, `--seeds`, `--workers`, ...) are its own
(finders/hunt/driver.py); `--workers` is the solver's worker count.
"""

import argparse
import sys
from typing import NamedTuple

import hunt_common as hc

# isort: split
import chan_big
import checker
import oracle
from ortools.sat.python import cp_model

from examples._shared import cpsat

sys.path.insert(0, str(hc.ROOT / "finders" / "hunt"))
# isort: split
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


def grid_rows(grid):
    """The flat row-major grid as nine lists."""
    return [list(grid[r * N : (r + 1) * N]) for r in range(N)]


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

    def __init__(self, hunt=None, ten=None, corner=None, timeout=None, q34=False):
        self.config = {
            "hunt": hunt,
            "ten": ten,
            "corner": corner,
            "timeout": timeout,
            "q34": q34,
        }
        self.found = []

    def propose(self, rng):
        c = self.config
        flags = {"tables", "hint"} | ({"criteria=q34"} if c["q34"] else set())
        q, _, _ = chan_big.build(c["hunt"], c["ten"], c["corner"], flags)
        cells = {(r, col): q.x[r][col] for r in range(N) for col in range(N)}
        for i, g in enumerate(self.found):
            cpsat.forbid(
                q.m,
                cells,
                {rc: int(g[rc[0] * N + rc[1]]) for rc in cells},
                tag=f"found{i}",
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
        return Candidate(grid, c["hunt"], c["ten"], c["corner"], c["q34"])

    def verify(self, candidate):
        rows = grid_rows(candidate.grid)
        if not is_sudoku(rows):
            return Verdict(False, "not a sudoku")
        cage, target, _ = hc.HUNTS[candidate.hunt]
        pin = checker.CORNERS[candidate.corner]
        ten = chan_big.parse_ten(candidate.ten)
        ranks, _nums, cr = oracle.rank_grid(rows)
        why = []
        if cr[cage[0]][cage[1]] != 33:
            why.append(f"cage QQRR {cr[cage[0]][cage[1]]}, not 33")
        if cr[pin[0]][pin[1]] != 5:
            why.append(f"corner QQRR {cr[pin[0]][pin[1]]}, not 5")
        if rows[target[0]][target[1]] > 7:
            why.append(f"bounded cell {rows[target[0]][target[1]]} > 7")
        if ranks[ten[0]][ten[1]] != 10:
            why.append(f"QR {ranks[ten[0]][ten[1]]} at {candidate.ten}, not 10")
        if not oracle.seven_digit_ties(ranks):
            why.append("no 7-digit seeing tie")
        if candidate.q34 and not hc.q34_accept(ranks, cr):
            why.append("no clean QQRR 34-36 cell")
        return Verdict(not why, "; ".join(why))

    def record(self, candidate):
        rows = grid_rows(candidate.grid)
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
        if candidate.q34:
            rec["q34_cells"] = [
                f"r{r + 1}c{c + 1}={cr[r][c]}" for r, c in hc.q34_accept(ranks, cr)
            ]
        return rec

    def key(self, candidate):
        return candidate.grid

    def candidate_from_record(self, record):
        return Candidate(
            tuple(int(d) for d in record["grid"] if d != "/"),
            record["hunt"],
            record["ten"],
            record["corner"],
            record["q34"],
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
    return run(TieFinder(own.hunt, own.ten, own.corner, own.timeout, own.q34), rest)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
