# Halvers and between lines: truths to build on

Spec #39. Facts about the halver + between-line rules that the rule check
(#40), the hunt (#41) and the setter can use. Sections 1–3 follow from the rules
alone. Section 4 also assumes Chris's marks on the board, which #40's report
checks. Treat section 4 as provisional until that report says every mark held.

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

## 4. The board (assumes Chris's marks hold; #40 checks them)

- **L1's body is all of box 5.** All nine box-5 digits must sit strictly
  between two circles of at most 9, so box 5's 9 cannot be a normal 9. Box 5's
  halver is its 9 (4.5). The rest of box 5 is normal 1–8, values 1–8, so the
  circles must be 0.5 and 9. **{r4c3, r6c3} = {halved 1, normal 9}**, which
  matches Chris's {1,9} marks.
  - In general, a body that holds a whole house forces that house's halver to
    be its 9, and the line's circles to be the halved 1 and a normal 9.
- **So box 4's halver is the 1, in column 3.** With Chris's marks, five
  halvers are placed or narrowed:

  | box | halver | cell |
  |---|---|---|
  | 1 | 8 | r2c1 or r3c1 |
  | 4 | 1 | r4c3 or r6c3 |
  | 5 | 9 | r5c5 or r5c6 |
  | 7 | 6 | r8c2 |
  | 8 | 3 | r9c4 |

- **The four halvers left are boxes 2, 3, 6 and 9, with digits {2, 4, 5, 7}.**
  Rows and columns follow from the house rules:
  - Box 9's halver is in r7, columns 7–9.
  - Box 6's halver is in r4 or r6, whichever box 4 does not use, in columns 7–9.
  - Box 2's halver is in c5 or c6, whichever box 5 does not use, in rows 1–3.
  - Box 3's halver is in rows 1–3, columns 7–9.
  - Boxes 2 and 3 take r1 and whichever of r2/r3 box 1 does not use.
- **What the new lines have to do.** They must pin the halved 5 and halved 7
  (the one-apart circles in §3 are the direct tool). They must place the
  halved 2 and 4, by line or by elimination. They must also settle the five
  two-way choices above, and fill the empty top-right digits.
- **The halved-1 cell is a hub.** Lines may share circles, and every body with
  a value-1 cell must end on the halved 1 at r4c3 or r6c3. A new line
  starting there can reach far into the grid. The same goes for any normal 9
  as a high circle.

## 5. Use in the hunt (#41)

- A line separates target T from second solution S only if it includes a
  cell whose value differs between T and S. Generate candidates through those
  cells only.
- Reject a candidate early, before any solver call, if:
  - a body cell holds the halved 1 or a normal 9 in T;
  - its circles are equal in value in T;
  - a one-house body breaks the k − 1 bound in §2.
