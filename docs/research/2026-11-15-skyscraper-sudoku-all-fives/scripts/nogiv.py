"""SCRATCH: each board in page_boards.json with its inside givens removed; every line of its grid that reads the clue value is shown (bx: its box number). Count solutions up to CAP. Run from the custom-constraints checkout with --project ~/src/grid-hunts."""
import sys, json, re, time
sys.path.insert(0, "examples/skyscraper"); sys.path.insert(0, "examples/_shared")
from build_size import add_visibility, sky
from ortools.sat.python import cp_model
from sudoku_kit import cpsat
N = 9; CAP = 20

D = {"boards": json.load(open(sys.argv[1]))}
def line(t):
    i = int(t[1:-1]) - 1
    seq = [(i, c) for c in range(N)] if t[0] == "r" else [(r, i) for r in range(N)]
    return seq[::-1] if t[-1] in "RB" else seq
ALL = [s + str(i) + e for i in range(1, 10) for s, ends in (("r", "LR"), ("c", "TB")) for e in ends]
def boxnum(t):
    i = int(t[1:-1]) - 1; s = t[-1]
    band, stack = (i // 3, 0 if s == "L" else 2) if t[0] == "r" else (0 if s == "T" else 2, i // 3)
    return band * 3 + stack + 1
class Cnt(cp_model.CpSolverSolutionCallback):
    def __init__(s): super().__init__(); s.n = 0
    def on_solution_callback(s):
        s.n += 1
        if s.n >= CAP: s.StopSearch()
for b in D["boards"]:
    g = {(r, c): int(b["grid"][r * 9 + c]) for r in range(N) for c in range(N)}
    want = (lambda t: boxnum(t)) if b["v"] == "bx" else (lambda t, v={"k": 5, "7J": 7}.get(b["v"], b["v"]): v)
    lay = [t for t in ALL if sky([g[p] for p in line(t)], None, None) == want(t)]
    regs = ([[(r, c) for r in range(N) for c in range(N) if b["reg"][r * 9 + c] == k] for k in "ABCDEFGHI"] if "reg" in b else cpsat.boxes(N, 3, 3))
    m, x = cpsat.sudoku_model(N, regs)
    for t in lay: add_visibility(m, x, line(t), want(t), N, t, None)
    s = cp_model.CpSolver(); s.parameters.enumerate_all_solutions = True; s.parameters.num_workers = 1; s.parameters.max_time_in_seconds = 60
    cb = Cnt(); t0 = time.time(); st = s.Solve(m, cb)
    n = f"{cb.n}" if st == cp_model.OPTIMAL else f">={cb.n}"
    print(f"{b['id']:10} v={b['v']:3} clues {len(lay):2} solutions {n} {s.StatusName(st)} {time.time()-t0:.0f}s", flush=True)
