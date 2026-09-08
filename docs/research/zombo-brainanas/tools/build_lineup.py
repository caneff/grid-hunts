"""Rebuild lineup.html from the repo's found grids: DATA line spliced into lineup_template.html."""
import json, glob, os
Z = os.path.dirname(os.path.abspath(__file__))
F = "/home/caneff/orca/workspaces/sudokumaker-custom-constraints/tang/docs/research/zombo-brainanas/found"
ARM = {"bal36": "balance ≥36", "box9": "box 9", "box9_cross": "box 9 + reach", "box9_spread": "box 9 + spread",
       "dist25": "distance 25", "probe": "probe", "spread": "spread", "want2a": "two pockets", "want2b": "two pockets", "want3": "three pockets", "tpl720": "template: 720 opener"}
N = range(9); box = lambda r, c: (r // 3) * 3 + c // 3 + 1
def comps(inf, val):
    seen, out = set(), []
    for r in N:
        for c in N:
            if inf[r][c] == val and (r, c) not in seen:
                st, cur = [(r, c)], []
                seen.add((r, c))
                while st:
                    a, b = st.pop(); cur.append((a, b))
                    for q in ((a+1,b),(a-1,b),(a,b+1),(a,b-1)):
                        if 0 <= q[0] < 9 and 0 <= q[1] < 9 and inf[q[0]][q[1]] == val and q not in seen:
                            seen.add(q); st.append(q)
                out.append(cur)
    return out
rows = []
for f in sorted(glob.glob(F + "/*.json")):
    d = json.load(open(f)); name = os.path.basename(f)[:-5]
    arm, seed = name.rsplit("_", 1)
    if name.startswith("pairopt_"):  # pairopt_r7c7_r7c8_IU -> arm, seed = pair+kind
        arm, seed = "pair optimal", name[8:]
    elif name.startswith("groups_"):  # groups_5 -> the exact-count check asked for >= 5 brainanas
        arm, seed = "brainanas", "≥ " + name[7:]
    elif name.startswith("pairg5_"):  # pairg5_r7c7_r7c8_IU -> five brainanas required, circles maximized
        arm, seed = "pair, 5 brainanas", name[7:]
    elif name.startswith("x9_"):  # x9_r8c9_w3_s0 -> r9c7 uninfected + another box-9 circle infected, r9c9 != 9, 4 pockets
        arm, seed = "r9c7 + other box-9 circle", name[3:]
    elif name.startswith("pair99ring_"):  # pair99ring_UI_w3_s0_g3 -> r9c7 + r9c9, opener kropki touching the would-be green ring
        arm, seed = "r9c7 + r9c9", "ring kropki " + name[11:]
    elif name.startswith("pair99b68_"):  # pair99b68_UI_w3_s0_g3 -> r9c7 + r9c9, black dot in box 1 or 2, circle in b6 off row 6 and in b8 off col 6
        arm, seed = "r9c7 + r9c9", "b6 b8 off r6 c6 + dot b1/b2 " + name[10:]
    elif name.startswith("pair99b8d1_"):  # pair99b8d1_UI_w3_s0 -> r9c7 + r9c9, >= 2 circles in box 8, a black dot inside box 1
        arm, seed = "r9c7 + r9c9", "b8 x2 + black dot b1 " + name[11:]
    elif name.startswith("pair99"):  # every r9c7 + r9c9 hunt in one arm; the variant goes in front of the seed
        sub = {"pair99fills": "fills", "pair99digits": "digits", "pair99g4nearIU": "near IU", "pair99g4near": "near", "pair99g4": "4 pockets",
               "pair99var": "variety", "pair99free": "free", "pair99": "chocolate"}
        key = next(k for k in sub if name.startswith(k + "_"))
        arm, seed = "r9c7 + r9c9", sub[key] + " " + name[len(key) + 1:]
    elif name.startswith("pairone5_"):  # pairone5_r7c7_I -> one box-9 circle, 5 brainanas, circles + chocolate maximized
        arm, seed = "one circle, 5 brainanas", name[9:]
    elif name.startswith("pairpock_"):  # pairpock_r7c7_r7c8_IU -> every uninfected group rewarded
        arm, seed = "pair pockets", name[9:]
    elif name.startswith("pairb24_"):  # pairb24_r7c7_r7c8_IU -> chocolate in boxes 2+4 rewarded
        arm, seed = "pair boxes 2+4", name[8:]
    elif name.startswith("pair_"):  # pair_r7c7_r7c8 -> one arm, seed = the pair
        arm, seed = "pair", name[5:].replace("_", "+")
    grid, inf = d["grid"], [[ch == "*" for ch in row] for row in d["infected"]]
    circles, pockets = [], []
    for val in (True, False):
        for comp in comps(inf, val):
            hits = [p for p in comp if int(grid[p[0]][p[1]]) == len(comp)]
            circles += hits
            if not val and hits: pockets.append(len(comp))
    circles.sort()
    dots, white = [], []  # black: boundary edge, uninfected digit double the infected; white: two uninfected consecutive digits
    for r in N:
        for c in N:
            for a, b in ((r+1, c), (r, c+1)):
                if a >= 9 or b >= 9: continue
                if inf[r][c] != inf[a][b]:
                    i, u = ((r, c), (a, b)) if inf[r][c] else ((a, b), (r, c))
                    if int(grid[u[0]][u[1]]) == 2 * int(grid[i[0]][i[1]]): dots.append([r, c, a, b])
                elif not inf[r][c] and abs(int(grid[r][c]) - int(grid[a][b])) == 1:
                    white.append([r, c, a, b])
    TOUCH = {(4, 5), (4, 6), (4, 7), (4, 8), (5, 4)}  # r5c6-r5c9, r6c5: outside the 7-cell block r9c7=9 would force
    groups = len(comps(inf, False))  # every uninfected group, circled or not
    opener = [e for e in white if (e[0], e[1]) in TOUCH or (e[2], e[3]) in TOUCH]
    cross = sum(1 for r in N for c in N for a, b in ((r+1, c), (r, c+1)) if a < 9 and b < 9 and inf[r][c] and inf[a][b] and box(r, c) != box(a, b))
    rows.append(dict(id=name, arm=ARM.get(arm, arm), seed=seed, grid=grid, inf=d["infected"], circles=[list(p) for p in circles],
                     pockets=sorted(pockets), circ=len(circles), infected=sum(map(sum, inf)), dots=len(dots), dotEdges=dots, white=len(white), whiteEdges=white, cross=cross,
                     box9=sum(1 for p in circles if box(*p) == 9), opener=opener, groups=groups))
t = open(Z + "/lineup_template.html").read()
out = t.replace("const DATA=[];\n", "const DATA=" + json.dumps(rows, separators=(",", ":"), ensure_ascii=False) + ";\n", 1)
open(Z + "/lineup.html", "w").write(out); print(len(rows), "grids")
