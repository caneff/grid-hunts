"""SCRATCH: more 16-outside-5 unique Skyscraper Sudokus, most clumped first.
Score = edge boxes that are the first box of >=2 clues; was: clues whose first cell is in the top-left box (r1L-r3L, c1T-c3T); by symmetry any corner box is the same.
Found layouts are banned with all 8 dihedral images.  sky5b.py <maxfound> [cap]"""
import sys, time, importlib.util
from ortools.sat.python import cp_model
sp = importlib.util.spec_from_file_location("s", sys.argv[0].replace("sky5d.py", "sky5lib.py")); L = importlib.util.module_from_spec(sp); sp.loader.exec_module(L)
N, cells, LINES, NAMES = L.N, L.cells, L.LINES, L.NAMES

def pairs():
    ps = []
    for s in "LRTB":
        for i in range(1, N):
            a = f"r{i}{s}" if s in "LR" else f"c{i}{s}"
            b = f"r{i+1}{s}" if s in "LR" else f"c{i+1}{s}"
            ps.append((a, b))
    ps += [("r1L", "c1T"), ("r1R", "c9T"), ("r9L", "c1B"), ("r9R", "c9B")]
    return ps
PAIRS = pairs()
def firstbox(t):
    i = int(t[1:-1]) - 1; s = t[-1]
    if t[0] == "r": return (i // 3, 0 if s == "L" else 2)
    return (0 if s == "T" else 2, i // 3)
BOXES = sorted({firstbox(t) for t in NAMES})
def score(lay): return sum(sum(firstbox(t) == b for t in lay) >= 2 for b in BOXES)

def T(t):  # transpose
    k, i, s = t[0], t[1:-1], t[-1]
    return {"r": "c", "c": "r"}[k] + i + {"L": "T", "T": "L", "R": "B", "B": "R"}[s]
def H(t):  # mirror columns
    k, i, s = t[0], int(t[1:-1]), t[-1]
    return f"r{i}{ {'L':'R','R':'L'}[s] }" if k == "r" else f"c{N+1-i}{s}"
def images(lay):
    out, frontier = set(), [frozenset(lay)]
    while frontier:
        x = frontier.pop()
        if x in out: continue
        out.add(x); frontier += [frozenset(map(T, x)), frozenset(map(H, x))]
    return out

if __name__ == "__main__":
    MAXF = int(sys.argv[1]); CAP = float(sys.argv[2]) if len(sys.argv) > 2 else 3000
    m, x = L.model()
    oc = {t: m.NewBoolVar(t) for t in NAMES}
    for t in NAMES:
        m.Add(L.vis_expr(m, x, LINES[t], t) == 5).OnlyEnforceIf(oc[t])
    five = {p: m.NewBoolVar("") for p in cells}
    for p in cells:
        m.Add(x[p] == 5).OnlyEnforceIf(five[p]); m.Add(x[p] != 5).OnlyEnforceIf(five[p].Not())
    m.Add(sum(oc.values()) == 16)
    hb = []
    for b in BOXES:
        v = m.NewBoolVar(""); m.Add(sum(oc[t] for t in NAMES if firstbox(t) == b) >= 2).OnlyEnforceIf(v); hb.append(v)
    m.Maximize(sum(hb))
    t0 = time.time(); found = 0; it = 0
    while time.time() - t0 < CAP and found < MAXF:
        it += 1
        s = L.solver(600); st = s.Solve(m)
        if st not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            print("master", s.StatusName(st), f"{time.time()-t0:.0f}s", flush=True); break
        G = {p: s.Value(x[p]) for p in cells}; lay = [t for t in NAMES if s.Value(oc[t])]
        st2, G2 = L.second(G, lay)
        print(f"it {it} clump {score(lay)} ({s.StatusName(st)}) second {st2} {time.time()-t0:.0f}s", flush=True)
        if st2 == "INFEASIBLE":
            found += 1
            print(f"FOUND {found} clump {score(lay)}")
            print("  grid   ", " ".join("".join(str(G[(r, c)]) for c in range(N)) for r in range(N)))
            print("  outside", " ".join(lay), flush=True)
            for im in images(lay):
                m.AddBoolOr([oc[t].Not() if t in im else oc[t] for t in NAMES])
            continue
        if G2 is None:
            print("check timeout", flush=True); break
        alts = [oc[t] for t in NAMES if L.sky([G2[p] for p in LINES[t]]) != 5]
        alts += [five[p] for p in cells if G2[p] != 5]
        eq = m.NewBoolVar("")
        for p in cells: m.Add(x[p] == G2[p]).OnlyEnforceIf(eq)
        m.AddBoolOr(alts + [eq])
    else:
        print("done or time cap", flush=True)
