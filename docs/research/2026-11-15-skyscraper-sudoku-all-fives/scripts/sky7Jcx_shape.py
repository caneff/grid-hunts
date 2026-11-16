"""SCRATCH: region-layout complexity: inner boundary edges, max cells of one region in a line, straight regions, min rows/cols spanned."""
import json, sys
def stats(reg):
    R = reg.replace(" ", ""); g = lambda r, c: R[r * 9 + c]
    b = sum(g(r, c) != g(r, c + 1) for r in range(9) for c in range(8)) + sum(g(r, c) != g(r + 1, c) for r in range(8) for c in range(9))
    ml = st = 0; span = 9
    for k in set(R):
        cs = [(i // 9, i % 9) for i, ch in enumerate(R) if ch == k]
        lines = [sum(r == i for r, _ in cs) for i in range(9)] + [sum(c == i for _, c in cs) for i in range(9)]
        if max(lines) == 9: st += 1
        else: ml = max(ml, max(lines))
        span = min(span, len({r for r, _ in cs}), len({c for _, c in cs}))
    return b, ml, st, span
if __name__ == "__main__":
    D = json.load(open(sys.argv[1]))
    print("boxes", stats("".join("ABC"[c // 3] if r < 3 else "DEF"[c // 3] if r < 6 else "GHI"[c // 3] for r in range(9) for c in range(9))))
    for b in D["boards"]:
        if b.get("reg"): print(b["id"], "boundary %d, max line %d, straight %d, min span %d" % stats(b["reg"]))
