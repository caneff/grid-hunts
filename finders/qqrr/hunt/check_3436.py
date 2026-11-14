"""Usage: check_3436.py; reads every big-*.log in $HUNT_LOGS (default .scratch/place).
Prints one line per grid found there, naming the QR-1 windows and the interior cells of
QQRR 34-36 none of whose windows shares a cell with one (`hunt_common.q34_accept`)."""

import glob

import hunt_common as hc

# isort: split
import oracle


def report(logs=None):
    """One line per grid found in `logs`' big-*.log (default $HUNT_LOGS), the first log naming it
    first: the log, the QR-1 windows, the cells that qualify, the grid."""
    logs = hc.LOGS if logs is None else logs
    seen = {}
    for p in sorted(glob.glob(str(logs / "big-*.log"))):
        for g in hc.logged_grids(p):
            seen.setdefault(g, p.split("/")[-1])
    lines = []
    for g, src in seen.items():
        grid = hc.grid_rows(g)
        ranks, _nums, cr = oracle.rank_grid(grid)
        ones = {
            (wr, wc)
            for wr in range(len(ranks))
            for wc in range(len(ranks))
            if ranks[wr][wc] == 1
        }
        clean = [f"r{r + 1}c{c + 1}" for r, c in hc.q34_accept(ranks, cr)]
        lines.append(
            " ".join(
                map(
                    str,
                    (
                        src,
                        "QR1",
                        sorted(f"r{a + 1}c{b + 1}" for a, b in ones),
                        "clean:",
                        clean,
                        "grid",
                        g,
                    ),
                )
            )
        )
    return lines


if __name__ == "__main__":
    print("\n".join(report()))
