# U-Bahn: what the outside numbers force

Facts that hold in every valid U-Bahn network, derived by hand on 2026-10-10
by the controller session and then checked against a full enumeration of
small boards. They are for three uses: redundant constraints in the finder
(`finders/ubahn/`, #773), free rejects of an impossible set of numbers before
any solve, and steps a person solving the puzzle can use.

## Status of each claim

- **Proved** below by a counting argument that does not depend on board size.
- **Checked** by two throwaway scripts that enumerated every connected valid
  network on 3x4 (446), 4x4 (15,593), 4x5 (546,756), 5x4 (546,756) and 3x6
  (53,542): every fact below held with zero failures. Larger boards rest on
  the proofs alone. The scripts are not in the tree, because this repo keeps
  no new Python under `docs/research/`; they are readable in history with
  `git show b83ab03:docs/research/2026-10-10-u-bahn-forced-facts/check_lemmas.py`
  (and `check_lemmas_border.py`). Their home, if kept, is a test under
  `finders/ubahn/`.
- **Not measured**: whether adding any of these to the CP-SAT model makes a
  solve faster.

## Words

Pieces: blank, turn, straight, branch, cross. A **sideways branch** has two
vertical arms and one horizontal (`├ ┤`). An **upright branch** has two
horizontal arms and one vertical (`┬ ┴`). For row `r` the outside numbers are
`t` turns, `s` straights, `b` branches, `x` crosses. `d(r)` is the number of
vertical edges crossing the boundary between row `r` and row `r+1`. Every row
fact has a column twin with "horizontal" and "vertical" swapped.

## The one counting argument

Every edge has two ends. In one row, count the horizontal arm ends: a turn
has 1, a horizontal straight 2, a vertical straight 0, a sideways branch 1,
an upright branch 2, a cross 2. The total is twice the row's horizontal
edges, so it is even. Count the vertical arm ends the same way: the total is
`d(r-1) + d(r)`.

## Facts for any row

1. **Sideways branches match turns in parity.** The number of sideways
   branches in a row is odd exactly when its turn number is odd. In a column
   the same holds for upright branches.
2. **An odd turn number needs a branch.** A row with an odd number of turns
   has at least one branch, and at least one of its branches is sideways.
3. **A lone branch has a forced class.** In a row with exactly one branch,
   that branch is sideways if the row's turn number is odd and upright if it
   is even. A branch that is alone in both its row and its column therefore
   needs the row's and the column's turn numbers to have different parity.
4. **Horizontal runs.** Cells joined by horizontal edges form runs. Each run
   has exactly two end cells, each a turn or a sideways branch, and every
   cell between them is a horizontal straight, an upright branch or a cross.
   So a cross, a horizontal straight or an upright branch needs two run ends
   in its row.
5. **Which numbers a middle row can show.** A row's numbers are possible
   inside the row exactly when all of these hold: `t + b` is not 1; if `t`
   is odd then `b >= 1`; if `x > 0` then `t + b >= 2`; and the pieces fit the
   width. On width 5 that leaves 73 of the 125 non-blank tuples.
6. **No turns and no branches** means no crosses, and every straight in the
   row is vertical.
7. **One used cell** in a row means it is a vertical straight.

## Facts for the first and last used row (and column)

A wholly blank row can only lie outside the network, never between two used
rows. The first used row behaves as the top border does:

8. **No crosses.** Every straight is horizontal and every branch points
   inward.
9. **The turn number is even and at least 2.** Turns alternate along the
   row: one opening a run, the next closing it. Only blanks lie between
   runs.
10. **The boundary count is exact:** `d = t + b`. Each turn and each branch
    sends exactly one edge inward, in its own column.
11. **Few numbers are possible.** On width 5 a border row can show 13 of the
    125 tuples: `t` in {2, 4}, `x = 0`, `t + s + b <= 5`.
12. **Corner cells** are blank or the one turn that fits.

## Facts for a row boundary

13. **Parity is fixed by the numbers.** `d(r)` is odd exactly when the branch
    numbers of rows 1 to `r` sum to an odd number. Proof: the degrees of all
    cells above the boundary sum to twice the edges among them plus `d(r)`,
    and only a branch has odd degree.
14. **At least two edges when that sum is even**, whenever used cells lie on
    both sides. Connectivity needs one edge; parity forbids exactly one.
15. **A single edge across a boundary** needs at least two used rows on each
    side, because each side must hold a closed loop.
16. **Crosses bound it below:** `d(r)` is at least the cross number of the
    row above and of the row below.
17. **Two-row window.** `d(r-1) + d(r)` lies between
    `t + b + 2x + (1 if t is odd)` and `t + 2s + 2x + b + p`, where `p` is
    the largest count of sideways branches the parity in fact 1 allows (`b`
    or `b - 1`). With fact 10 fixing the first and last boundary exactly,
    the windows chain inward from both ends.

## Whole-board facts

18. **The branch total is even**, and it is at least the number of rows with
    an odd turn number plus the number of columns with an odd turn number.
19. **At least 4 turns.** The turn total, the sideways-branch total and the
    upright-branch total all share one parity.
20. **Closed regions:** a connected network encloses exactly
    `branches / 2 + crosses + 1` regions.
21. For each piece type the row numbers and the column numbers have the same
    sum.

## What the solver does not already know

CP-SAT's linear relaxation carries every equality above that is a plain sum
over edge variables. It does not see the parity facts (1, 2, 3, 13, 14, 18),
which are the candidates worth adding as explicit constraints. Facts 5 and 11
are the content of the per-line automaton in
`2026-10-10-u-bahn-optimization-queue.md`. All of them belong in a `verify`
oracle that shares nothing with the model, whatever they do for speed.
