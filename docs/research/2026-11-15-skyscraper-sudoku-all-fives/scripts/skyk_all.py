"""SCRATCH: box-numbered givens (box k shows k) + outside 5s; was: re-check every all-5s find on the repo model and build a link per puzzle.
sky5_all.py <scratch dir>   reads <dir>/skyk_list.json, writes link files + skyk_built.json"""
import json, sys, pathlib
sys.path.insert(0, "."); sys.path.insert(0, "../_shared")
from build_size import SPEC, sky, add_visibility
from lanes import RingGlobal
from board import load_board
from sudoku_kit import cpsat
S = pathlib.Path(sys.argv[1]); N = 9
def bn(r, c): return (r // 3) * 3 + c // 3 + 1
def line(t):
    i = int(t[1:-1]) - 1
    seq = [(i, c) for c in range(N)] if t[0] == "r" else [(r, i) for r in range(N)]
    return seq[::-1] if t[-1] in "RB" else seq
out = []
for P in json.loads((S / "skyk_list.json").read_text()):
    G = [[int(ch) for ch in r] for r in P["grid"].split()]; OUT = P["outside"].split()
    g = {(r, c): G[r][c] for r in range(N) for c in range(N)}
    assert all(sky([g[p] for p in line(t)], None, None) == 5 for t in OUT), P["id"]
    m, x = cpsat.sudoku_model(N, cpsat.boxes(N, 3, 3))
    for (r, c), v in g.items():
        if v == bn(r, c): m.Add(x[(r, c)] == v)
    for t in OUT: add_visibility(m, x, line(t), 5, N, t, None)
    first, uniq = cpsat.solve_unique(m, x, 60)
    ok = first is not None and uniq
    clue = {}
    for i in range(N):
        row = G[i]; col = [G[r][i] for r in range(N)]
        clue[f"L{i}"] = sky(row, None, None); clue[f"R{i}"] = sky(row[::-1], None, None)
        clue[f"T{i}"] = sky(col, None, None); clue[f"B{i}"] = sky(col[::-1], None, None)
    gen = {"seed": 0, "n": 9, "box": [3, 3], "grid": G, "clue": clue,
           "active": sorted(t[-1] + str(int(t[1:-1]) - 1) for t in OUT),
           "givens": {f"{r},{c}": G[r][c] for r in range(N) for c in range(N) if G[r][c] == bn(r, c)}}
    gp = S / f"skyk_{P['id']}_gen.json"; gp.write_text(json.dumps(gen))
    link, _ = RingGlobal(SPEC).encode(load_board(gp))
    lp = S / f"skyk_{P['id']}_link.txt"; lp.write_text(link + "\n")
    out.append({**P, "unique_repo_model": bool(ok), "link_file": str(lp)})
    print(P["id"], "unique" if ok else "NOT UNIQUE", flush=True)
(S / "skyk_built.json").write_text(json.dumps(out, indent=1))
