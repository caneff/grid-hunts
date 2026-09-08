"""Template-first hunt: fix the shading of an opener region, let the solver fill the rest.

  python template.py mk found.json r7c8 r9c7 > opener.txt   # template from a hit: the circled groups + border
  python template.py run opener.txt outdir first last [limit] [min_distance]

Template: 9 rows of '#' infected, '.' uninfected, '?' free; then 'circles: r7c8 r9c7'.
A circle's digit must equal its group size (rectangle in-model, pocket by CEGAR)."""
import sys, json, glob, os, time
sys.path.insert(0, "/home/caneff/orca/workspaces/sudokumaker-custom-constraints/tang/docs/research")
import zombo_brainanas_cpsat as zb
from pathlib import Path
FOUND = "/home/caneff/orca/workspaces/sudokumaker-custom-constraints/tang/docs/research/zombo-brainanas/found/*.json"
rc = lambda s: (int(s[1]) - 1, int(s[3]) - 1)

def mk(path, cells):
    d = json.load(open(path)); shade = {p: int(d["infected"][p[0]][p[1]] == "*") for p in zb.CELLS}
    keep = set()
    for comp in zb.comps(shade, 0) + zb.comps(shade, 1):
        if any(c in comp for c in cells):
            keep |= comp | {q for p in comp for q in zb.nb(p)}
    for r in range(9):
        print("".join(("#" if shade[r, c] else ".") if (r, c) in keep else "?" for c in range(9)))
    print("circles:", " ".join(f"r{r+1}c{c+1}" for r, c in cells))

def run(tpl, outdir, first, last, limit=300, dist=6):
    lines = [l.strip() for l in open(tpl) if l.strip()]
    shade = {(r, c): 1 if ch == "#" else 0 for r, l in enumerate(lines[:9]) for c, ch in enumerate(l) if ch in "#."}
    circles = {rc(t): None for t in lines[9].split()[1:]} if len(lines) > 9 else {}
    out = Path(outdir); out.mkdir(exist_ok=True); prog = out / "PROGRESS.md"
    for seed in range(first, last):
        known = {}
        for f in glob.glob(FOUND) + glob.glob(str(out / "full_*.json")):
            d = json.load(open(f)); known["".join(d["infected"])] = {p: int(d["infected"][p[0]][p[1]] == "*") for p in zb.CELLS}
        t = time.time()
        try:
            found = zb.solve_valid(circles=circles, seed=seed, limit=limit, avoid=list(known.values()), min_distance=dist, fix_shade=shade)
        except TimeoutError:
            found = None
        if found is None:
            prog.open("a").write(f"seed {seed}: nothing within {limit}s\n"); continue
        sol, sh = found; circ = zb.circle_candidates(sol, sh); pockets = zb.clued_bananas(sol, sh, circ)
        prog.open("a").write(f"seed {seed}: {len(circ)} circles, {len(pockets)} clued bananas sizes {sorted(len(c) for c in pockets)}, {sum(sh.values())} infected ({time.time()-t:.0f}s)\n")
        (out / f"grid_{seed}.txt").write_text(zb.show(sol, sh, circles=circ) + "\n")
        zb.dump(out / f"full_{seed}.json", sol, sh, dict(sol), circ)
    prog.open("a").write("TEMPLATE DONE\n")

if __name__ == "__main__":
    if sys.argv[1] == "mk": mk(sys.argv[2], [rc(t) for t in sys.argv[3:]])
    else: run(sys.argv[2], sys.argv[3], int(sys.argv[4]), int(sys.argv[5]), *map(int, sys.argv[6:]))
