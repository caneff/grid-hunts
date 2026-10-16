# Halvers and between lines: truths to build on

Spec #39. Facts about the halver + between-line rules that the rule check
(#40), the hunt (#41) and the setter can use. Sections 1–3 follow from the rules
alone. Section 4 applies them to the board, using only what L1–L5 force.

Values are written in real form here (a halved 5 is 2.5). The model doubles
them, so a real gap of 0.5 is a doubled gap of 1.

## 1. The value table

| value | cells that have it |
|---|---|
| 0.5 | halved 1 |
| 1 | normal 1, halved 2 |
| 1.5 | halved 3 |
| 2 | normal 2, halved 4 |
| 2.5 | halved 5 |
| 3 | normal 3, halved 6 |
| 3.5 | halved 7 |
| 4 | normal 4, halved 8 |
| 4.5 | halved 9 |
| 5–9 | normal 5–9 |

- **A non-integer value is always a halver with an odd digit.** There are
  exactly five such cells in a grid: the halved 1, 3, 5, 7 and 9.
- **Collisions:** a halved 2k has the same value as a normal k (k = 1..4).
  The two cells can even share a house, since their digits differ. Inside a
  house, distinct digits do not always mean distinct values.
- **Equal circles kill a line.** That includes circles with different digits
  and the same value, such as a halved 6 and a normal 3.

## 2. What a body cell can and cannot be

- **0.5 (the halved 1) is the global minimum, and 9 (a normal 9) is the
  global maximum.** Neither can ever be a body cell. Each is a circle or off
  every line.
- **A body cell with value 1** (a normal 1 or a halved 2) needs a circle below
  1, so that circle is the halved 1. Every line with a value-1 body cell ends
  on the one halved-1 cell.
- **A body cell with value 8** (a normal 8) needs a normal-9 circle.
- **A halver as the high circle** has a value of at most 4.5, so its body holds
  only values below that.
- **Body cells in one house:** k cells need k distinct digits strictly between
  the circles. At most one of them is halved, so they take at least k − 1
  distinct values. This is a cheap bound for pruning a candidate line before
  any solver call.

## 3. Lines that pin halvers

- **Circles one apart pin a halver.** Integer circles n and n+1 leave only
  n + 0.5 for the body. That value is one halver, so the body is exactly one
  cell: the halved (2n+1). A 3-cell line with circles 2 and 3 forces its
  middle to be the halved 5, and circles 3 and 4 force the halved 7.
- **Halved 2 and halved 4 are hard to pin.** Their values collide with
  normal 1 and normal 2, so a line rarely tells them apart. They are best left
  for elimination: once the other halvers are pinned, the house rules force
  the last ones.
- **Halvers off every line are invisible.** A cell on no line constrains
  nothing about its own halver status beyond the house rules. Uniqueness needs
  every halver either on a line that fixes its status, or forced by
  elimination (one per row, column and box, and each digit once).
- **Search space:** there are 46,656 (6^6) ways to place nine cells one per
  row, column and box. Each takes 9! digit orders, cut down by the digit grid.

## 4. The first board (BGHKnjgkHd), from L1–L5 alone

Corrected 2026-10-16. The first version of this section assumed all of Chris's
marks. #40's report then found that 8 of the 18 marks are not forced by
L1–L5: r1c1=1, r1c2=9, r4c1=2, r8c2=6, r9c4=3, r8c2 and r9c4 as halvers, and
"box 5's halver in r5c5 or r5c6". Each has a counterexample solution, two of
which were re-checked by a separate checker. This section now uses only what
holds.

- **L1's body is all of box 5.** All nine box-5 digits must sit strictly
  between two circles of at most 9, so box 5's 9 cannot be a normal 9. Box 5's
  halver is its 9 (4.5), which can be in any box-5 cell. The rest of box 5 is
  normal 1–8, values 1–8, so the circles must be 0.5 and 9.
  **{r4c3, r6c3} = {halved 1, normal 9}**.
  - In general, a body that holds a whole house forces that house's halver to
    be its 9, and the line's circles to be the halved 1 and a normal 9.
- **Forced halvers.** Box 4's halver is the 1, at r4c3 or r6c3. Box 5's is the
  9, somewhere in box 5. Box 1's is the 8, at r2c1 or r3c1 (a mark that held).
- **The six halvers left are boxes 2, 3, 6, 7, 8 and 9, with digits
  {2, 3, 4, 5, 6, 7}.** The new lines must pin them, or leave them forced by
  elimination. The marks that held: r4c2=8, r6c1=6, r6c2=7, r7c3=7, r8c3=8,
  and {1,9} at r4c3, r6c3, r7c2 and r9c1.
- **The halved-1 cell is a hub.** Lines may share circles, and every body with
  a value-1 cell must end on the halved 1 at r4c3 or r6c3. A new line
  starting there can reach far into the grid. The same goes for any normal 9
  as a high circle.

## 4b. The current board (DFRTLJqBKt, Chris's switch on 2026-10-16)

L1–L4 are unchanged, so §4's box-5 facts still hold. Box 5's halver is its 9,
and {r4c3, r6c3} = {halved 1, normal 9}. The new L5 is r7c9 [r8c9 r8c8 r8c7]
r7c7, and L6 is r9c4 [r9c5 r9c6 r8c6 r7c5 r7c4] r8c3. All 23 of Chris's marks
on this board hold in every solution of L1–L6 (#39 comment, checked with
#40's rule model). The halvers fixed so far:

| box | halver | cell |
|---|---|---|
| 4 | 1 | r4c3 or r6c3 |
| 5 | 9 | r5c5 or r5c6 |
| 7 | 6 | r8c2 |
| 8 | 2 or 3 | r9c4 |

The halvers left are in boxes 1, 2, 3, 6 and 9. Every unique finish keeps all
23 marks, since adding lines only removes solutions.

## 5. Use in the hunt (#41)

- A line separates target T from second solution S only if it includes a
  cell whose value differs between T and S. Generate candidates through those
  cells only.
- Reject a candidate early, before any solver call, if:
  - a body cell holds the halved 1 or a normal 9 in T;
  - its circles are equal in value in T;
  - a one-house body breaks the k − 1 bound in §2.

## 6. Line economy: space, not speed, is the binding limit

Measured on the current board (L1–L6): 28 body cells and 9 circles are taken,
so **44 cells are left that can become bodies**. Per box: 9 each in boxes 2, 3
and 6, 5 in box 1, 4 in box 9, 3 in boxes 4 and 8, 2 in box 7, and 0 in box 5.

- **A fresh circle costs a body cell too.** A cell that is a circle can never
  be a body cell, so each new circle permanently removes one cell from the 44.
  Reusing an existing circle (r4c3, r6c3, r8c3, r6c1, r9c4, r4c1, r4c2, r7c7,
  r7c9, or a new line's circle) is free. Rank candidates by
  **solutions killed per new cell consumed**, counting fresh circles and
  bodies, not by solutions killed alone.
- **Rough budget.** Boxes 2, 3 and 6 are empty of lines, and the halvers of
  boxes 1, 2, 3, 6 and 9 are unpinned. A body cell inside a window of a few
  values carries about one to two bits. The 44 cells give a few tens of bits
  at best, which is the same order as what has to be fixed. A greedy
  separator that spends cells on one-solution kills can run out of space
  with solutions left. That is the most likely way a seed ends `Empty`, and
  the report should say so when it happens.
- **Two phases.** While the pool of sampled solutions is large, pick lines by
  the share of the pool they kill per cell. Tight windows (circles a few
  values apart) are informative, and wide windows with extreme circles (a
  halved 1 or normal 9 end) carry little. Once every pool sample equals the
  target, switch to the check's second solution. Late second solutions tend
  to differ in a small swap set: aim one line through a cell of that set
  whose window splits the two values, ideally reusing a circle.
- **Grow lines from the target; don't enumerate paths.** Unbounded king paths
  explode. Start at a circle, extend through neighbours whose target value
  stays inside the window, and stop when the gain per cell drops.
- **Dead seeds early.** If no free cell lies where the target and the second
  solution differ, or every such cell is boxed in by the crossing rule, end
  the seed with `Empty("no space: …")` at once rather than searching.
