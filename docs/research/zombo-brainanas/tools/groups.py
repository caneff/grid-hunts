"""Can a valid grid have >= K uninfected groups (brainanas)? Exact count, no pocket library. usage: groups.py K [limit] [workers]"""
import sys, time; sys.path.insert(0, "/home/caneff/orca/workspaces/sudokumaker-custom-constraints/tang/docs/research")
import zombo_brainanas_cpsat as zb
zb.BIG_POCKET_CELLS = frozenset(p for p in zb.CELLS if zb.box(*p) == 9)
zb.WORKERS = int(sys.argv[3]) if len(sys.argv) > 3 else 8
K = int(sys.argv[1]); limit = int(sys.argv[2]) if len(sys.argv) > 2 else 900
t = time.time(); rounds = []
try:
    f = zb.solve_valid(seed=3, limit=limit, min_pockets=0, min_groups=K, log=rounds.append)
except TimeoutError:
    f = "timeout"
print("\n".join(rounds)); print(f"K={K}: {'TIMEOUT' if f == 'timeout' else 'FEASIBLE' if f else 'INFEASIBLE'} {time.time()-t:.0f}s", flush=True)
if f and f != "timeout":
    sol, sh = f; g = zb.uninfected_groups(sh); print("groups", g); print(zb.show(sol, sh, circles=zb.circle_candidates(sol, sh)))
    zb.dump("/home/caneff/orca/workspaces/sudokumaker-custom-constraints/tang/scratch-zombo/hunt/plant/groups_K%d.json" % K, sol, sh, dict(sol), zb.circle_candidates(sol, sh))
