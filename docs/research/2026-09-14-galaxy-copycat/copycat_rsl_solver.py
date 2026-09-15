"""CP-SAT checker for Copycat cells + Copycat Region Sum Lines.

Rules modelled
- Normal sudoku.
- Nine copycat cells, one per row, column and box, with nine different
  digits. A copycat's VALUE is the digit in the cell 180 degrees opposite
  (about the grid centre); every other cell's value is its digit.
- Region sum lines on values: within a line, each maximal run of consecutive
  cells in one box sums to the same total.
- Copycat line pairs: the two lines of a pair hold the same multiset of
  values.

Setup file (JSON). Cells are "r1c1".."r9c9".
{
  "lines": {"A": ["r1c3", "r1c4", ...], "B": [...]},
  "pairs": [["A", "B"]],
  "givens": {"r5c5": 5},            # digits
  "value_givens": {"r1c3": 8},      # values (what a line sees)
  "sums": {"A": 8},                 # a line's segment sum
  "copycats": ["r3c3"],             # cells known to be copycats
  "not_copycats": ["r1c1"]          # cells known not to be
}
Every key except "lines" is optional.

A SudokuMaker link (or a file holding one) works in place of the JSON:
its region sum lines (type 404) become lines L1, L2, ... in board order and
its givens become digits. Pairs then come from --pair L1,L2 (repeatable) or
--all-share (every line holds the same multiset); --sum L1=8 fixes a sum.
Decoding goes through gridfind's link_file.py, never a local decoder.

Usage: uv run copycat_rsl_solver.py setup.json|link|link.txt [--pair A,B]...
       [--all-share] [--sum L=n]... [--limit K] [--workers N]
Reports the number of solutions found (up to K, default 2), the first
solution with copycats starred, each line's values and sum, and, when the
enumeration finished below K, every fact forced across all solutions.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections import defaultdict
from itertools import pairwise
from pathlib import Path

from ortools.sat.python import cp_model

CELL_RE = re.compile(r"^r([1-9])c([1-9])$")


def parse_cell(name: str) -> tuple[int, int]:
    m = CELL_RE.match(name)
    if not m:
        raise SystemExit(f"bad cell name {name!r}")
    return int(m.group(1)) - 1, int(m.group(2)) - 1


def box_of(r: int, c: int) -> int:
    return (r // 3) * 3 + c // 3


def segments(cells: list[tuple[int, int]]) -> list[list[tuple[int, int]]]:
    segs: list[list[tuple[int, int]]] = []
    for cell in cells:
        if segs and box_of(*segs[-1][-1]) == box_of(*cell):
            segs[-1].append(cell)
        else:
            segs.append([cell])
    return segs


def check_line(name: str, cells: list[tuple[int, int]]) -> None:
    if len(set(cells)) != len(cells):
        raise SystemExit(f"line {name} repeats a cell")
    for (r1, c1), (r2, c2) in pairwise(cells):
        if max(abs(r1 - r2), abs(c1 - c2)) != 1:
            raise SystemExit(
                f"line {name}: r{r1 + 1}c{c1 + 1} and r{r2 + 1}c{c2 + 1} not adjacent"
            )


class Collector(cp_model.CpSolverSolutionCallback):
    def __init__(self, digit, cc, limit: int) -> None:
        super().__init__()
        self.digit, self.cc, self.limit = digit, cc, limit
        self.solutions: list[tuple[list[list[int]], list[list[bool]]]] = []

    def on_solution_callback(self) -> None:
        d = [[self.Value(self.digit[r][c]) for c in range(9)] for r in range(9)]
        k = [[bool(self.Value(self.cc[r][c])) for c in range(9)] for r in range(9)]
        self.solutions.append((d, k))
        if len(self.solutions) >= self.limit:
            self.StopSearch()


def value_of(d: list[list[int]], k: list[list[bool]], r: int, c: int) -> int:
    return d[8 - r][8 - c] if k[r][c] else d[r][c]


def build(setup: dict, relax: set[str] | None = None):
    """relax: 'distinct' drops nine-different-digits, 'rowcol' drops one-per-row/col."""
    relax = relax or set()
    m = cp_model.CpModel()
    digit = [[m.NewIntVar(1, 9, f"d{r}{c}") for c in range(9)] for r in range(9)]
    cc = [[m.NewBoolVar(f"k{r}{c}") for c in range(9)] for r in range(9)]
    value = [[m.NewIntVar(1, 9, f"v{r}{c}") for c in range(9)] for r in range(9)]
    is_val = [
        [[m.NewBoolVar(f"b{r}{c}{v}") for v in range(10)] for c in range(9)]
        for r in range(9)
    ]

    for i in range(9):
        m.AddAllDifferent([digit[i][c] for c in range(9)])
        m.AddAllDifferent([digit[r][i] for r in range(9)])
        m.AddAllDifferent(
            [digit[r][c] for r in range(9) for c in range(9) if box_of(r, c) == i]
        )
        if "rowcol" not in relax:
            m.AddExactlyOne([cc[i][c] for c in range(9)])
            m.AddExactlyOne([cc[r][i] for r in range(9)])
        m.AddExactlyOne(
            [cc[r][c] for r in range(9) for c in range(9) if box_of(r, c) == i]
        )

    # copycats carry nine different digits
    is_dig = [
        [[m.NewBoolVar(f"e{r}{c}{v}") for v in range(10)] for c in range(9)]
        for r in range(9)
    ]
    for r in range(9):
        for c in range(9):
            for v in range(1, 10):
                m.Add(digit[r][c] == v).OnlyEnforceIf(is_dig[r][c][v])
                m.Add(digit[r][c] != v).OnlyEnforceIf(is_dig[r][c][v].Not())
                m.Add(value[r][c] == v).OnlyEnforceIf(is_val[r][c][v])
                m.Add(value[r][c] != v).OnlyEnforceIf(is_val[r][c][v].Not())
            m.AddExactlyOne(is_dig[r][c][1:])
            m.AddExactlyOne(is_val[r][c][1:])
            m.Add(value[r][c] == digit[8 - r][8 - c]).OnlyEnforceIf(cc[r][c])
            m.Add(value[r][c] == digit[r][c]).OnlyEnforceIf(cc[r][c].Not())
    for v in range(1, 10):
        both = []
        for r in range(9):
            for c in range(9):
                b = m.NewBoolVar(f"cd{r}{c}{v}")
                m.AddBoolAnd([cc[r][c], is_dig[r][c][v]]).OnlyEnforceIf(b)
                m.AddBoolOr([cc[r][c].Not(), is_dig[r][c][v].Not()]).OnlyEnforceIf(
                    b.Not()
                )
                both.append(b)
        if "distinct" not in relax:
            m.Add(sum(both) <= 1)

    lines = {
        name: [parse_cell(x) for x in cells] for name, cells in setup["lines"].items()
    }
    sums = {}
    for name, cells in lines.items():
        check_line(name, cells)
        s = m.NewIntVar(1, 45, f"S_{name}")
        sums[name] = s
        for seg in segments(cells):
            m.Add(sum(value[r][c] for r, c in seg) == s)
        if name in setup.get("sums", {}):
            m.Add(s == int(setup["sums"][name]))
    for a, b in setup.get("pairs", []):
        if len(lines[a]) != len(lines[b]):
            raise SystemExit(f"pair {a}/{b}: lengths differ, no solution possible")
        for v in range(1, 10):
            m.Add(
                sum(is_val[r][c][v] for r, c in lines[a])
                == sum(is_val[r][c][v] for r, c in lines[b])
            )

    for cell, v in setup.get("givens", {}).items():
        r, c = parse_cell(cell)
        m.Add(digit[r][c] == int(v))
    for cell, v in setup.get("value_givens", {}).items():
        r, c = parse_cell(cell)
        m.Add(value[r][c] == int(v))
    for cell in setup.get("copycats", []):
        r, c = parse_cell(cell)
        m.Add(cc[r][c] == 1)
    for cell in setup.get("not_copycats", []):
        r, c = parse_cell(cell)
        m.Add(cc[r][c] == 0)
    return m, digit, cc, lines


GRIDFIND = Path.home() / "src" / "gridfind"


def setup_from_link(link: str) -> dict:
    """Decode a SudokuMaker link with gridfind and lift lines and givens."""
    out = subprocess.run(
        [
            "uv",
            "run",
            "--directory",
            str(GRIDFIND),
            "python",
            "scripts/link_file.py",
            "decode",
            link,
            "-",
        ],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    doc = json.loads(out)
    puzzle = doc["puzzle"]
    cells = puzzle["cells"]
    if len(cells) != 81:
        raise SystemExit(f"board has {len(cells)} cells, only 9x9 is modelled")
    setup: dict = {"lines": {}, "givens": {}}
    n = 0
    for cons in puzzle["constraints"]:
        if cons.get("type") != 404:
            continue
        for line in cons["lines"]:
            n += 1
            setup["lines"][f"L{n}"] = [f"r{i // 9 + 1}c{i % 9 + 1}" for i in line]
    for i, cell in enumerate(cells):
        if cell.get("given") and "value" in cell:
            setup["givens"][f"r{i // 9 + 1}c{i % 9 + 1}"] = cell["value"]
    return setup


def load_setup(arg: str) -> dict:
    text = arg
    if not arg.startswith("http") and Path(arg).exists():
        text = Path(arg).read_text().strip()
        if arg.endswith(".json"):
            return json.loads(text)
    if text.startswith("http"):
        return setup_from_link(text)
    return json.loads(text)


def candidates(m, digit, cc, lines, workers: int):
    """Feasibility-test each cell digit and copycat flag; print pencilmarks.
    Returns (cands, ccs): per-cell digit sets and copycat-flag sets, or None."""
    solver = cp_model.CpSolver()
    solver.parameters.num_search_workers = workers
    solver.parameters.max_time_in_seconds = 60
    base = solver.Solve(m)
    if base not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        print("INFEASIBLE: nothing to test")
        return None
    seed_d = [[solver.Value(digit[r][c]) for c in range(9)] for r in range(9)]
    seed_k = [[solver.Value(cc[r][c]) for c in range(9)] for r in range(9)]
    cands = [[{seed_d[r][c]} for c in range(9)] for r in range(9)]
    ccs = [[{seed_k[r][c]} for c in range(9)] for r in range(9)]
    on_line = {cell for cells in lines.values() for cell in cells}
    for r in range(9):
        for c in range(9):
            for v in range(1, 10):
                if v in cands[r][c]:
                    continue
                lit = m.NewBoolVar("")
                m.Add(digit[r][c] == v).OnlyEnforceIf(lit)
                m.AddAssumption(lit)
                st = solver.Solve(m)
                m.ClearAssumptions()
                if st in (cp_model.OPTIMAL, cp_model.FEASIBLE):
                    for rr in range(9):
                        for cc_ in range(9):
                            cands[rr][cc_].add(solver.Value(digit[rr][cc_]))
                            ccs[rr][cc_].add(solver.Value(cc[rr][cc_]))
            for flag in (0, 1):
                if flag in ccs[r][c]:
                    continue
                m.AddAssumption(cc[r][c] if flag else cc[r][c].Not())
                st = solver.Solve(m)
                m.ClearAssumptions()
                if st in (cp_model.OPTIMAL, cp_model.FEASIBLE):
                    for rr in range(9):
                        for cc_ in range(9):
                            cands[rr][cc_].add(solver.Value(digit[rr][cc_]))
                            ccs[rr][cc_].add(solver.Value(cc[rr][cc_]))
    print(
        "candidates (digits; * = may be copycat, ! = must be copycat, line cells in [ ]):"
    )
    for r in range(9):
        row = []
        for c in range(9):
            s = "".join(str(v) for v in sorted(cands[r][c]))
            mark = "!" if ccs[r][c] == {1} else ("*" if 1 in ccs[r][c] else "")
            cell = f"{s}{mark}"
            cell = f"[{cell}]" if (r, c) in on_line else cell
            row.append(f"{cell:>12}")
        print(
            " ".join(row[0:3]) + " |" + " ".join(row[3:6]) + " |" + " ".join(row[6:9])
        )
        if r in (2, 5):
            print("-" * 120)
    never = sum(1 for r in range(9) for c in range(9) if ccs[r][c] == {0})
    print(f"cells that can never be a copycat: {never} of 81")
    return cands, ccs


def forced_setup(cands, ccs) -> dict:
    """The exact forced facts as setup keys, to seed later searches."""
    out: dict = {"givens": {}, "copycats": [], "not_copycats": []}
    for r in range(9):
        for c in range(9):
            cell = f"r{r + 1}c{c + 1}"
            if len(cands[r][c]) == 1:
                out["givens"][cell] = next(iter(cands[r][c]))
            if ccs[r][c] == {1}:
                out["copycats"].append(cell)
            elif ccs[r][c] == {0}:
                out["not_copycats"].append(cell)
    return out


def show_grid(d, k) -> str:
    rows = []
    for r in range(9):
        cells = [f"{d[r][c]}{'*' if k[r][c] else ' '}" for c in range(9)]
        rows.append(
            " ".join(cells[0:3])
            + " | "
            + " ".join(cells[3:6])
            + " | "
            + " ".join(cells[6:9])
        )
        if r in (2, 5):
            rows.append("---------+-----------+---------")
    return "\n".join(rows)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("setup")
    ap.add_argument("--limit", type=int, default=2)
    ap.add_argument("--workers", type=int, default=1)
    ap.add_argument("--time", type=float, default=600.0)
    ap.add_argument("--pair", action="append", default=[], help="A,B")
    ap.add_argument("--all-share", action="store_true")
    ap.add_argument("--sum", action="append", default=[], help="L=n")
    ap.add_argument(
        "--relax", action="append", default=[], help="distinct|rowcol (debug)"
    )
    ap.add_argument(
        "--candidates",
        action="store_true",
        help="test every cell digit and copycat flag; print the pencilmark grid",
    )
    ap.add_argument(
        "--forced-out",
        help="with --candidates: write the forced digits/flags as setup keys (JSON)",
    )
    args = ap.parse_args()
    setup = load_setup(args.setup)
    setup.setdefault("pairs", [])
    setup.setdefault("sums", {})
    for spec in args.pair:
        setup["pairs"].append(spec.split(","))
    if args.all_share:
        names = list(setup["lines"])
        setup["pairs"].extend([names[0], other] for other in names[1:])
    for spec in args.sum:
        name, n = spec.split("=")
        setup["sums"][name] = int(n)
    print(
        "lines: " + "; ".join(f"{k} {'-'.join(v)}" for k, v in setup["lines"].items())
    )
    print(
        f"pairs: {setup['pairs'] or 'none'}  sums: {setup['sums'] or 'none'}  givens: {len(setup.get('givens', {}))}"
    )
    m, digit, cc, lines = build(setup, set(args.relax))

    if args.candidates:
        res = candidates(m, digit, cc, lines, args.workers)
        if res and args.forced_out:
            forced = forced_setup(*res)
            Path(args.forced_out).write_text(json.dumps(forced, indent=1) + "\n")
            print(
                f"forced: {len(forced['givens'])} digits, {len(forced['copycats'])} copycats, "
                f"{len(forced['not_copycats'])} non-copycats -> {args.forced_out}"
            )
        return

    solver = cp_model.CpSolver()
    solver.parameters.num_search_workers = args.workers
    solver.parameters.enumerate_all_solutions = True
    solver.parameters.max_time_in_seconds = args.time
    col = Collector(digit, cc, args.limit)
    status = solver.Solve(m, col)
    sols = col.solutions
    name = solver.StatusName(status)
    if not sols:
        print(
            f"{name}: no solution found"
            + (" (timed out, undecided)" if status == cp_model.UNKNOWN else "")
        )
        sys.exit(1)
    complete = len(sols) < args.limit and status == cp_model.OPTIMAL
    print(
        f"solutions: {len(sols)}{'' if complete else f' (stopped at limit {args.limit})' if len(sols) >= args.limit else ' (timed out, count incomplete)'}"
    )
    d, k = sols[0]
    print("\nfirst solution (copycat = *):")
    print(show_grid(d, k))
    for lname, cells in lines.items():
        vals = [value_of(d, k, r, c) for r, c in cells]
        segs = segments(cells)
        seg_str = " | ".join(
            ",".join(str(value_of(d, k, r, c)) for r, c in seg) for seg in segs
        )
        print(f"line {lname}: sum {sum(vals) // len(segs)}  values {seg_str}")

    if complete and len(sols) > 1:
        print("\nforced across all solutions:")
        cands = defaultdict(set)
        ccset = defaultdict(set)
        for d, k in sols:
            for r in range(9):
                for c in range(9):
                    cands[r, c].add(d[r][c])
                    ccset[r, c].add(k[r][c])
        fixed = [
            f"r{r + 1}c{c + 1}={next(iter(s))}"
            for (r, c), s in sorted(cands.items())
            if len(s) == 1
        ]
        print("  digits: " + (" ".join(fixed) if fixed else "none"))
        yes = [
            f"r{r + 1}c{c + 1}" for (r, c), s in sorted(ccset.items()) if s == {True}
        ]
        no = [
            f"r{r + 1}c{c + 1}" for (r, c), s in sorted(ccset.items()) if s == {False}
        ]
        print("  copycats forced: " + (" ".join(yes) if yes else "none"))
        print(f"  cells never copycat: {len(no)} of 81")
        for lname, cells in lines.items():
            ss = {
                sum(value_of(d, k, r, c) for r, c in cells) // len(segments(cells))
                for d, k in sols
            }
            print(f"  line {lname} sums: {sorted(ss)}")


if __name__ == "__main__":
    main()
