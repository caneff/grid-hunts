"""The shared halver layer's report (spec #52): a board's status, then
whether each mark holds in every solution, for any line type.

`report(board, marks, time_limit)` prints `L1-L<k>: <status>`, then one line
per mark, `held` or `NOT HELD` (with a solution that breaks it) or `TIMEOUT`
(no verdict in `time_limit` seconds, never read as held). It returns 0 when
every mark held, 1 otherwise. A board with no solution, or no verdict on its
own status, has no mark checked and returns 1 with the reason.
"""

from halver_rules import cell_name, mark_name


def describe(solution):
    """A solution on one line: each row's digits, then the halver cells."""
    rows = " ".join(
        f"r{r + 1} {''.join(map(str, row))}" for r, row in enumerate(solution.digits)
    )
    halvers = " ".join(cell_name(c) for c in sorted(solution.halvers))
    return f"{rows}; halvers {halvers}"


def report(board, marks, time_limit):
    """Print the board's status and each mark's verdict; the exit status."""
    status = board.check(time_limit=time_limit).status
    print(f"L1-L{len(board.lines)}: {status}")
    if status not in ("unique", "not_unique"):
        print(f"no mark checked: the board's status is {status}")
        return 1

    all_held = True
    for mark in marks:
        result = board.mark_holds(mark, time_limit=time_limit)
        name = mark_name(mark)
        if result.status == "held":
            print(f"held      {name}")
            continue
        all_held = False
        if result.status == "not_held":
            print(f"NOT HELD  {name}")
            print(f"  broken by: {describe(result.counterexample)}")
        else:
            print(f"TIMEOUT   {name} (no verdict in {time_limit:g}s)")
    return 0 if all_held else 1
