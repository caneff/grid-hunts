"""Does grid shadeability cluster, or is every legal grid isolated?

Random solved grids are effectively never shadeable, so sampling them is not a
generator. The rescue would be local search: start from a grid we know works
and walk. That only pays if a *neighbour* of a shadeable grid is often
shadeable too. This measures exactly that.

A move is one of the sudoku symmetries that actually changes the whisper
structure -- swapping two rows inside a band, two columns inside a stack, or
relabelling two digits. (Transposing and the 10-v relabel are excluded: both
preserve every |difference|, so they map a legal grid to a legal one for free
and would only flatter the result.)

    uv run --with ortools docs/research/renbanana/tools/probe_neighbourhood.py --moves 1

One worker, one process (AGENTS.md).
"""

import argparse
import random
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import renbanana_verify as rv
from probe_inverted import CELLS, Shadings


def perturb(grid, rng, kinds=("rows", "cols", "digits")):
    """One symmetry move that can change which adjacencies are whisper-legal.

    `kinds` is drawn from with replacement, so repeating an entry weights it.
    The default is the flat three this file measured with; the walk leans on
    row and column swaps instead, because a digit swap moves 18 grid cells and
    typically no shading cells at all.
    """
    kind = rng.choice(kinds)
    if kind == "digits":
        u, v = rng.sample(range(1, 10), 2)
        swap = {u: v, v: u}
        return {p: swap.get(grid[p], grid[p]) for p in CELLS}

    if kind in ("bands", "stacks"):
        # Whole bands and stacks, not rows inside one. Swapping two rows of a
        # band leaves most of the grid's adjacencies alone, so the shading
        # re-solves within a few cells of where it was; swapping two bands
        # moves twenty-seven cells of context at once. Still a sudoku symmetry
        # -- bands map to bands, so rows, columns and boxes all survive.
        i, j = rng.sample(range(3), 2)

        def send(x):
            band, off = divmod(x, 3)
            band = j if band == i else i if band == j else band
            return band * 3 + off

        if kind == "bands":
            return {(r, c): grid[send(r), c] for r, c in CELLS}
        return {(r, c): grid[r, send(c)] for r, c in CELLS}

    band = rng.randrange(3)
    i, j = rng.sample(range(3), 2)
    a, b = band * 3 + i, band * 3 + j
    if kind == "rows":
        return {
            (r, c): grid[(b if r == a else a if r == b else r), c] for r, c in CELLS
        }
    return {(r, c): grid[r, (b if c == a else a if c == b else c)] for r, c in CELLS}


def shadeable(grid, seconds, workers, seed):
    model = Shadings(grid)
    _, is_choc = model.solve(seconds, workers, seed)
    return is_choc


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--moves", type=int, default=1, help="perturbations per sample")
    ap.add_argument("--samples", type=int, default=4, help="samples per source grid")
    ap.add_argument("--seconds", type=float, default=20.0)
    ap.add_argument("--workers", type=int, default=1)
    a = ap.parse_args()

    sources = sorted(Path("docs/research/renbanana").glob("candidates*/cand_*.json"))
    rng = random.Random(0)
    hits = tries = 0
    began = time.monotonic()
    for path in sources:
        grid, _, _ = rv.load(path)
        got = 0
        for k in range(a.samples):
            g = grid
            for _ in range(a.moves):
                g = perturb(g, rng)
            found = shadeable(g, a.seconds, a.workers, k)
            got += found is not None
            if found is not None:
                assert not rv.check(g, found), "probe returned an illegal shading"
        hits += got
        tries += a.samples
        print(
            f"{path.parent.name}/{path.name}: {got}/{a.samples} neighbours shadeable",
            flush=True,
        )
    print(
        f"\n{hits}/{tries} grids {a.moves} move(s) from a known-good one are "
        f"shadeable ({100 * hits / max(tries, 1):.0f}%); "
        f"{time.monotonic() - began:.0f}s",
        flush=True,
    )


if __name__ == "__main__":
    main()
