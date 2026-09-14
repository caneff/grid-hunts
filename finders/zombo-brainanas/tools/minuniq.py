"""Minimal clue set (irreducible, greedy) that makes one found fill the unique solution, using only circles, white dots
and black dots, no givens, no negative constraint on dots. r9c7, r9c9 and the opener white dot r4c6-r5c6 are always kept.
usage: minuniq.py <found name> [limit] Dots are stripped first with every circle kept, then circles. -> hunt/minuniq/<name>.json + PROGRESS.md"""
import sys, os, json, time
sys.path.insert(0, "/home/caneff/orca/workspaces/sudokumaker-custom-constraints/tang/docs/research")
import zombo_brainanas_cpsat as zb
Z = os.path.dirname(os.path.abspath(__file__)) + "/"
OUT = Z + "hunt/minuniq/"; os.makedirs(OUT, exist_ok=True)
F = "/home/caneff/orca/workspaces/sudokumaker-custom-constraints/tang/docs/research/zombo-brainanas/found/"
name = sys.argv[1]; tag = ("_nb" if os.environ.get("NO_BLACK") else "") + "".join("_" + c for c in os.environ.get("KEEP", "").split()); limit = int(sys.argv[2]) if len(sys.argv) > 2 else 120
zb.WORKERS = int(os.environ.get("ZB_WORKERS", zb.WORKERS)); zb.BIG_POCKET_CELLS = None  # any pocket may carry a circle
d = json.load(open(F + name + ".json"))
sol = {(r, c): int(d["grid"][r][c]) for r in range(9) for c in range(9)}
shade = {(r, c): int(d["infected"][r][c] == "*") for r in range(9) for c in range(9)}
A, B, OPEN = (8, 6), (8, 8), ((3, 5), (4, 5))
if os.environ.get("SECOND"):  # the second box-9 circle, e.g. SECOND=r7c9 (default r9c9)
    B = (int(os.environ["SECOND"][1]) - 1, int(os.environ["SECOND"][3]) - 1)
if os.environ.get("OPENER"):  # the opener white dot, e.g. OPENER=r5c5-r5c6 (default r4c6-r5c6)
    a, b = os.environ["OPENER"].split("-"); OPEN = ((int(a[1]) - 1, int(a[3]) - 1), (int(b[1]) - 1, int(b[3]) - 1))
items = {}
for p in zb.circle_candidates(sol, shade): items[("c", p)] = 1
for p in zb.CELLS:
    for q in zb.nb(p):
        if q < p: continue
        if not shade[p] and not shade[q] and abs(sol[p] - sol[q]) == 1: items[("w", p, q)] = 1
        if shade[p] != shade[q]:
            i, u = (p, q) if shade[p] else (q, p)
            if sol[u] == 2 * sol[i]: items[("b", p, q)] = 1
if os.environ.get("NO_BLACK"):  # circles + white dots only
    items = {k: v for k, v in items.items() if k[0] != "b"}
keep = {("c", A), ("c", B), ("w", *OPEN)}
for cell in os.environ.get("KEEP", "").split():  # extra circles to keep, e.g. KEEP=r6c8
    keep.add(("c", (int(cell[1]) - 1, int(cell[3]) - 1)))
assert keep <= set(items), "opener or box-9 circles missing on this fill"
def log(line): open(OUT + "PROGRESS.md", "a").write(f"{name}{tag}: {line}\n")
def fmt(k): return (f"r{k[1][0]+1}c{k[1][1]+1}" if k[0] == "c" else f"{'white' if k[0]=='w' else 'black'} r{k[1][0]+1}c{k[1][1]+1}-r{k[2][0]+1}c{k[2][1]+1}")
_build = zb.build
current = {}
def build(*a, **k):
    m, x, inf = _build(*a, **k)
    for key in current:
        if key[0] == "w":
            p, q = key[1], key[2]; m.Add(inf[p] == 0); m.Add(inf[q] == 0); e = m.NewBoolVar("")
            m.Add(x[p] - x[q] == 1).OnlyEnforceIf(e); m.Add(x[q] - x[p] == 1).OnlyEnforceIf(e.Not())
        elif key[0] == "b":
            p, q = key[1], key[2]; m.Add(inf[p] != inf[q])
            m.Add(x[q] == 2 * x[p]).OnlyEnforceIf(inf[p]); m.Add(x[p] == 2 * x[q]).OnlyEnforceIf(inf[q])
    return m, x, inf
zb.build = build
cuts = []
tests = [0]
def test(trial):
    global current
    current = trial; tests[0] += 1
    circles = {k[1]: None for k in trial if k[0] == "c"}
    t = time.time()
    try:
        other = zb.solve_valid(circles=circles, cuts=cuts, exclude=[sol], limit=limit)
    except TimeoutError:
        log(f"  test {tests[0]} ({len(trial)} clues): timeout, keep ({time.time()-t:.0f}s)"); return False
    log(f"  test {tests[0]} ({len(trial)} clues): {'UNIQUE' if other is None else 'second solution'} ({time.time()-t:.0f}s)")
    return other is None
log(f"start: {len(items)} candidate clues ({sum(k[0]=='c' for k in items)} circles, {sum(k[0]=='w' for k in items)} white, {sum(k[0]=='b' for k in items)} black)")
if not test(items):
    log("NOT UNIQUE even with every clue"); sys.exit(0)
# phase 1: strip dots while every circle stays; phase 2: strip circles
after_dots = zb.strip(items, keep | {k for k in items if k[0] == "c"}, test)
log(f"dots minimal: {sum(k[0] != 'c' for k in after_dots)} dots kept with all circles: " + ", ".join(fmt(k) for k in after_dots if k[0] != "c"))
final = zb.strip(after_dots, keep, test)
log(f"MINIMAL {len(final)} clues after {tests[0]} tests: " + ", ".join(fmt(k) for k in final))
json.dump({"fill": name, "clues": [fmt(k) for k in final], "circles": [list(k[1]) for k in final if k[0] == "c"],
           "white": [[*k[1], *k[2]] for k in final if k[0] == "w"], "black": [[*k[1], *k[2]] for k in final if k[0] == "b"]},
          open(OUT + name + tag + ".json", "w"), indent=1)
