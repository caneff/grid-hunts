# Renbanana — the chocolate rectangle catalogue

Ticket #377. Every legal chocolate rectangle, enumerated exhaustively, in two
layers. The circle-value table in `CIRCLE-VALUES.md` (#374) falls out of this
as a query; the support matrices here are the reusable part.

Data: `rectangle-catalogue.json` beside this file — per shape, per box offset,
the count, the support matrix, one example filling, and the circle cells.

**A shape being in this catalogue means it is *locally* legal. It does not mean
it fits in a real grid.** The catalogue says nothing about whether a legal
shading can put that rectangle there, nor about the digits outside it. 1x8 is
the standing counterexample: it is catalogue-legal (2 fillings) and yet
UNSAT in a real grid, because it dies at the shading stage.

## What is enumerated

A filling of an `a x b` rectangle is legal when:

- orthogonally adjacent cells differ by **>= 5** (German Chocolate), and
- digits are **distinct within each row of the rectangle and each column of
  it** — a Latin condition, restricted to the rectangle's own cells.

That is all. Digits may repeat across different rows and columns; that is
exactly why `4 9 / 9 4` works as a 2x2.

Two things are *consequences*, not inputs:

- **No 5 in any group of area >= 2.** A 5 with a chocolate neighbour needs
  `|5 - d| >= 5`, so `d <= 0` or `d >= 10`. In a rectangle of area >= 2 every
  cell has at least one neighbour, so the 5 is squeezed out by the adjacency
  rule alone. **A 1x1 has no neighbour, so a lone chocolate 5 is legal** — and
  the 1x1 support below is all of 1..9 including 5, as it must be. Stated the
  way the component will want it: *no chocolate group of size >= 2 contains a
  5; every 5 on the grid is banana or a lone 1x1 chocolate cell.*
- **The low/high checkerboard.** Two digits from {1,2,3,4} differ by at most 3,
  as do two from {6,7,8,9}, so every chocolate adjacency pairs a low with a
  high and the parity classes are fixed. Not imposed; it emerges.

### Two layers, reported side by side

- **Layer L (Latin, region-agnostic)** — the constraints above and nothing
  else. No boxes. Reusable for any region layout, including a boxless or
  irregular-region variant, or the 6x6 variant.
- **Layer B (boxed)** — for each box offset `(ro, co)` of the rectangle's
  top-left cell mod 3, the subset of L in which no repeated digit has both its
  cells inside one sudoku box.

Distinctness against cells *outside* the rectangle is an embedding question,
not a catalogue question, and is in neither layer.

## Side bound

**No side exceeds 8.** A column of the rectangle holds `ceil(a/2)` cells of one
parity class. They lie in distinct grid rows but the same grid column, so they
are distinct, and they are all drawn from a 4-element set — {1,2,3,4} or
{6,7,8,9}. So `ceil(a/2) <= 4`, giving `a <= 8`; the same argument on rows gives
`b <= 8`. The bound depends on the 5 exclusion: the parity classes have four
members each *because* 5 is out, which holds for area >= 2 — and area 1 is the
only case where a side above 1 is impossible anyway.

**The enumeration is much tighter than that bound.** Latin-UNSAT shapes:

```
2x8  3x7  3x8  4x7  4x8  5x7  5x8  6x7  6x8  7x7  7x8  8x8
```

So in layer L the real limit is: a side of 8 needs the other side to be 1, a
side of 7 needs the other to be 1 or 2, and once both sides are >= 3 neither
exceeds 6.

## The catalogue

`L` is the layer-L filling count; `boxSAT offsets` are the `(ro, co)` classes
where layer B is non-empty. Exhaustive, nothing truncated.

| shape | area | L | boxSAT offsets |
|---|---|---|---|
| 1x1 | 1 | 9 | all 9 |
| 1x2 | 2 | 20 | all 9 |
| 1x3 | 3 | 40 | all 9 |
| 1x4 | 4 | 70 | all 9 |
| 1x5 | 5 | 72 | all 9 |
| 1x6 | 6 | 62 | all 9 |
| 1x7 | 7 | 16 | all 9 |
| 1x8 | 8 | 2 | all 6 that fit |
| 2x2 | 4 | 140 | all 9 |
| 2x3 | 6 | 428 | all 9 |
| 2x4 | 8 | 1148 | all 9 |
| 2x5 | 10 | 832 | all 9 |
| 2x6 | 12 | 396 | all 9 |
| 2x7 | 14 | 4 | **only ro=2** |
| 3x3 | 9 | 1520 | all but **(0,0)** |
| 3x4 | 12 | 5380 | only ro in {1,2} |
| 3x5 | 15 | 1600 | only ro in {1,2} |
| 3x6 | 18 | 408 | only ro in {1,2} |
| 4x4 | 16 | 26358 | **only (1,1)** |
| 4x5 | 20 | 3076 | **none** |
| 4x6 | 24 | 424 | **none** |
| 5x5 | 25 | 928 | **none** |
| 5x6 | 30 | 300 | **none** |
| 6x6 | 36 | 328 | **none** |
| 2x8, 3x7, 3x8, 4x7, 4x8, 5x7, 5x8, 6x7, 6x8, 7x7, 7x8, 8x8 | — | **0** | — |

Transposes `b x a` behave identically with the offsets swapped.

Two results worth pulling out:

- **Five shapes are Latin-legal but boxed-impossible: 4x5, 4x6, 5x5, 5x6, 6x6.**
  They cannot sit in a 9x9 sudoku at any offset. A boxless or irregular-region
  variant would admit them — which is precisely why layer L is worth keeping
  separately.
- **The largest chocolate rectangle a 9x9 sudoku can hold is 3x6 (18 cells)**,
  with 4x4 (16) and 2x7 (14) next. Subject to a legal shading existing, which
  is a separate question and a much harsher one.

## Layer L support matrices

Each entry is the set of digits that can occupy that cell.

```
1x1   123456789

1x4   12346789  123789    123789    12346789
1x6   12346789  123789    123789    123789    123789    12346789
1x7   12346789  123789    123789    2378      123789    123789    12346789
1x8   46        19        37        28        28        37        19        46

2x2   12346789  12346789          2x3   12346789  123789    12346789
      12346789  12346789                12346789  123789    12346789

2x4   12346789  123789    123789    12346789
      12346789  123789    123789    12346789

3x3   12346789  123789    12346789
      123789    123789    123789
      12346789  123789    12346789
```

### The degree lemma

**Lemma.** Inside a chocolate rectangle, a cell's left and right neighbours
share its grid row, and its up and down neighbours share its grid column. Each
such pair must therefore be *distinct* partners of the cell's digit. A digit
with exactly one German partner can consequently never have two neighbours in
the same line. Partner sets are 1:{6,7,8,9}, 2:{7,8,9}, 3:{8,9}, **4:{9}**,
5:{}, **6:{1}**, 7:{1,2}, 8:{1,2,3}, 9:{1,2,3,4} — so the digits with a single
partner are exactly **4 and 6**, and each is confined to a rectangle **corner**,
where it has at most one horizontal and one vertical neighbour. Those two
neighbours carry equal digits (9 and 9 for a 4, 1 and 1 for a 6) in different
rows and different columns, so they collide unless the rectangle straddles a
box line.

**The support matrices reproduce it mechanically.** Every interior support
above is `123789` — no 4, no 6 — and every corner support is `12346789`. The
3x3 centre, degree 4, is `123789` for the same reason.

**Two confirming witnesses**, both verified grids from `CIRCLE-VALUES.md`:

- The circled **4** sits at r4c4 in a 2x2 at rows 3-4, cols 3-4, with **9 at
  r3c4 and 9 at r4c3** — its only two neighbours, equal, in different rows and
  columns, and the 2x2 straddles the horizontal band boundary so they land in
  different boxes.
- The circled **6** sits at r4c9, a corner of the 2x3 at rows 3-4, cols 7-9,
  with **1 at r3c9 and 1 at r4c8**.

**This doubles as the offset-handling self-check.** If layer B's support for
the digit 4 in a box-*aligned* 2x2 ever comes out non-empty, the offset
handling is wrong. It comes out `123789` — no 4 — at all four aligned offsets,
against `12346789` in layer L. The delta is neither empty nor total, which is
what a correct implementation looks like.

## The L-to-B delta

Where layer B differs from layer L is where the box constraint is doing work.
These three are the diagnostic cases.

**2x2 — this is the circled-4 story.** Box-aligned, the 4 vanishes.

```
offset (0,0), (0,1), (1,0), (1,1)  -- box-aligned      count 40
    123789    123789
    123789    123789

offset (0,2), (1,2), (2,0), (2,1), (2,2)  -- straddling  count 140 (= all of L)
    12346789  12346789
    12346789  12346789
```

A 4 in a 2x2 needs a 9 on both neighbours; those two 9s sit in different rows
and different columns, so they collide only if the whole 2x2 is inside one box.
The moment the 2x2 straddles a box line in either direction, all four cells are
in different boxes and the box constraint does nothing at all — layer B equals
layer L. **A circled 4 in a 2x2 therefore requires a box-straddling 2x2**, and
that is now a table entry, not prose. The verified witness in
`CIRCLE-VALUES.md` has its 2x2 at rows 3-4, cols 3-4 — offset (2,2).

**2x3 — the same story for the circled 6, plus a side.**

```
offset (0,0), (1,0)   count 16    circle cells: none
    123789    1289      123789
    123789    1289      123789

offset (0,1), (1,1)   count 152   circle cells: the right-hand corners
    123789    123789    12346789
    123789    123789    12346789

offset (2,*)          count 428   circle cells: all four corners
    12346789  123789    12346789
    12346789  123789    12346789
```

**3x3 — the box-aligned 3x3 is impossible.** Offset (0,0) has layer B **empty**
against 1520 layer-L fillings. That is the mechanical form of the old hand
argument: a box-aligned 3x3 is a whole sudoku box, so it holds all nine digits
including the 5, which no multi-cell chocolate group may contain. Every other
offset is fine (40 at the once-straddling offsets, 552 at the twice-straddling
ones), and a 9 can sit in any of the nine cells.

## Why the boxed offsets die: the three-in-a-band lemma

The catalogue counts which `(shape, offset)` pairs are boxed-dead. This section
says **why**. Three rules account for every boxed-dead offset in the catalogue
except one shape, with **no false kills** — no offset a rule calls dead has a
non-zero count.

### Rule F — the rectangle contains a whole box

If three of the rectangle's rows lie in one band **and** three of its columns
lie in one stack, the nine cells at that intersection are one full sudoku box.
They are pairwise distinct, so they are all nine digits, including the 5 — and
no chocolate group of area >= 2 may contain a 5. Dead.

This is the old box-aligned-3x3 argument, stated once for every shape.

### Rule R — three rows in one band, width >= 4

**Lemma.** A chocolate rectangle with three rows inside a single box band and
width `b >= 4` admits no legal filling.

The width threshold is real and sharp: at `b = 3` a rectangle with three rows in
one band is fine (3x3 has 40 fillings at offsets (0,1) and (0,2)); at `b = 4` it
is dead at every column offset.

**Proof.** Take the three rows in the band; they alone must be fillable. Group
the rectangle's columns by stack. Consecutive columns of the rectangle fall into
runs, one per stack, and only the first and last run can be shorter than 3.

*Case A — some run has length 3.* Then those three columns and the three band
rows form a whole box, and Rule F kills it.

*Case B — every run has length <= 2.* Then there are at most two runs, so
`b <= 4`, and with `b >= 4` we get exactly `b = 4` split `2 + 2`: two 3x2 blocks
side by side, each entirely inside one box.

Analyse one such **3x2 block, all six cells in one box** (hence pairwise
distinct). Label it

```
    (1,1) (1,2)
    (2,1) (2,2)
    (3,1) (3,2)
```

with (1,1) low. Every cell has at least two neighbours inside the block, and any
two of those neighbours are either in the same rectangle row, the same rectangle
column, or the same box — distinct in all three cases. So:

- (1,1) and (3,1) each need >= 2 distinct partners, so neither is a **4**
  (partner set of 4 is {9}).
- (2,2) has three in-block neighbours, pairwise distinct, so it needs >= 3
  distinct partners: `(2,2) ∈ {1,2}`.
- Symmetrically (1,2), (3,2) are not **6**, and `(2,1) ∈ {8,9}`.

The block's three lows are therefore three distinct members of {1,2,3} — that
is, exactly **{1,2,3}** — and its three highs are exactly **{7,8,9}**. Because
`(2,2) ∈ {1,2}` the **3** sits in an outer row, and because `(2,1) ∈ {8,9}` the
**7** does too.

Now place the 3. Its partner set is {8,9}, and its two in-block neighbours are
distinct, so they are exactly {8,9} — which uses up both of the block's other
highs. The remaining high, the 7, is then forced into the block's *other* outer
row. **In any 3x2 in-box block, the 3 and the 7 occupy opposite outer rows.**

Apply that to both blocks of the 2+2 split. Each block's lows are {1,2,3}, so
each block has its own 3, and rectangle-row distinctness forbids the two 3s from
sharing a row. Both 3s are in outer rows, so one is in the top row and the other
in the bottom row. Say the left 3 is at (1,1); then the left 7 is at (3,2), and
the right 3 must be at (3,3). But (3,2) and (3,3) are orthogonally adjacent, and
`|7 - 3| = 4 < 5`. Contradiction. The mirror case is identical. ∎

**Why width 4 and not width 3.** Width 4 with a 2+2 split is the smallest
configuration that puts *two* complete in-box 3x2 blocks side by side. One block
is satisfiable — 16 fillings. Two blocks each force a 3 into an outer row, the
row constraint pushes them to opposite outer rows, and each block's 7 then lands
in the other block's 3's row, directly across the block boundary. At width 3 the
third column stands alone in its own stack, no second block forms, nothing is
forced, and the shape survives with 40 fillings.

**Rule C** is Rule R transposed: three columns in one stack and height `a >= 4`.

### The worked example: the 4x4 offset table

`(ro, co)` is the box offset of the top-left cell. A 4x4 at row offset 0 covers
grid rows 0-3 and so contains band rows 0-2; at row offset 2 it covers rows 2-5
and contains band rows 3-5; only row offset 1 (rows 1-4) contains no full band.
Same for columns.

| offset | full band? | full stack? | rule | count |
|---|---|---|---|---|
| (0,0) | yes | yes | F (and R, C) | 0 |
| (0,1) | yes | no | **R** | 0 |
| (0,2) | yes | yes | F (and R, C) | 0 |
| (1,0) | no | yes | **C** | 0 |
| (1,1) | no | no | — | **2288** |
| (1,2) | no | yes | **C** | 0 |
| (2,0) | yes | yes | F (and R, C) | 0 |
| (2,1) | yes | no | **R** | 0 |
| (2,2) | yes | yes | F (and R, C) | 0 |

Four of the eight dead offsets contain a whole box and fall to the 5 argument.
The other four — (0,1), (2,1), (1,0), (1,2) — contain **no** full box, so the 5
argument does not reach them; they are exactly the offsets Rule R (or its
transpose C) kills, via the 3x4 or 4x3 sub-rectangle with a 2+2 split. Offset
(1,1) splits 2+2 in both directions, contains neither obstruction, and is the
one survivor.

### The general form, checked against every shape

Predicate: `(shape, offset)` is dead if F, R or C fires.

- **False kills: none.** Every offset the rules call dead has count 0 in
  `rectangle-catalogue.json`. Checked over all 36 shapes x all offsets.
- **Coverage.** Of the 69 boxed-dead offsets belonging to shapes that are
  Latin-legal, the rules explain **63**.

| shape | offsets killed | by |
|---|---|---|
| 3x3 | (0,0) | F only |
| 3x4 | (0,0), (0,1), (0,2) | (0,1) by **R alone**; the others also F |
| 3x5, 3x6 | (0,0), (0,1), (0,2) | F and R |
| 4x4 | all but (1,1) | (0,1), (2,1) by **R alone**; (1,0), (1,2) by **C alone** |
| 4x5, 4x6 | all 9 | R/C everywhere; C alone at ro=1 |
| 5x5, 5x6, 6x6 | all 9 | F, R and C at every offset |

3x3 at (0,0) is the only offset needing **F on its own** — it is exactly one box,
too narrow for R. And Rule R is not redundant either: 3x4 at (0,1) and 4x4 at
(0,1)/(2,1) are dead with no full box anywhere in them.

**This gives a hand proof of a result the catalogue previously had only by
enumeration:** 4x5, 4x6, 5x5, 5x6 and 6x6 are boxed-impossible at every offset.
A rectangle with `a >= 5` contains a full band at every row offset, and one with
`a = 4` contains one at row offsets 0 and 2; pairing that with `b >= 4` and the
transposed rule covers all nine offsets in each case.

### The one gap: 2x7

**2x7 is dead at row offsets 0 and 1 and no rule above explains it.** Both rows
lie in one band there, but two rows in a band is not three, so R does not apply.

The reason is visible in the enumeration but rests on it. All four layer-L 2x7
fillings are shifts —

```
1 7 2 8 3 9 4        4 9 3 8 2 7 1
6 1 7 2 8 3 9        9 3 8 2 7 1 6
```

and their vertical flips. In each, `row2[j+1] = row1[j]` for every `j`. When the
two rows are in one band and columns `j`, `j+1` are in one stack, that pair of
equal digits sits in a single box. Among 7 columns some stack holds two adjacent
ones, so at row offsets 0 and 1 every filling dies; at row offset 2 the rows
straddle the band boundary and all 4 survive. That is a proof, but it is a proof
about four hand-checked fillings, not a structural one — recorded as an open
end, not as a lemma.

### Verification

Two independent checks, both re-run for this section:

1. **Predicate vs. catalogue.** The F/R/C predicate was evaluated for every
   shape and offset in `rectangle-catalogue.json` and compared with the stored
   counts: zero false kills, six unexplained dead offsets, all six being 2x7.
2. **Proof steps vs. a fresh enumerator.** A separately written brute-force
   enumerator reproduced each step: a 3x2 block wholly inside one box has **16**
   fillings, **every one** of them using lows exactly {1,2,3} and highs exactly
   {7,8,9}, with the 3 and the 7 in opposite outer rows in all 16 (rows 1/3 or
   3/1, never the middle, never the same row). It also reproduced 3x4 at
   row offset 0 = 0 fillings at all three column offsets, and 3x3 at row offset
   0 = 0 / 40 / 40, matching the catalogue.

## The circle query

Derived from the catalogue: for a shape of area `k`, can the digit `k` appear,
and where. This is the whole of `CIRCLE-VALUES.md`'s digit half, computed
exactly.

| area | shape | fillings containing the digit | where the digit may sit |
|---|---|---|---|
| 1 | 1x1 | 9 of 9 | the cell |
| 4 | 1x4 | 12 of 70 | the two ends only |
| 4 | 2x2 | 14 of 140 | any cell — but only at a box-straddling offset |
| 5 | 1x5 | **0 of 72** | nowhere |
| 6 | 1x6 | 18 of 62 | the two ends only |
| 6 | 2x3 | — | the four corners only; which corners depends on the offset |
| 7 | 1x7 | **16 of 16** | any cell |
| 8 | 1x8 | 2 of 2 | positions 4 and 5 only |
| 8 | 2x4 | 1060 of 1148 | any cell |
| 9 | 3x3 | 1456 of 1520 | any cell, at any offset but (0,0) |

Two rows carry real weight:

- **Circle 5 is impossible, mechanically.** Area 5 has only one shape, 1x5, and
  not one of its 72 legal fillings contains a 5. That replaces the hand
  argument with an exhaustive check.
- **Circle 7 is free once the shape exists.** All 16 legal 1x7 fillings contain
  a 7, at every offset. So "can a circle read 7" and "does a 1x7 exist" are the
  same question — which is how `CIRCLE-VALUES.md` closes it.

## Why the support matrix is the artifact

Given a chocolate rectangle of known shape and box position, the support matrix
says which digits can sit in which cell — a sound candidate-elimination oracle,
computed once, offline, exhaustively. That is exactly the shape of deduction
the constraint component needs, and it is sound by construction: it never
removes a digit that some legal filling uses.

It does not solve the component's harder problem — the shading is existential,
so the component does not know which rectangle a cell belongs to. But once a
rectangle is known or hypothesised, this table is the answer, and it is
reusable at every later ticket on this map.

## One example per shape

The smallest boxed-SAT offset for each shape; for the five shapes that are
Latin-legal but boxed-impossible, a layer-L filling instead.

```
1x1  @0,0   1                     2x2  @0,0   1 7
1x2  @0,0   1 6                               8 2
1x3  @0,0   1 7 2
1x4  @0,0   1 7 2 8               2x3  @0,0   1 8 3
1x5  @0,0   1 7 2 8 3                         7 2 9
1x6  @0,0   1 7 2 8 3 9
1x7  @0,0   1 7 2 8 3 9 4         2x4  @0,0   1 8 3 9
1x8  @0,0   4 9 3 8 2 7 1 6                   7 2 9 1

2x5  @0,0   1 8 3 9 2             2x6  @0,0   1 8 3 9 2 7
            7 2 9 1 8                         7 2 9 3 8 1

2x7  @2,0   1 7 2 8 3 9 4         3x3  @0,1   1 7 2
            6 1 7 2 8 3 9                     8 2 7
                                              3 9 1

3x4  @1,0   1 8 3 9               3x5  @1,0   1 8 3 9 2
            7 2 9 1                           7 2 9 1 8
            2 7 1 6                           2 7 1 8 3

3x6  @1,0   1 8 3 9 2 7           4x4  @1,1   1 7 2 8
            7 2 9 3 8 1                       8 2 7 1
            2 7 1 8 3 9                       2 8 1 7
                                              7 1 8 2

boxed-UNSAT, layer L only:

4x5         1 7 2 8 3             4x6         1 7 2 8 3 9
            7 1 8 2 9                         7 1 8 3 9 2
            2 8 3 9 1                         2 8 3 9 1 7
            8 2 9 1 6                         8 3 9 2 7 1

5x5         1 7 2 8 3             5x6         1 7 2 8 3 9
            7 1 8 2 9                         7 1 8 3 9 2
            2 8 3 9 1                         2 8 3 9 1 7
            8 2 9 1 7                         8 3 9 2 7 1
            3 9 1 7 2                         3 9 1 7 2 8

6x6         1 7 2 8 3 9
            7 1 8 3 9 2
            2 8 3 9 1 7
            8 3 9 2 7 1
            3 9 1 7 2 8
            9 2 7 1 8 3
```

## Method and verification

Plain depth-first search in row-major order, pruning on row distinctness,
column distinctness and the two adjacency differences as each cell is placed.
No CP-SAT anywhere near it. All 36 shapes finished exhaustively well inside a
minute; nothing was truncated, so every count above is exact and every support
matrix is complete.

Layer B is a filter over layer L: a filling survives offset `(ro, co)` iff no
digit repeats within a box, where the box of local cell `(i, j)` is
`((ro + i) // 3, (co + j) // 3)`. Offsets are restricted to those a side of
that length can actually take in a 9-wide grid — a side of 8 can only start at
column 1 or 2, so it has offsets 0 and 1.

**Verification, three independent ways.**

1. **Against a brute force.** The counts were cross-checked against a
   separately written enumerator that walks all `9^area` assignments and
   applies the rules directly, with no shared code: 1x1, 1x4, 1x6, 2x2 and 2x3
   in layer L, and 2x2 and 2x3 at four box offsets in layer B. Every count
   matched.
2. **Against real verified grids — the end-to-end check.** Take the five full
   9x9 grids that the from-scratch six-rule checker has passed (the
   `FEASIBILITY.md` witness and the four in `CIRCLE-VALUES.md`), decompose each
   into its chocolate components, and look every one of them up in the
   catalogue at its actual box offset. **All 93 rectangles are present, and
   every digit in every one of them lies in that offset's support matrix — zero
   mismatches.** A support matrix that had over-pruned would have shown up here
   as a legal digit missing from the table.
3. **Against results derived elsewhere.** The 1x8 row gives one filling up to
   reversal (`4 9 3 8 2 7 1 6`), matching `FEASIBILITY.md`; the 1x7 row gives
   16 fillings, i.e. 8 up to reversal, matching `CIRCLE-VALUES.md`; and the 3x3
   offset-(0,0) zero reproduces the box-aligned-3x3 argument.

