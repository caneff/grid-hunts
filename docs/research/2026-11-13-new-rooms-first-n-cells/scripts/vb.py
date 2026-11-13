import sys, subprocess
from collections import Counter
prog, nth, title, out = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
L_ = open(prog).read().splitlines()
i = next(k for k, l in enumerate(L_) if l.endswith(f"FOUND {nth}"))
get = lambda j, tag: L_[i + j].split(tag, 1)[1].split()
R, Dg, L = get(1, "regions"), get(2, "digits"), get(4, "circles")
cells = [(r, c) for r in range(6) for c in range(6)]
D = {(r, c): int(Dg[r][c]) for r, c in cells}; G = {(r, c): R[r][c] for r, c in cells}
def seq(t):
    i = int(t[1]) - 1; ln = [(i, c) for c in range(6)] if t[0] == 'r' else [(r, i) for r in range(6)]
    return ln[::-1] if t[-1] in 'RB' else ln
def val(t):
    ln = seq(t); f = D[ln[0]]; assert f <= 6, t
    rg = [G[q] for q in ln]; assert all(z == rg[0] for z in rg[:f]) and (f == 6 or rg[f] != rg[0]), t
    return D[ln[f - 1]]
vals = [val(t) if t[-1] in 'LRTB' else D[(int(t[1]) - 1, int(t[3]) - 1)] for t in L]
cnt = Counter(vals); assert all(cnt[w] == w for w in cnt), cnt
for k in "ABCD": assert sorted(D[p] for p in cells if G[p] == k) == list(range(1, 10)), k
for j in range(6): assert len({D[(j, c)] for c in range(6)}) == 6 and len({D[(r, j)] for r in range(6)}) == 6
print("ok", len(L), " ".join(R), " ".join(Dg)); print("outside", " ".join(get(3, "outside")))
S = "/tmp/claude-1000/-home-caneff-src-grid-hunts/3702cf19-92f5-4309-b53e-71ca692fbe21/scratchpad"
link = subprocess.run(["uv", "run", "python", f"{S}/build_new.py", f"{S}/board.json", " ".join(L), title], capture_output=True, text=True, check=True, cwd="/home/caneff/src/grid-hunts").stdout
open(out, "w").write(link)
