"""A candidate-carrying human solver for copycat + paired region-sum lines.

State: per cell a candidate set for its own digit, a copycat status in
{P, C, ?}, and for line cells a set of allowed shown options (kind, value).
Propagation (not counted as rungs): naked and hidden singles, locked
candidates (pointing / claiming), one copycat per house, copycat digits
distinct (pigeonhole, and naked subsets over the boxes' copycat-digit
sets), a plain cell never holds its box's copycat digit, line-cell
candidate sync, and each line pruned by exact enumeration of its shown
options (distinct plain digits in a shared house, one copycat per house,
equal run sums where runs are contiguous box runs, a digit confined to the
line inside a house must sit on it).  A rung is one argument on one pair:
equal line totals, or one digit's count equal on both lines.  Every
elimination is checked against the known solution when one is given.
"""

import json
import sys
from collections import defaultdict
from itertools import combinations
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from copycat_rsl_solver import parse_cell

BOARDS_DIR = "docs/research/2026-09-14-galaxy-copycat/boards"


def idx(c):
    r, cc = parse_cell(c)
    return r * 9 + cc


def nm(i):
    return f"r{i // 9 + 1}c{i % 9 + 1}"


def box(i):
    return (i // 9 // 3) * 3 + (i % 9) // 3


HOUSES = (
    [[r * 9 + c for c in range(9)] for r in range(9)]
    + [[r * 9 + c for r in range(9)] for c in range(9)]
    + [
        [(b // 3 * 3 + k // 3) * 9 + (b % 3 * 3 + k % 3) for k in range(9)]
        for b in range(9)
    ]
)
PEERS = [set().union(*[set(h) for h in HOUSES if i in h]) - {i} for i in range(81)]


def same_house(a, b):
    return a // 9 == b // 9 or a % 9 == b % 9 or box(a) == box(b)


class Unsound(Exception):
    pass


class Human:
    def __init__(self, lines, pairs, forced, sol=None, cc_sol=None, locked=True):
        self.lines = {k: [idx(c) for c in v] for k, v in lines.items()}
        self.pairs = pairs
        self.cand = [set(range(1, 10)) for _ in range(81)]
        self.cc = ["?"] * 81
        self.opts = {}  # line cell -> allowed shown options
        self.sol = sol
        self.ccsol = set(cc_sol) if cc_sol else None
        self.locked = locked
        for c, d in forced["givens"].items():
            self.cand[idx(c)] = {d}
        for c in forced["copycats"]:
            self.cc[idx(c)] = "C"
        for c in forced["not_copycats"]:
            self.cc[idx(c)] = "P"
        for line_cells in self.lines.values():
            for i in line_cells:
                self.opts[i] = None
        self.log = []
        self.ccdig = {}

    # ---- soundness
    def check(self):
        if self.sol is None:
            return
        for i in range(81):
            if self.sol[i] not in self.cand[i]:
                raise Unsound(f"{nm(i)} lost {self.sol[i]}")
            truth = "C" if i in self.ccsol else "P"
            if self.cc[i] not in ("?", truth):
                raise Unsound(f"{nm(i)} cc {self.cc[i]} vs {truth}")
            if i in self.opts and self.opts[i] is not None:
                o = (truth, self.sol[80 - i] if truth == "C" else self.sol[i])
                if o not in self.opts[i]:
                    raise Unsound(f"{nm(i)} lost option {o}")

    # ---- option view of a line cell
    def options(self, i):
        o = set()
        ccd = self.ccdig.get(box(i), set())
        if self.cc[i] != "C":
            o |= {("P", d) for d in self.cand[i] if not (len(ccd) == 1 and d in ccd)}
        if self.cc[i] != "P":
            o |= {("C", d) for d in self.cand[80 - i]}
        if self.opts.get(i) is not None:
            o &= self.opts[i]
        return o

    def restrict(self, i, allowed):
        """apply allowed option set to cell i; return True if something changed"""
        cur = self.options(i)
        new = cur & allowed
        if new == cur:
            return False
        if not new:
            raise Unsound(f"{nm(i)} no options")
        self.opts[i] = new
        if not any(k == "P" for k, _ in new):
            self.set_cc(i, "C")
        if not any(k == "C" for k, _ in new):
            self.set_cc(i, "P")
        if self.cc[i] == "P":
            self.cand[i] &= {d for k, d in new if k == "P"} or self.cand[i]
        if self.cc[i] == "C":
            self.cand[80 - i] &= {d for k, d in new if k == "C"} or self.cand[80 - i]
        return True

    def set_cc(self, i, v):
        if self.cc[i] == v:
            return
        if self.cc[i] != "?":
            raise Unsound(f"{nm(i)} cc conflict")
        self.cc[i] = v

    # ---- propagation
    def propagate(self):
        changed = True
        loops = 0
        while changed:
            changed = False
            loops += 1
            if loops > 200:
                raise RuntimeError("propagate did not converge")
            # naked singles
            for i in range(81):
                if len(self.cand[i]) == 1:
                    d = next(iter(self.cand[i]))
                    for j in PEERS[i]:
                        if d in self.cand[j]:
                            self.cand[j].discard(d)
                            changed = True
                        if not self.cand[j]:
                            raise Unsound(f"{nm(j)} empty")
            # hidden singles + locked candidates
            for h in HOUSES:
                for d in range(1, 10):
                    cells = [i for i in h if d in self.cand[i]]
                    if not cells:
                        raise Unsound(f"digit {d} gone from house")
                    if len(cells) == 1 and len(self.cand[cells[0]]) > 1:
                        self.cand[cells[0]] = {d}
                        changed = True
                    elif self.locked and 1 < len(cells) <= 3:
                        for h2 in HOUSES:
                            if h2 is h or not all(i in h2 for i in cells):
                                continue
                            for j in h2:
                                if j not in cells and d in self.cand[j]:
                                    self.cand[j].discard(d)
                                    changed = True
            # copycat: one per house
            for h in HOUSES:
                cc_cells = [i for i in h if self.cc[i] == "C"]
                q_cells = [i for i in h if self.cc[i] == "?"]
                if len(cc_cells) > 1:
                    raise Unsound("two copycats in a house")
                if cc_cells and q_cells:
                    for i in q_cells:
                        self.cc[i] = "P"
                        changed = True
                if not cc_cells and len(q_cells) == 1:
                    self.cc[q_cells[0]] = "C"
                    changed = True
                if not cc_cells and not q_cells:
                    raise Unsound("house without copycat")
            # copycat digits distinct
            cs = [i for i in range(81) if self.cc[i] == "C"]
            for i in cs:
                if len(self.cand[i]) == 1:
                    d = next(iter(self.cand[i]))
                    for j in cs:
                        if j != i and d in self.cand[j]:
                            self.cand[j].discard(d)
                            changed = True
            # copycat digit pigeonhole: nine copycats, nine different digits
            self.ccdig = {}
            for b in range(9):
                cells = [i for i in HOUSES[18 + b] if self.cc[i] != "P"]
                self.ccdig[b] = (
                    set().union(*[self.cand[i] for i in cells]) if cells else set()
                )
            for d in range(1, 10):
                boxes = [b for b in range(9) if d in self.ccdig[b]]
                if not boxes:
                    raise Unsound(f"no box can copycat digit {d}")
                if len(boxes) == 1:
                    b = boxes[0]
                    for i in HOUSES[18 + b]:
                        if self.cc[i] != "P" and d not in self.cand[i]:
                            self.cc[i] = "P"
                            changed = True
                        if self.cc[i] == "C" and self.cand[i] != {d}:
                            self.cand[i] = {d}
                            changed = True
                        if d in self.cand[i] and self.cc[i] == "P":
                            self.cand[i].discard(d)
                            changed = True
                    self.ccdig[b] = {d}
            # naked subsets among the boxes' copycat-digit sets
            for k in (1, 2, 3, 4):
                for bs in combinations(range(9), k):
                    u = set().union(*[self.ccdig[b] for b in bs])
                    if len(u) == k:
                        for b2 in range(9):
                            if b2 in bs or not (self.ccdig[b2] & u):
                                continue
                            self.ccdig[b2] -= u
                            for i in HOUSES[18 + b2]:
                                if self.cc[i] == "C" and self.cand[i] & u:
                                    self.cand[i] -= u
                                    changed = True
                                if self.cc[i] == "?" and not (self.cand[i] - u):
                                    self.cc[i] = "P"
                                    changed = True
            for b in range(9):
                if len(self.ccdig[b]) == 1:
                    d = next(iter(self.ccdig[b]))
                    for b2 in range(9):
                        if b2 != b and d in self.ccdig[b2]:
                            self.ccdig[b2].discard(d)
                            for i in HOUSES[18 + b2]:
                                if self.cc[i] == "C":
                                    self.cand[i].discard(d)
            # sync line-cell candidates with their surviving shown options
            for i in self.opts:
                o = self.options(i)
                if self.cc[i] == "P":
                    keep = {d for k, d in o if k == "P"}
                    if keep and self.cand[i] - keep:
                        self.cand[i] &= keep
                        changed = True
                if self.cc[i] == "C":
                    keep = {d for k, d in o if k == "C"}
                    if keep and self.cand[80 - i] - keep:
                        self.cand[80 - i] &= keep
                        changed = True
            # each line pruned by its own sums
            for k, line_cells in self.lines.items():
                t = self.line_tables(line_cells)
                if t["n"] == 0:
                    raise Unsound(f"line {k} impossible")
                for i in line_cells:
                    if self.restrict(i, t["used"][i]):
                        changed = True
            self.check()

    def line_tables(self, cells):
        opts = {i: self.options(i) for i in cells}
        runs = []  # contiguous box runs
        for k, i in enumerate(cells):
            if runs and box(cells[k - 1]) == box(i):
                runs[-1].append(k)
            else:
                runs.append([k])
        conf = [
            [j for j in range(k) if same_house(cells[k], cells[j])]
            for k in range(len(cells))
        ]
        ol = [sorted(opts[i]) for i in cells]
        # digits confined to the line inside a house: some line cell there
        # holds them
        line_set = set(cells)
        need = []
        for h in HOUSES:
            if not line_set & set(h):
                continue
            for d in range(1, 10):
                hit = [i for i in h if d in self.cand[i]]
                if hit and all(i in line_set for i in hit):
                    need.append((d, [cells.index(i) for i in hit]))
        used = {i: set() for i in cells}
        cnt = set()
        sums = set()
        oc = defaultdict(lambda: defaultdict(set))
        osum = defaultdict(set)
        n = 0

        def rec(k, cur):
            nonlocal n
            if k == len(cells):
                vals = [o[1] for o in cur]
                ss = {sum(vals[j] for j in r) for r in runs}
                if len(ss) > 1:
                    return
                for d, ks in need:
                    if not any(
                        cur[kk] == ("P", d)
                        or (
                            cur[kk][0] == "C"
                            and d in self.cand[cells[kk]]
                            and d in self.ccdig.get(box(cells[kk]), set(range(1, 10)))
                        )
                        for kk in ks
                    ):
                        return
                n += 1
                s = ss.pop() * len(runs)
                c = tuple(sum(1 for v in vals if v == d) for d in range(1, 10))
                cnt.add(c)
                sums.add(s)
                for kk, o in enumerate(cur):
                    used[cells[kk]].add(o)
                    key = (cells[kk], *o)
                    osum[key].add(s)
                    for d in range(9):
                        oc[key][d].add(c[d])
                return
            for o in ol[k]:
                ok = True
                for j in conf[k]:
                    if o[0] == "P" and cur[j][0] == "P" and cur[j][1] == o[1]:
                        ok = False
                        break
                    if o[0] == "C" and cur[j][0] == "C":
                        ok = False
                        break
                if ok:
                    cur.append(o)
                    rec(k + 1, cur)
                    cur.pop()

        rec(0, [])
        return {"n": n, "used": used, "cnt": cnt, "sums": sums, "oc": oc, "osum": osum}

    # ---- rungs
    def arguments(self):
        """all (pair, argument, eliminations) currently available"""
        res = []
        for line_a, line_b in self.pairs:
            t_a = self.line_tables(self.lines[line_a])
            t_b = self.line_tables(self.lines[line_b])
            for a in ["sum"] + [f"{d}s" for d in range(1, 10)]:
                el = set()
                if a == "sum":
                    ok = t_a["sums"] & t_b["sums"]
                    for t in (t_a, t_b):
                        for key, ss in t["osum"].items():
                            if not ss & ok:
                                el.add(key)
                else:
                    d = int(a[0]) - 1
                    ok = {c[d] for c in t_a["cnt"]} & {c[d] for c in t_b["cnt"]}
                    for t in (t_a, t_b):
                        for key, cs in t["oc"].items():
                            if not cs[d] & ok:
                                el.add(key)
                if el:
                    res.append((line_a + line_b, a, el))
        return res

    def apply(self, el):
        by = defaultdict(set)
        for i, k, d in el:
            by[i].add((k, d))
        for i, s in by.items():
            self.restrict(i, self.options(i) - s)
        self.check()

    def solved(self):
        return all(len(c) == 1 for c in self.cand) and all(x != "?" for x in self.cc)

    def placed(self):
        return (
            sum(1 for c in self.cand if len(c) == 1),
            sum(1 for x in self.cc if x == "C"),
        )

    def run(self, verbose=False):
        self.propagate()
        while not self.solved():
            args = self.arguments()
            if not args:
                break
            pick = max(args, key=lambda t: len(t[2]))
            elims = sorted(f"{nm(i)}{k}{d}" for i, k, d in pick[2])
            if verbose:
                print("  trying", pick[0], pick[1], elims)
            self.apply(pick[2])
            self.propagate()
            self.log.append(
                {
                    "pair": pick[0],
                    "arg": pick[1],
                    "elims": elims,
                    "placed": self.placed(),
                }
            )
            if verbose:
                print(
                    pick[0],
                    pick[1],
                    len(pick[2]),
                    "elims ->",
                    self.placed(),
                    "placed",
                    elims,
                )
        return self


def load_board(path):
    j = json.loads(Path(path).read_text())
    return j["lines"], j["pairs"]


def solution_for(lines):
    """digits + copycats from the full board-14 residual set"""
    import numpy as np
    import residual

    f = residual.load(".scratch/copycat-rsl/b14-residual.npz")
    m = np.ones(f.n, bool)
    for line_cells in lines.values():
        m &= f.line_mask(line_cells)
    return f, m


def seed_from_link(h, path):
    """Center marks -> cell candidates; corner marks -> the digit is confined to
    the marked cells of that box; colour 4096 -> plain, 8192 -> copycat."""
    j = json.loads(Path(path).read_text())
    cells = j["puzzle"]["cells"]
    corner = defaultdict(set)
    for i, c in enumerate(cells):
        v = c.get("value")
        if v:
            h.cand[i] = {int(v)}
            continue
        b = c.get("candidates", 0) or 0
        s = {d for d in range(1, 10) if b >> d & 1}
        if s:
            h.cand[i] &= s
        pm = c.get("cornerPencilMarks", 0) or 0
        for d in range(1, 10):
            if pm >> d & 1:
                corner[(box(i), d)].add(i)
        col = c.get("colors")
        if col == 4096:
            h.set_cc(i, "P")
        if col == 8192:
            h.set_cc(i, "C")
    for (b, d), cs in corner.items():
        for i in HOUSES[18 + b]:
            if i not in cs:
                h.cand[i].discard(d)
    h.check()


def batch(
    seed,
    src=f"{BOARDS_DIR}/board14-pair7.unique-dedup.jsonl",
    dst=".scratch/copycat-rsl/p7/human_batch.jsonl",
):
    """Scratch-only: needs `.scratch/copycat-rsl/b14-residual.npz` for the
    solution check, so this stays outside `just test`/`just check-full`."""
    import numpy as np
    import residual

    f = residual.load(".scratch/copycat-rsl/b14-residual.npz")
    base = json.loads(Path(f"{BOARDS_DIR}/board25-pair7-relaxed.json").read_text())
    forced = json.loads(Path(f"{BOARDS_DIR}/board14-forced.json").read_text())
    rows = [json.loads(line) for line in Path(src).read_text().splitlines()]
    with Path(dst).open("w") as out:
        for n, r in enumerate(rows):
            lines = dict(base["lines"])
            lines["L5"] = r["X"].split("-")
            lines["L6"] = r["Y"].split("-")
            m = np.ones(f.n, bool)
            for line_cells in lines.values():
                m &= f.line_mask(line_cells)
            for a, b in base["pairs"]:
                m &= f.pair_mask(lines[a], lines[b])
            assert m.sum() == 1
            sol = [int(d) for d in f.digits[m][0]]
            ccs = [int(i) for i in np.where(f.flags[m][0])[0]]
            h = Human(lines, base["pairs"], forced, sol, ccs)
            try:
                if seed and seed != "-":
                    seed_from_link(h, seed)
                h.run()
                rec = {
                    "X": r["X"],
                    "Y": r["Y"],
                    "solved": h.solved(),
                    "placed": h.placed(),
                    "rungs": len(h.log),
                    "ladder": [
                        (log["pair"], log["arg"], len(log["elims"]), log["placed"])
                        for log in h.log
                    ],
                }
            except Exception as e:
                rec = {"X": r["X"], "Y": r["Y"], "error": repr(e)}
            out.write(json.dumps(rec) + "\n")
            out.flush()
            print(
                n, rec.get("placed"), rec.get("rungs"), rec.get("error", ""), flush=True
            )


def bifurcations(h):
    """For every open fact, assume it and run; report contradictions (the
    negation is then proven) and full solves."""
    import copy

    res = []

    def trial(label, fn):
        g = copy.deepcopy(h)
        g.sol = None
        try:
            fn(g)
            g.run()
            res.append((label, "solved" if g.solved() else f"placed {g.placed()}"))
        except (Unsound, RuntimeError):
            res.append((label, "CONTRADICTION -> negation proven"))

    for i in range(81):
        if h.cc[i] == "?":
            trial(f"{nm(i)} is the copycat", lambda g, i=i: g.set_cc(i, "C"))
            trial(f"{nm(i)} is plain", lambda g, i=i: g.set_cc(i, "P"))
        if 1 < len(h.cand[i]) <= 3:
            for d in sorted(h.cand[i]):

                def f(g, i=i, d=d):
                    g.cand[i] = {d}

                trial(f"{nm(i)}={d}", f)
    return res


if __name__ == "__main__":
    import numpy as np

    if sys.argv[1] == "batch":
        batch(sys.argv[2] if len(sys.argv) > 2 else None, *sys.argv[3:])
        sys.exit()
    board_lines, board_pairs = load_board(sys.argv[1])
    forced_facts = json.loads(Path(f"{BOARDS_DIR}/board14-forced.json").read_text())
    residual_f, residual_m = solution_for(board_lines)
    for line_a, line_b in board_pairs:
        residual_m &= residual_f.pair_mask(board_lines[line_a], board_lines[line_b])
    assert residual_m.sum() == 1, residual_m.sum()
    solution = [int(d) for d in residual_f.digits[residual_m][0]]
    copycats = [int(i) for i in np.where(residual_f.flags[residual_m][0])[0]]
    human = Human(
        board_lines,
        board_pairs,
        forced_facts,
        solution,
        copycats,
        locked="--no-locked" not in sys.argv,
    )
    if "--seed" in sys.argv:
        seed_from_link(human, sys.argv[sys.argv.index("--seed") + 1])
    human.run(verbose=True)
    print(
        "solved" if human.solved() else "STUCK",
        "placed",
        human.placed(),
        "rungs",
        len(human.log),
    )
    if not human.solved():
        for k, line_cells in human.lines.items():
            print(
                k,
                [(nm(i), sorted(human.cand[i]), human.cc[i]) for i in line_cells],
            )
