import sys
import time

n = int(sys.argv[1])
k = n  # n x n grid, regions of n cells, n regions
cap = float(sys.argv[2]) if len(sys.argv) > 2 else 300


def norm(cells):
    mr = min(r for r, c in cells)
    mc = min(c for r, c in cells)
    return frozenset((r - mr, c - mc) for r, c in cells)


cur = {frozenset({(0, 0)})}
for _ in range(2, n + 1):
    nxt = set()
    for s in cur:
        for r, c in s:
            for d in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                q = (r + d[0], c + d[1])
                if q not in s:
                    nxt.add(norm(s | {q}))
    cur = nxt
sym = []
for s in cur:
    sr = sum(r for r, c in s) * 2
    sc = sum(c for r, c in s) * 2  # doubled centroid
    if sr % n or sc % n:
        continue
    a, b = sr // n, sc // n  # centre in doubled coords
    if all((a - r, b - c) in s for r, c in s):
        sym.append((s, (a, b)))
print(f"{n}x{n}: fixed {n}-ominoes {len(cur)}, point-symmetric {len(sym)}")
full = (1 << n * n) - 1


def bit(r, c):
    return 1 << (r * n + c)


placements = {}
for sh, _ in sym:
    h = max(r for r, c in sh)
    w = max(c for r, c in sh)
    for cr in range(n - h):
        for cc in range(n - w):
            m = 0
            for r, c in sh:
                m |= bit(cr + r, cc + c)
            low = (m & -m).bit_length() - 1
            placements.setdefault(low, []).append(m)
sols = []
t0 = time.time()


def dfs(used, acc):
    if used == full:
        sols.append(list(acc))
        return
    if time.time() - t0 > cap:
        raise TimeoutError
    low = ((~used) & (used + 1)).bit_length() - 1
    for m in placements.get(low, ()):
        if m & used == 0:
            dfs(used | m, [*acc, m])


try:
    dfs(0, [])
    done = True
except TimeoutError:
    done = False


def cells_of(m):
    return [(i // n, i % n) for i in range(n * n) if m >> i & 1]


def canon(sol):
    best = None

    def tr(r, c, f):
        for _ in range(f % 4):
            r, c = c, n - 1 - r
        if f >= 4:
            c = n - 1 - c
        return r, c

    for f in range(8):
        key = tuple(
            sorted(tuple(sorted(tr(r, c, f) for r, c in cells_of(m))) for m in sol)
        )
        if best is None or key < best:
            best = key
    return best


uniq = {}
for s in sols:
    uniq.setdefault(canon(s), s)


def bars(s):
    return sum(
        1
        for m in s
        if len({r for r, c in cells_of(m)}) == 1
        or len({c for r, c in cells_of(m)}) == 1
    )


nobar = [s for s in uniq.values() if bars(s) == 0]
print(
    f"tilings {len(sols)} ({'complete' if done else 'timed out'}), distinct {len(uniq)}, without any 1x{n} bar {len(nobar)}"
)
for s in nobar[:6]:
    grid = [["."] * n for _ in range(n)]
    for i, m in enumerate(s):
        for r, c in cells_of(m):
            grid[r][c] = chr(65 + i)
    print("---")
    print("\n".join("".join(row) for row in grid))
