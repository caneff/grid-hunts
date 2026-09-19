"""Throwaway probe: does a sudoku + shaded cell set exist with a shaded cell holding 8?

Rule: a shaded cell cell's digit equals the number of shaded cells among its king-move
neighbours. unshaded cells are unconstrained.
"""

from ortools.sat.python import cp_model

N = 9
m = cp_model.CpModel()
x = [
    [[m.new_bool_var(f"x{r}{c}{d}") for d in range(1, 10)] for c in range(N)]
    for r in range(N)
]
g = [[m.new_bool_var(f"g{r}{c}") for c in range(N)] for r in range(N)]
digit = [
    [sum((d + 1) * x[r][c][d] for d in range(9)) for c in range(N)] for r in range(N)
]

for r in range(N):
    for c in range(N):
        m.add_exactly_one(x[r][c])
for d in range(9):
    for i in range(N):
        m.add_exactly_one(x[i][c][d] for c in range(N))
        m.add_exactly_one(x[r][i][d] for r in range(N))
    for br in range(3):
        for bc in range(3):
            m.add_exactly_one(
                x[br * 3 + a][bc * 3 + b][d] for a in range(3) for b in range(3)
            )


def neighbours(r, c):
    return [
        (r + a, c + b)
        for a in (-1, 0, 1)
        for b in (-1, 0, 1)
        if (a or b) and 0 <= r + a < N and 0 <= c + b < N
    ]


for r in range(N):
    for c in range(N):
        m.add(sum(g[i][j] for i, j in neighbours(r, c)) == digit[r][c]).only_enforce_if(
            g[r][c]
        )

# Some shaded cell holds an 8.
eight = []
for r in range(N):
    for c in range(N):
        b = m.new_bool_var(f"e{r}{c}")
        m.add_implication(b, g[r][c])
        m.add_implication(b, x[r][c][7])
        eight.append(b)
m.add_bool_or(eight)

s = cp_model.CpSolver()
s.parameters.num_workers = 1
s.parameters.max_time_in_seconds = 120
st = s.solve(m)
print(s.status_name(st), f"{s.wall_time:.2f}s")
if st in (cp_model.OPTIMAL, cp_model.FEASIBLE):
    for r in range(N):
        row = []
        for c in range(N):
            d = next(d + 1 for d in range(9) if s.value(x[r][c][d]))
            row.append(f"{d}{'*' if s.value(g[r][c]) else ' '}")
        print(" ".join(row))
    # Independent recheck of the rule from the printed solution.
    grid = [
        [next(d + 1 for d in range(9) if s.value(x[r][c][d])) for c in range(N)]
        for r in range(N)
    ]
    gh = [[s.value(g[r][c]) for c in range(N)] for r in range(N)]
    ok = all(
        sum(gh[i][j] for i, j in neighbours(r, c)) == grid[r][c]
        for r in range(N)
        for c in range(N)
        if gh[r][c]
    )
    ok &= all(sorted(row) == list(range(1, 10)) for row in grid)
    ok &= all(
        sorted(grid[r][c] for r in range(N)) == list(range(1, 10)) for c in range(N)
    )
    ok &= all(
        sorted(grid[br + a][bc + b] for a in range(3) for b in range(3))
        == list(range(1, 10))
        for br in (0, 3, 6)
        for bc in (0, 3, 6)
    )
    print("recheck", "OK" if ok else "FAIL")
