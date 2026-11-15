"""SCRATCH: re-check every all-5s find on the repo model and build a link per puzzle.
sky5_all.py <scratch dir>   reads <dir>/sky7_list.json, writes link files + sky7_built.json"""
import json, sys, pathlib
sys.path.insert(0, "."); sys.path.insert(0, "../_shared")
from build_size import SPEC, sky, add_visibility
from lanes import RingGlobal
from board import load_board
from sudoku_kit import cpsat
S = pathlib.Path(sys.argv[1]); N = 9
def line(t):
    i = int(t[1:-1]) - 1
    seq = [(i, c) for c in range(N)] if t[0] == "r" else [(r, i) for r in range(N)]
    return seq[::-1] if t[-1] in "RB" else seq
out = []
for P in json.loads((S / "sky7_list.json").read_text()):
    G = [[int(ch) for ch in r] for r in P["grid"].split()]; OUT = P["outside"].split()
    g = {(r, c): G[r][c] for r in range(N) for c in range(N)}
    assert all(sky([g[p] for p in line(t)], None, None) == 7 for t in OUT), P["id"]
    m, x = cpsat.sudoku_model(N, cpsat.boxes(N, 3, 3))
    for p, v in g.items():
        if v == 7: m.Add(x[p] == 7)
    for t in OUT: add_visibility(m, x, line(t), 7, N, t, None)
    first, uniq = cpsat.solve_unique(m, x, 60)
    ok = first is not None and uniq
    clue = {}
    for i in range(N):
        row = G[i]; col = [G[r][i] for r in range(N)]
        clue[f"L{i}"] = sky(row, None, None); clue[f"R{i}"] = sky(row[::-1], None, None)
        clue[f"T{i}"] = sky(col, None, None); clue[f"B{i}"] = sky(col[::-1], None, None)
    gen = {"seed": 0, "n": 9, "box": [3, 3], "grid": G, "clue": clue,
           "active": sorted(t[-1] + str(int(t[1:-1]) - 1) for t in OUT),
           "givens": {f"{r},{c}": 7 for r in range(N) for c in range(N) if G[r][c] == 7}}
    gp = S / f"sky7_{P['id']}_gen.json"; gp.write_text(json.dumps(gen))
    link, _ = RingGlobal(SPEC).encode(load_board(gp))
    lp = S / f"sky7_{P['id']}_link.txt"; lp.write_text(link + "\n")
    out.append({**P, "unique_repo_model": bool(ok), "link_file": str(lp)})
    print(P["id"], "unique" if ok else "NOT UNIQUE", flush=True)
(S / "sky7_built.json").write_text(json.dumps(out, indent=1))
