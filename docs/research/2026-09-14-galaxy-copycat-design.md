# Copycat Galaxies — design note

Date: 2026-09-14. Follows `2026-09-14-copycat-scan.md` (no Copycat puzzle
has used a region-division genre) and survey §3.7 (Spiral Galaxies).

## The idea in one line

Copycat cells copy the digit in the cell rotationally opposite them **about
their own galaxy's centre**, not the grid centre. The solver has to build the
galaxy to know where a copycat is looking.

## Why galaxies and copycats fit

- Scojo's modifier is a 180° reflection through one fixed point. Spiral
  Galaxies is the genre whose entire content is 180° reflection through many
  points. The copycat's partner becomes an unknown that the region-building
  half of the puzzle resolves; in every published Copycat puzzle the partner
  is fixed from the start.
- The partner is always inside the same galaxy, so a copycat says something
  about the galaxy's *extent*: a copycat far from its centre forces a big
  galaxy, because the mirror image must be inside it.
- Galaxies already behave as regions (killer-galaxy and parity-galaxy hybrids
  exist, survey §3.7), so value-reading clues have a natural home.

## Design space

Three dials.

**1. Which cells copy?**

| Option | Rule | Coupling to galaxies | Cluing load |
|--------|------|----------------------|-------------|
| Latin placement (Scojo) | 9 copycats, one per row, column, box; different digits | only at the 9 cells | low — the latin structure carries most of the placement |
| Latin + galaxy exclusion | as above, **and no galaxy holds two copycats**; a copycat is never its galaxy's centre cell | the galaxies act as a Star Battle region set on top of the latin structure | low |
| One per galaxy | exactly one copycat in every galaxy | tightest | high — without the latin structure every galaxy needs a clue that singles out its copycat |
| Marked cells | given squares are copycats | at the marks only | lowest, but the placement puzzle is gone |
| Everyone copies | every cell copies its galaxy partner | total | see "Mirror Galaxies" below |

**2. Reflection point.** Own galaxy's centre (the new idea) or the grid
centre (Scojo's rule with galaxies used only for placement). The grid-centre
form is a safe fallback but throws away the reason to pair the two.

**3. What reads the values.** Anything that has worked with Copycat: killer
cages (Yin Yang, Cipher, juggler), arrows (Choco Banana), sight-line circles
(Yin Yang), Kropki and XV, X-sums. Galaxy-native options: each galaxy's
values sum to a given total; tail sums equal (LMD 000897); digits do not
repeat inside a galaxy (a galaxy of at most nine cells is then a hidden
region, and the copycat pair is the one repeated *value* in it).

## Recommended ruleset

> Normal sudoku rules apply.
>
> **Galaxies:** Divide the grid into galaxies. Each galaxy is orthogonally
> connected, contains exactly one circle, and is symmetric under 180°
> rotation about that circle. Every cell belongs to one galaxy.
>
> **Copycat cells:** Place nine copycat cells so that every row, column and
> 3x3 box contains exactly one. No galaxy contains more than one copycat, and
> a copycat is never the cell a circle sits on. The nine copycats contain
> nine different digits.
>
> **Values:** The value of a copycat is the digit in the cell rotationally
> opposite it about its galaxy's circle. The value of every other cell is
> its digit. All other clues refer to values.
>
> Plus one value-reading clue family (killer cages first choice).

Why this shape:

- The latin placement keeps Scojo's feel and keeps the cluing load sane.
- "No galaxy holds two" is the Star Battle essence; it makes a big galaxy
  expensive (it eats a copycat slot for several boxes) and a small galaxy
  useless as a hiding place.
- "Never the circle cell" removes the self-copy (value = digit, which would
  be a copycat that does nothing). With at most one copycat per galaxy, a
  copycat can never be opposite another copycat, so the value definition
  never recurses; Scojo's grid version has to allow the swap case.
- Values may repeat in a unit (a copycat and its partner in one box both
  show the partner's digit). Cages read values, so "digits do not repeat in
  a cage, values may" carries over verbatim.

## The deductions the ruleset creates

1. **Reach.** A copycat at distance (dr, dc) from its circle needs the cell
   at (−dr, −dc) inside the grid and inside its galaxy. Corner and edge
   copycats are only possible for galaxies whose circle is near them. Conversely,
   a small galaxy near a wall cannot host a copycat that has nowhere to look.
2. **Cage arithmetic locates the copycat.** A two-cell cage totalling 2 must
   be values 1 and 1: one cell is a digit 1, the other a copycat whose partner
   is a 1, in the same galaxy, and sudoku puts the two 1s in different units.
   The classic Copycat opening, now with a positional payload: the partner
   must lie at the mirror position, so the galaxy must reach it.
3. **Galaxy exclusion on the latin grid.** A galaxy spanning two boxes takes
   at most one copycat, so the other box's copycat sits outside that galaxy.
   Standard Star Battle counting across boxes and galaxies.
4. **Symmetry transfers constraints.** If a copycat and its partner both sit
   inside a cage or on a line, the partner's digit is counted twice in that
   clue's values. A cage placed symmetrically inside a galaxy is a strong
   tell.
5. **Copycat digits are a full set.** Nine different digits across nine
   copycats: once eight are known, the ninth is forced, exactly as in Scojo's
   puzzles.

## Degenerate cases and their fixes

| Case | Effect | Fix in the recommended rules |
|------|--------|------------------------------|
| Copycat on a circle cell | copies itself, value = digit | forbidden |
| Copycat opposite a copycat | allowed in Scojo's 2024 rule (digits are copied, so the two just show each other's digits); cannot arise here anyway | at most one per galaxy |
| Partner has the same digit as the copycat | value = digit, copycat invisible | allowed (Scojo allows it); the setter avoids it or uses it as a trap |
| Galaxy of size 1 or 2 | can hold a copycat only in the size-2 edge-centred case | allowed; small galaxies simply spend no copycat |
| Exactly nine galaxies wanted | a random spread of nine centres almost never partitions the grid symmetrically (1 of 100 random sets in a quick check) | do not require it; "at most one per galaxy" works for any galaxy count |

## Variants worth a puzzle each

- **Galaxy-placed, grid-copied.** Scojo's exact value rule (grid centre) with
  the copycat placement bound to galaxies (at most one per galaxy). Lower
  novelty, lowest risk; a good warm-up puzzle in a set.
- **Galaxy regions.** Add "digits do not repeat within a galaxy", with every
  galaxy of size at most nine. The copycat pair becomes the only repeated
  value in a galaxy, which makes sight-line and "count equal values" clues
  possible.
- **Copycat tails.** Adopt the tail-sum rule from LMD 000897 on values: the
  copycat shifts one tail's sum by (partner − own digit), so equal tails pin
  the copycat's digit against its partner's.

## Dead end: everyone copies ("Mirror Galaxies")

Rejected 2026-09-14. If every cell copies its galaxy partner, the copy is an
involution inside each galaxy, so the value grid is the digit grid with each
galaxy rotated 180° in place. Once the galaxies are drawn, every clue is the
same clue relocated to its mirror cells, and what remains is a plain variant
sudoku with moved clues. Consequences: there is no hidden placement to find;
digits feed back into the partition only as "this shape gives a
contradictory sudoku" (bifurcation, not deduction); a clue that is itself
mirror-symmetric inside its galaxy reads identically on values and digits,
so the copy is invisible exactly where the galaxy is prettiest; and every
cell-centred galaxy has a dead centre cell copying itself. A single
"copycat galaxy" (one galaxy whose cells all copy, the rest normal) is a
k-way choice, too thin to carry a puzzle. The sparse nine-copycat rule is
the version worth setting.

## What to test by hand first

1. A 6x6 with three or four galaxies, three copycats (one per row/col/box in
   2x3 boxes), three cages. Checks whether "reach" and "cage arithmetic" carry
   a solve without the galaxies being fully forced by their circles alone.
2. The same grid with the grid-centre value rule, to feel the difference the
   local mirror makes.
3. A 9x9 where one galaxy deliberately spans three boxes, to see how strongly
   the exclusion rule bites.

## What else pairs with it

The test for a pairing: does the constraint talk to at least two of the
three layers (galaxy shape, copycat placement, value vs digit)? Ordered by
how many it touches.

### Tier 1 — touches all three

- **Centre digit = galaxy size.** The value of a circled cell is the number of
  cells in its galaxy. Fillomino's clue in Galaxies clothing. Galaxy sizes
  cap at 9; a cell-centred galaxy is odd-sized, an edge- or vertex-centred one
  is even-sized (its cells come in pairs), so the centre type alone fixes the
  parity of the centre digit. The copycat cannot sit on the circle, so this
  digit is always honest; but a copycat elsewhere in the galaxy is a cell
  that "counts" while its value belongs to its partner.
- **Symmetric-pair relations** (a family, one rule per puzzle): every pair of
  cells opposite each other in a galaxy satisfies R. Published: different
  parity (LMD 00045K, Space Oddity). Others: differ by at least 5 (galaxy
  whispers), sum to 10, consecutive, one double the other. Under the copycat
  rule R(digit(c), digit(partner)) becomes R(digit(c), value(c)): a copycat
  is a cell whose value differs from its digit in a known way, so any clue
  that reads values leaks the copycat. Parity is the cleanest: odd/even
  circles on values then detect copycats directly.
- **Galaxy sum lines.** Region sum lines with galaxy borders in place of box
  borders: a line is cut into segments by galaxy boundaries and every segment
  has the same value sum. The solver must draw the galaxies to know the
  segments, and a copycat on the line shifts one segment by (partner − own
  digit). This is the Chaos Construction move applied to Galaxies.

### Tier 2 — touches two

- **Killer galaxies.** Each galaxy's values sum to a given or common total.
  Reads the copycat (value sum = digit sum − own + partner) and the shape.
  Already the standard galaxy-sudoku pairing (00045K), so solvers know it.
- **Zipper through the circle.** A zipper line whose midpoint is a galaxy
  circle and whose cells are mirror pairs: values equidistant from the
  centre sum to the centre value, so the line makes partner pairs sum to a
  fixed number. Mirror pairs are exactly what the galaxy already pairs.
- **Sight-line circles** (Copycat Yin Yang used them): a circled cell's value
  counts the cells of its own galaxy visible in the four directions. Reads
  shape and value. Alternative: counts cells of *other* galaxies seen.
- **Quadruples on vertex circles.** A galaxy centre on a vertex already is a
  circle; giving it digits makes it a quadruple clue for the four cells that
  must all be in the galaxy. Two clues in one glyph.
- **X-sums and skyscrapers on values.** An outside clue indexed by a copycat's
  value reads the partner digit, so the row's first cell can be a copycat
  looking deep into its galaxy.
- **Tail sums** (LMD 000897): the sum of values along each arm of a galaxy is
  equal. Only arms exist when the galaxy is drawn.

### Tier 3 — touches one, still useful as glue

- Kropki, XV, thermo, whispers on values: standard Copycat glue, no galaxy
  awareness.
- Givens on circle cells (the "digit acts as the centre" convention from
  000897): a free, honest digit in every cell-centred galaxy.
- Fog: clear the fog of a cell *and its galaxy partner* when a digit is
  placed. Presentation only, but it makes the mirror visible in SudokuPad.

### Pencil-genre stacking (use sparingly)

- **Star Battle**: the copycats are the stars of a one-star battle on the
  galaxies as regions — that is already the recommended placement rule.
- **Pentominoes** (WPC 2018 "Galaxies and Pentominoes"): a pentomino set
  placed first, galaxies fill the rest; copycats forbidden on pentominoes.
  Heavy; only for a championship-style set.
- Shading or loop genres on top add a fourth layer and are not recommended.

### First three puzzles to set

1. Centre digit = galaxy size, plus killer cages. Classic feel, every layer
   live.
2. Parity pairs with odd/even circles. Copycats become detectable through a
   single glyph type.
3. Galaxy sum lines only. The cleanest test of whether drawing the galaxies
   is fun when the lines are the only clue.

## Not done

No CP-SAT model, no generated puzzle, no uniqueness check; the prototype
started in `2026-09-14-galaxy-copycat/` is untracked and abandoned at the
user's request.

## Second candidate: Copycat cells + Copycat lines

Recorded 2026-09-14 after the galaxy direction cooled. Scojo's cells plus
Phistomefel's lines, two mechanics that share a name and have never met.
(Scojo's own "Copycat Copycat", 2023, is Doublers plus copycats; not this.)

> Normal sudoku rules apply.
>
> **Copycat cells:** Place nine copycat cells, one in every row, column and
> 3x3 box, containing nine different digits. The value of a copycat is the
> digit in the cell rotationally opposite it (180° about the grid centre).
> Every other cell's value is its digit.
>
> **Copycat lines:** Lines come in pairs. The two lines of a pair contain
> the same multiset of *values*, in any order. Each line pair is drawn as
> the 180° image of itself: line B is the mirror of line A.

Mechanism. Because B is A's mirror, a copycat on A at cell c takes its
value from the mirror cell, which lies on B. So:

- With no copycat on the pair, A and B hold the same digits.
- With one copycat on A, A's digits differ from B's by exactly one swap: the
  copycat's own digit is the unmatched one, and the value it shows is B's
  digit at the mirror position. Counting digits on the pair therefore proves
  the copycat and names its cell.
- Copycats opposite each other are allowed (Scojo's 2024 wording copies the
  digit, so two opposite copycats simply show each other's digits). On a
  mirrored pair that is a third pattern: A's digits and B's digits differ by
  a double swap (A carries two extra copies of the copycat's digit relative
  to B, B two extra of its partner's), distinguishable from the one-swap and
  no-swap cases by counting.
- Sudoku bites: the mirror cell is normally in another row, column and box,
  so the copied digit is often one line A could not carry directly. The pair
  ends up sharing a digit one of them is forbidden.

Why it is easier to like than Copycat Galaxies: nothing is drawn or
constructed, the symmetry is given, and every deduction is counting digits
on two visible lines. Phistomefel's Copycat Confusion supplies the natural
twist (line types to be deduced), giving two competing explanations for a
mismatch.

Variant: non-mirrored pairs. The lines share values but are not images of
each other, so a copycat pulls a digit in from anywhere in the grid. Looser,
closer to Phistomefel's original; the copycat is a wildcard both lines must
accept.

First puzzle: three mirrored pairs, no other constraints, copycat rule as
above; see whether counting alone reaches the nine copycats.

## Revision: latin square with galaxies as the regions (preferred)

Recorded 2026-09-14. Precedent check: *Galactic Union* (Tacosian, LMD
000GAA, Dec 2023) is a chaos construction where galaxies are killer cages
straddling the regions; *Colorguru Chaos Deconstruction: Spiral Galaxies*
(crispy16, LMD 000BYE, Nov 2022) has no digits. Galaxies *as* the sudoku
regions is unclaimed in the Galaxies tag listings we hold.

> Divide the grid into nine galaxies of nine cells. Each galaxy is
> orthogonally connected and symmetric under 180° rotation about its circle.
> Every row, column and galaxy contains the digits 1 to 9 once each.
>
> Place nine copycat cells, one in every row, column and galaxy, never on a
> circle. The value of a copycat is the digit in the cell rotationally
> opposite it about its galaxy's circle. Every other cell's value is its
> digit. All clues read values.

Why this beats the sudoku-box version:

- Nine regions of nine cells force exactly nine galaxies, so "exactly one
  copycat per galaxy" returns without any feasibility worry; the earlier
  1-in-100 figure was for random centres, which a setter never uses.
- Every copycat is live by construction: the partner is in the same galaxy,
  which holds 1 to 9 once, so the copied digit always differs from the
  copycat's own digit. The "invisible copycat" case disappears.
- The galaxies carry the region rule, so the solver must build them to place
  digits at all: a chaos construction whose regions have a symmetry to
  exploit, which is far more tractable than connectivity guessing.
- A nine-cell symmetric region has odd size, so every circle is a cell. The
  nine circles are nine known, honest (never copycat) cells, one per galaxy.
- A galaxy's values are 1 to 9 with one repeated digit (the copied one) and
  one missing (the copycat's own). Any sum over a galaxy or over a symmetric
  cage inside it reads exactly that difference.

Costs and cautions: setting a symmetric nonomino partition is real work;
straight 1x9 galaxies are legal but duplicate the row or column rule and
must be avoided; "centre digit = galaxy size" from the pairings list is
dead (every size is nine). Everything else in the pairings list applies.

## Result: equal-size symmetric regions cannot tile the grid irregularly

Checked 2026-09-14 by exhaustive search
(`2026-09-14-galaxy-copycat/symmetric_region_tilings.py`; shape counts
cross-checked against the known 9,910 fixed nonominoes).

| Grid | Point-symmetric n-ominoes (fixed) | Tilings by n of them | Distinct up to symmetry | Without any 1xn bar |
|------|----------------------------------:|---------------------:|------------------------:|--------------------:|
| 6x6 | 24 | 54 | 15 | 1 (the 2x3 boxes) |
| 8x8 | 85 | 250 | 58 | 9, all made of 2x4 and 4x2 rectangles |
| 9x9 | 86 | 37 | 12 | 1 (the 3x3 boxes) |

Every tiling found is made of rectangles: full-length bars or the standard
boxes (and for 8x8, mixed rectangle layouts). No irregular point-symmetric
region ever fits. So "nine galaxies of nine cells as the sudoku regions"
collapses to ordinary sudoku boxes, and the latin-square revision above is
dead in that form.

What survives:

- **Galaxies of unequal size** with "digits do not repeat inside a galaxy"
  (every galaxy at most nine cells, so at least ten galaxies on a 9x9; the
  region rule is weaker than boxes but real). Copycats one per row and
  column, at most one per galaxy, never on a circle. Each copycat is live
  only if its partner's digit differs from its own, which the galaxy
  no-repeat rule guarantees exactly as before.
- **The sudoku-box version** from the recommended ruleset, unchanged.
- Any grid where regions and galaxies are allowed to differ, i.e. Galactic
  Union's arrangement: galaxies are cages or extra constraints laid across
  the regions, not the regions themselves.

## Chosen for setting: Copycat cells + Copycat Region Sum Lines

Chosen 2026-09-14 as the puzzle to set within a few days. Renban rejected
(no-repeat clause too strong); whispers and entropic considered; Region Sum
Lines chosen. Whether a pair's two lines are drawn as 180° images of each
other is a layout choice, not a rule: the rules never mention symmetry
between lines, and the boards so far are simply not drawn symmetric.

> Normal sudoku rules apply.
>
> **Copycat cells:** Place 9 Copycat Cells into the grid so that there is
> exactly one Copycat Cell in each row, column, and 3x3 box. Each Copycat
> Cell must contain a different digit. The value of a Copycat Cell is the
> digit in the cell rotationally opposite itself in the grid (180° rotation
> about the center of the grid). Every other cell's value is its digit.
>
> **Region Sum Lines:** Box borders divide each blue line into segments.
> The values on every segment of a line sum to the same total.
>
> **Copycat lines:** Blue lines come in pairs. The two lines of a pair
> contain the same multiset of values, in any order.

What the combination gives:

- **Total arithmetic across the pair.** Equal value multisets mean equal
  line totals, so (segments of A) x S_A = (segments of B) x S_B. Lines with
  different segment counts share a total: two segments of 12 against three
  of 8, three of 10 against two of 15. The pair fixes both sums from one.
- **Repeats are the tell.** A segment lies inside one box, so its digits
  are distinct. Two equal values inside a segment prove one is a copycat.
  Repeats are legal on RSLs, so this is a clue, not a contradiction.
- **One-swap counting.** A copycat on A borrows the digit of its grid-mirror
  cell, which can be anywhere. digits(A) and values(B) then differ by one
  swap: A's own digit x out, borrowed d in. The unmatched digit on A names
  the copycat; the borrowed digit says what sits in the mirror cell, which
  the solver locates by the 180° rule. Without mirroring the source is
  found through the grid, not through the pair, which is the point.
- **A line can carry a forbidden digit.** The borrowed d must be legal at
  the mirror cell, not at the copycat's cell, so a segment can "contain" a
  digit its box already holds as a digit. Repeats inside a segment (above)
  are the visible form of this.
- **Copycats on both lines.** Each line then has one foreign digit;
  digits(A) and digits(B) differ by two swaps against a common value set.
  Keep for the hardest pair.

Setting recipe:

1. Three pairs; vary segment counts within a pair (a 2-segment line paired
   with a 3-segment line) so the total arithmetic has work to do.
2. Include one pair with a one-cell segment: that cell's value is S
   outright, and if it is a copycat its mirror cell's digit is S.
3. Fill the solution first, then choose the nine copycats last so that:
   pair 1 has no copycat (pure RSL start, gives the totals), pair 2 has one
   copycat on one line, pair 3 has one on each.
4. Place at least one copycat whose mirror cell is on a line of a different
   pair, so the pairs feed each other.
5. Glue: a few Kropki dots on values. No cages with "different digits"
   clauses.
6. Uniqueness: CP-SAT model is 81 copycat bools, one value channel per
   cell, one sum per segment, nine count-equalities per pair. Small.

### Openers (2026-09-14)

**Lemma.** Both lines of a pair have equal length, so segs(A) x S_A =
segs(B) x S_B. A one-cell segment on A puts value S_A on B, where it sits in
a segment summing to at least S_A + 1 unless that is also a one-cell segment.
Hence a line with singles, paired with a line without, has more segments and
the smaller sum. Segment counting alone orders the sums.

**Opener 1, the U-line.** A: r3c3, r3c4, r2c4, r2c3 (box 1, two cells in
box 2, back to box 1): segments (1, 2, 1). B: any straight 4-cell line over
one border, e.g. r5c2-r8c2: segments (2, 2).
1. 3 S_A = 2 S_B; A's values are {S, S, a, b}, a + b = S.
2. B's segments each sum to 1.5 S from those values; {S, S} would give 2S,
   so the segments are {S, a} and {S, b}, forcing a = b = S/2 and S even.
3. Equal values a = b in one segment (box 2): one of r3c4, r2c4 is a
   copycat, mirror digit S/2, the other has digit S/2.
4. The singles r3c3, r2c3 both show S inside box 1: one is a copycat,
   mirror digit S.
5. One copycat per row: (r3c3, r2c4) or (r2c3, r3c4). Two copycats
   pinned to a 2-way choice before any digit; one dot fixing S makes it
   rigid.

**Opener 2, minimal (withdrawn).** (1, 1) vs (2) needed a line inside one
box; ruled out below.

**Ruling (2026-09-14): every line has at least two segments.** No line lies
inside one box. Single-cell segments are fine.

### Segment-structure survey (2026-09-14)

`2026-09-14-galaxy-copycat/segment_openers.py` enumerates every pair of
segment structures up to length 8 (parts of any size, singles included) and
lists which (S_A, S_B) can be realised and how many in-segment duplicates
(copycats) that needs. Geometry-free relaxation: rows and columns are
ignored, so anything it marks forced is truly forced. Full output in
`segment_openers.out` (432 lines: 311 impossible, 13 pinned, 55 copycat
forced, 55 open).

Both openers above check out: (1,1,2) vs (2,2) allows only S_A in {4,6,8}
with a copycat forced; (1,1) vs (2) is the trivial case.

Pairings that pin both sums with no clue at all:

| A | B | S_A / S_B | copycats forced |
|---|---|---|---|
| (1,1,4) | (3,3) or (2,4) | 8 / 12 | 2 |
| (1,2,4) | (3,4) | 8 / 12 | 1 |
| (1,3,3) | (2,5) | 8 / 12 | 1 |
| (1,1,1,4) | (2,2,3) | 9 / 12 | 1 |
| (1,1,2,4) | (2,2,4) or (2,3,3) | 9 / 12 | 1 |
| (1,1,3,3) | (2,2,4) | 9 / 12 | 0 |
| (1,3,4) | (3,5) or (4,4) | 8 / 12 | 2 |
| (2,2,4), (2,3,3) | (2,6) | 12 / 18 | 2 |

All of these have two or more segments on both lines, so the ruling above
removes nothing from the table; it removes every "(n,)" pairing, including
Opener 2.

Without any single-cell segment nothing short forces a copycat: (2,2) vs
(4) and (2,2,2) vs (3,3) are open. The first no-single forcing is at
length 8 with a 6-cell segment, which is not a line shape worth drawing.

**Opener 3, fully determined values.** A: (1,1,4), e.g. a single in box 1,
a single in box 2, then four cells bent inside box 5. B: a straight 6-cell
line over one border, segments (3,3).
1. Sums pinned: S_A = 8, S_B = 12. Both singles are value 8.
2. Four distinct digits cannot sum to 8, so the box-5 segment holds a
   copycat and is {1,2,2,3} or {1,1,2,4}.
3. B must split the six values into two triples of 12, each holding one 8:
   the other two cells sum to 4, so {1,3} and {2,2}. Only {8,8,1,2,2,3}
   works: A's quad is {1,2,2,3}, B is {8,1,3} + {8,2,2}.
4. Two copycats located before any digit: one in A's quad (value 2), one
   in B's {8,2,2} triple (value 2). Every value on both lines is known;
   only the order within segments remains.

**Opener 4, sums with no copycat.** (1,1,3,3) vs (2,2,4) pins 9 / 12 and
needs no copycat, so it is a clean second pair when Opener 3 has already
spent two copycats.

**Filter: at most one single per line, no single beside a 4-cell segment.**
Only (1,3,3) vs (2,5) survives without a 6-cell one-box segment: sums 8 /
12, single = 8, B's pair {4,8}, B's 5-cell segment holds a copycat and is
{1,1,2,3,5} (then A = 8 | {1,2,5} | {1,3,4}, no second copycat) or
{1,2,2,3,4} (then A's triples are {1,3,4} and {2,2,4}, a second copycat).
The others, (2,2,4)/(2,3,3) vs (2,6) at 12/18 and (2,6) vs (3,5)/(4,4) at
16-18, all need a 6-cell segment in one box.

**Opener 5 laid out, (1,3,3) vs (2,5).** A: r1c3 | r1c4 r2c4 r3c4 | r4c4
r4c5 r5c5. B: r8c5 r8c6 | r8c7 r8c8 r8c9 r9c9 r9c8. A bends so its two 1s
can avoid sharing a row or column; B's 5-cell segment snakes in box 9.

```
     c1 c2 c3 | c4 c5 c6 | c7 c8 c9
r1    .  .  A |  A  .  . |  .  .  .
r2    .  .  . |  A  .  . |  .  .  .
r3    .  .  . |  A  .  . |  .  .  .
     ---------+----------+---------
r4    .  .  . |  A  A  . |  .  .  .
r5    .  .  . |  .  A  . |  .  .  .
r6    .  .  . |  .  .  . |  .  .  .
     ---------+----------+---------
r7    .  .  . |  .  .  . |  .  .  .
r8    .  .  . |  .  B  B |  B  B  B
r9    .  .  . |  .  .  . |  .  B  B
```

Forced before any digit: S_A = 8, S_B = 12; r1c3 = 8 in value; r8c5 r8c6 =
{4,8}; box 9 holds a copycat on B whose value repeats another B value there.
Branch 1: B's quint {1,1,2,3,5}, A's triples {1,2,5} and {1,3,4}, no other
copycat on the lines. Branch 2: quint {1,2,2,3,4}, A's triples {1,3,4} and
{2,2,4}, a second copycat in box 2 or box 5.

**Length 6 under the same filter.** Nothing forces a copycat outright. The
pick is (1,2,3) vs (2,4): sums 8/12 or 6/9 only. At S = 8 the sole
copycat-free fill is A = 8 | {2,6} | {1,3,4}, B = {4,8} | {1,2,3,6}; the
other ten branches each need a copycat on a line. At S = 6 all four
branches put a copycat in B's 4-cell segment, and A's triple is {1,2,3} in
three of them. (1,2,3) vs (3,3) is the same sums with fewer branches and
two copycat-free at S = 6. (2,2,2) vs (2,4), the no-single look, allows
8/12 or 10/15 without a copycat and 6/9 or 12/18 with one. (2,4) vs (3,3)
only says the sums are equal, 11 to 17. Branch lists come from
`line_multisets` in `segment_openers.py`.

### Checker (2026-09-14)

`2026-09-14-galaxy-copycat/copycat_rsl_solver.py` is the CP-SAT model of the
chosen ruleset: sudoku, nine copycats (one per row, column, box, nine
different digits, value = digit of the 180-degree opposite cell), region
sum lines on values, and copycat pairs as equal value multisets. It takes a
JSON setup or a SudokuMaker link (decoded through gridfind); pairs are
given with `--pair L1,L2`, sums with `--sum L1=8`. It prints the solution
count up to a limit, the first solution with copycats starred, and, when
the count is complete, every forced digit, copycat and sum.

**Board 1** (`boards/board1-three-lines.json`, three 6-cell lines, no
givens): L1 = r3c3-r3c4-r3c5-r2c5-r2c4-r2c3 is (1,4,1); L2 =
r6c4-r6c7-r4c7 is (3,3); L3 = r8c9-r8c8-r9c8-r9c7-r9c6-r9c5 is (4,2).
- L2 with L3 paired, L1 alone: feasible, 300+ solutions, so far open.
- L1 paired with L2 or L3, and all three sharing: infeasible. The segment
  model allows 8/12 with {8,8,1,2,2,3}, but the grid does not: L1's two
  singles r2c3, r3c3 both show 8, so one is digit 8 in column 3 and the
  other a copycat whose opposite, r7c7 or r8c7, is digit 8 in column 7.
  L2's column-7 segment then needs its 8 as a copycat copying r4-6c3,
  but column 3 already holds the 8. And L2's row-6 segment cannot carry
  {8,2,2}: a copycat in r6c4-6 copies r4c4-6, the same box, so the copied
  2 and the digit 2 would share box 5. L3 fails the same way through its
  box-9 quad, whose opposites lie in box 1 with L1's singles.

**Board 1, fourth line for L1.** With L2-L3 paired, searched every straight
(3,3) placement and every U-shaped (1,4,1) placement (a 2x2 block with two
singles across a border) that avoids the three lines: 31 candidates. All
straight lines infeasible. Four U-shapes feasible, each 3000+ solutions:
- r6c2-r7c2-r8c2-r8c1-r7c1-r6c1 (block in box 7, singles r6c1-2 in box 4; sample sums 9 / 11)
- r8c4-r8c3-r8c2-r7c2-r7c3-r7c4 (block in box 7, singles in box 8; 8 / 14)
- r8c7-r8c6-r8c5-r7c5-r7c6-r7c7 (block in box 8, singles in box 9; 8 / 11)
- r9c4-r9c3-r9c2-r8c2-r8c3-r8c4 (block in box 7, singles in box 8; 8 / 11)
Other 6-cell shapes (hooks, (2,4) bends) not searched.

**Board 1, all fourth lines (2026-09-14).** `find_l4_all.py` enumerated
every orthogonal 6-cell path avoiding the three lines (1729), kept the 798
whose structure the segment model allows against (1,4,1), i.e. (2,4),
(3,3) and the (1,1,4) family, and solved each with L2-L3 and L1-L4 paired.
332 feasible, none undecided: 114 of shape (4,2), 105 (2,4), 91 (3,3),
20 (1,4,1), 2 (4,1,1). Straight (3,3) lines all fail; the feasible (3,3)
ones bend. Full list in `boards/board1-l4-feasible.txt`, log in
`boards/board1-l4-search.log`.

**Board 1, L2-L3 pair by sum.** Segment model for (3,3) vs (4,2): sums 11
to 17 need no copycat (15 to 22 multisets each), 8 to 10 and 18 force one,
7 forces two. On the grid (L1 present, unpaired):
- S = 7: one multiset survives, {1,1,2,3,3,4}. L2's row-6 segment cannot
  hold a duplicate (a copycat there copies box 5 itself), so it is {1,2,4};
  L2's column-7 segment is {1,3,3} with a copycat; L3's box-9 quad is
  {1,1,2,3} with a copycat; L3's box-8 pair is {3,4}. Every value pinned,
  two copycats placed to a segment. Most forcing, but needs a clue to
  set S = 7.
- S = 8: {1,1,2,3,4,5}, {1,2,2,3,3,5}, {1,2,2,3,4,4} survive; the box-9
  quad always holds a copycat.
- S = 18: five multisets, all {.,.,.,.,9,9}; the 9,9 is always L3's box-8
  pair r9c5-r9c6, so that copycat is pinned to one of two cells with value
  9 and the other cell digit 9.
- S = 9, 10: open, 300+ distinct line fills.

**Board 1, digit coverage.** With L1's pair at {8,8,1,2,2,3} (pinned when
its partner is (2,4) or (3,3)), the L2-L3 pair covers the most new digits
at S = 16 with {1,4,5,6,7,9}: all nine digits across the four lines, the
only multiset at any sum that does. Feasible on the grid, no copycat
forced. S = 12, 13, 14, 15, 17, 18 reach eight digits; the pair alone
reaches six distinct values only for S = 11 to 17.

**Board 2** (`boards/board2-column7.json`): L1 = r6c8-r5c8-r4c8-r3c7-r2c7-r1c7
and L2 = r4c7-r9c7, both (3,3) with a segment in box 6. Never pairable:
the two box-6 segments are six distinct values, so L1's box-3 segment
r1-3c7 must repeat L2's box-6 values r4-6c7, three doubled values in
column 7, three copycats in one column. Checker: INFEASIBLE.

**Board 3** (`boards/board3-columns78.json`): L1 = r1-3c7 + r4-6c8, L2 =
r4-6c7 + r7-9c8. INFEASIBLE, same fault as board 2 in both columns.
General rule for two (3,3) lines sharing a box: the shared-box segments
are disjoint, so each line's other segment repeats the other line's
shared-box values and must avoid its rows, columns and box.

**Board 4** (`boards/board4-box6-share.json`): L1 = r1-3c7 + r4-6c8, L2 =
r4-6c7 + r1-3c6. INFEASIBLE through column 7 only (L1's box-3 segment
repeats L2's r4-6c7). Repairs tested: L1's top segment at r1-3c8 (a
straight column-8 line) or r1-3c9 both feasible, 3000+ solutions.

**Board 5** (`boards/board5-box6-row4.json`): L1 = r7-9c9 + r4-6c8, L2 =
r4-6c7 + r4c4-6. FEASIBLE, 3000+ solutions, sample sum 18. Shared box 6
makes L2's row-4 segment r4c4-6 repeat L1's r4-6c8 values, and r4c8 is
in row 4, so a copycat is forced among r4c8, r4c4, r4c5, r4c6 (checker:
all four as non-copycats is infeasible; r4c8 alone as non-copycat is
fine). Likewise L1's box-9 segment r7-9c9 repeats r4-6c7, no shared line.
If r4c8 is not a copycat: in all 39 line copycat patterns exactly one of
r4c4-6 is, with value = r4c8's digit, copied from r6c6/r6c5/r6c4. Then
r4c7 is never a copycat (row 4 spent), nor any other box-5 cell; r6c8
never is in either case.
Candidates mode (`--candidates`, every cell digit and copycat flag tested
for feasibility) on both branches of board 5, no givens:
- r4c8 not a copycat: no digit restricted anywhere; the row-4 copycat is
  one of r4c4-6, so 13 cells can never be a copycat (rest of row 4, rest
  of box 5, r6c8).
- r4c8 a copycat: no digit restricted; 20 cells can never be a copycat
  (rest of row 4, column 8 and box 6).
With no digits placed the branch moves copycats, not digits. Digit
consequences only appear once a given or a sum clue enters.
Distinct values across board 5's lines (`distinct_values.py`): min 5,
max 6, both optimal. Six cells of box 6 lie on the lines, so at most one
value repeats and the other segments copy them.
Value multisets board 5's lines can carry (`line_multisets_on_grid.py`,
full list in `boards/board5-multisets.txt`): 304 in all. 38 with six
distinct values: every even-total 6-subset of 1-9 except 123789 and
134679, sums 11 to 19. 266 with five distinct: one digit doubled, sums 8
to 22, the doubled digit anything from 1 to 9 (1 and 9 least often, 26
sets each; 3 to 7 most often, 32 each).

**Board 6** (`boards/board6-three-lines.json`): L1 = r5c8-r4c8-r4c7 +
r4c4-6 (3,3); L2 = the U-line r2c3-r2c4-r2c5-r3c5-r3c4-r3c3 (1,4,1); L3 =
r7-9c8 + r4-6c9 (3,3).
- L1-L3 pair: INFEASIBLE. L3's box-9 segment r7-9c8 must repeat L1's
  box-6 values, and two of those, r5c8 and r4c8, are in column 8: two
  doubled values in one column, two copycats in column 8.
- L2 with L1: feasible (the U-line does pair with a (3,3) line here). L2
  with L3: infeasible.
- Repair tested (`boards/board6b-col9.json`): L3 as the straight column
  9 line r4-9c9. L1-L3 feasible, sample sums 17/17. Fourth-line search
  for L2 on that board: `boards/board6b-l4-search.log`.
Board 6b fourth-line search for the U-line: 2777 paths, 1122 allowed
structures, 419 feasible, none undecided: 129 (4,2), 124 (3,3), 121
(2,4), 24 (1,4,1), 13 (1,1,4), 8 (4,1,1). List in
`boards/board6b-l4-feasible.txt`.

**Board 7** (`boards/board7-pair.json`): L1 = r5c7-r4c8-r4c7 + r4c4-6
(diagonal step r5c7 to r4c8), L2 = r7-9c8 + r4-6c9. VALID, 2000+
solutions, sample sum 13. Two forced copycat groups: r4c8's value repeats
in L2's column-8 segment, so one of r4c8, r7c8, r8c8, r9c8 is a copycat;
r4c9's value repeats in L1's row-4 segment, so one of r4c9, r4c4, r4c5,
r4c6 is. Both groups non-copycat is infeasible each; r4c8 and r4c9 both
non-copycat is fine (the copycats then sit on the other segments).
Sharper: r4c8 must be plain. A copycat at r4c8 spends row 4's copycat,
leaving r4c9 and r4c4-6 all plain, which the second group forbids.
Checker: r4c8 as copycat is INFEASIBLE. So the column-8 copycat is one
of r7c8, r8c8, r9c8, and it carries r4c8's digit.

**Board 8** (`boards/board8-pair.json`): L1 = r5c8-r5c7-r4c7 + r4c4-6,
L2 = r7-9c8 + r4-6c9. VALID, 2000+ solutions, sample sum 16. Same two
forced copycat groups as board 7 with r5c8 in place of r4c8: one of
r5c8, r7c8, r8c8, r9c8, and one of r4c9, r4c4, r4c5, r4c6. r5c8 and r4c9
both plain is fine.
Distinct values on boards 7 and 8: min 5, max 6, both optimal on each.
r4c9 as a copycat carrying r4c8's digit d: INFEASIBLE. With L1's other
box-6 values x, y and L2's p, q, equal multisets make the row-4 segment
{p,q,w} and the column-8 segment {x,y,w}; the two sum equations add to
d = w, but w is a plain digit in row 4 beside d at r4c8.

**Board 9** (`boards/board9-three-lines.json`): the user's slip, L3 drawn
as the 4-cell square r2c3-r2c4-r3c4-r3c3 (1,2,1). Partner search kept for
the record: 536 4-cell paths, 166 allowed, 28 feasible
(`boards/board9-l4-search.log`). Withdrawn ("oops").

**Board 10** (`boards/board10-three-lines.json`, 2026-09-14): L1 =
r4c4-r4c8 + r5c7, L2 = r9-7c8 + r6-4c9 (the board 7 pair), L3 = the U
r2c3-r2c4-r2c5-r3c5-r3c4-r3c3 (1,4,1). Fourth-line search for L3's
partner with L1-L2 paired: 2414 6-cell paths, 975 allowed, **333
feasible**, none undecided: 115 (4,2), 94 (2,4), 91 (3,3), 18 (1,4,1),
8 (1,1,4), 7 (4,1,1). List `boards/board10-l4-feasible.txt`, log
`boards/board10-l4-search.log`, per-partner scores
`boards/board10-l4-rank.jsonl` (`rank_l4.py`), multiset test
`boards/board10-l4-msets.jsonl`.

What every two-segment partner (300 of the 333) forces:
- **Pair sum pinned at 8.** L3's singles r2c3 and r3c3 both equal S, so
  S ≤ 9 and one of them is box 1's copycat; the box-2 quad needs S ≥ 7
  (1+1+2+3, with box 2's copycat). A two-segment partner needs 3S = 2S',
  so S is even: S = 8, S' = 12. L3 is 8 | {1,1,2,4} or {1,2,2,3} | 8 and
  always spends two copycats (box 1 and box 2). Four distinct values on
  the pair, every time.
- **(4,2) and (2,4) partners carry {8,8,1,1,2,4}**: quad {8,1,1,2} with
  a copycat, pair {8,4}. (3,3) partners carry {8,8,1,2,2,3}: triples
  {8,1,3} and {8,2,2} with a copycat. The partner's shape decides which
  of L3's two quads is drawn. 120 of the 300 also force a second copycat
  on the partner (`min_cc` 2 in the rank file).
- The 33 three-segment partners ((1,4,1) family) leave S in {7,8,9}.

Interaction with the L1-L2 pair (`boards/board10-l1sums.txt`, L1 sums
feasible, baseline with L3 unpaired is 8-22):
- r5c8-r6c8-r6c7-r6c6-r6c5-r6c4 (3,3 through boxes 6 and 5): L1 sum
  13 or 14.
- r5c2-r6c2-r6c3-r6c4-r6c5-r6c6 (3,3 through box 5): L1 sum 17 or 18.
- r5c4-r5c5-r5c6-r6c6-r6c7-r6c8 (4,2 through boxes 5 and 6): 14-18.
- r7c4-r7c5-r7c6-r7c7-r8c7-r9c7 (3,3 through box 9): 9-22, barely any.
- r6c4-r7c4-r7c5-r7c6-r8c6-r8c7 (1,4,1 through boxes 5, 8, 9): 8-22,
  none.
- r4c1-r5c1-r6c1-r7c1-r7c2-r7c3 (3,3, no shared box): 8-19.
So a partner whose 8 / 1,2,4 / 1,2,2,3 values land in box 5 or 6 is
what ties the two pairs together; box 9 partners do not.

**Board 10b, L3 moved up to r1c3** (`boards/board10b-r1c3.json`, U =
r1c3-r1c4-r1c5-r2c5-r2c4-r2c3): same search, 312 feasible
(`boards/board10b-l4-feasible.txt`). 273 partners are common to both
placements, including the three box-5/6 picks above. The r2c3 placement
keeps 60 partners the r1c3 one loses (all in boxes 5+8, 7+8, 8+9, i.e.
where L3's mirror cells sit) and the r1c3 one gains 39 (rows 7-9,
boxes 7-9). Moving up does not help: the partners that tie the two
pairs together are the same either way.

**Board 10, digit coverage across all four lines** (`boards/board10-coverage.txt`,
distinct values on L1-L4 together, min and max over solutions):
- r5c8-r6c8-r6c7-r6c6-r6c5-r6c4 (3,3): exactly 8, always. Sample L1
  3,5,6 | 1,4,9 with L3/L4 on {8,1,2,2,3}: 7 is the digit left out.
- r5c2-r6c2-r6c3-r6c4-r6c5-r6c6 (3,3): exactly 8, always.
- r5c4-r5c5-r5c6-r6c6-r6c7-r6c8 (4,2): 8 or 9.
- r7c4-r7c5-r7c6-r7c7-r8c7-r9c7 (3,3, box 9): 6 to 9.
- r6c4-r7c4-r7c5-r7c6-r8c6-r8c7 (1,4,1): 5 to 9.
- r4c1-r5c1-r6c1-r7c1-r7c2-r7c3 (3,3, no shared box): 6 to 9.

**Board 11** (`boards/board11-pair.json`, 2026-09-15): L1 = r4c4-r4c6 +
r4c7-r5c7-r6c7 (box 5 then down box 6), L2 = r9c4-r7c4 + r6c4-r6c6 (up
box 8 then along box 5). VALID, 3+ solutions at limit, pair sums 8 to
22. A copycat on the lines is forced: the two box-5 segments hold
disjoint values unless one carries a copycat, so with none each line's
box-5 triple would have to equal the other line's off-box triple, which
makes r4c4-6 and r6c4-6 the same three values inside one box.

**Board 12** (`boards/board12-three-lines.json`, 2026-09-15): board 11's
pair plus the U at r2c3. VALID with L1-L2 paired and the U unpaired
(sample sum 15); the U pairs with neither. Partner search for the U:
1525 paths, 727 allowed, **249 feasible**, none undecided (106 (2,4),
78 (3,3), 55 (4,2), 10 (1,4,1)). By boxes: 4+7 82, 8+9 67, 3+6 62,
6+9 24, 6+8+9 7, 4+5 4, 2+3+6 3. Box 5 is closed (rows 4 and 6 taken).
Files: `boards/board12-l4-feasible.txt`, `-search.log`,
`board12-l1sums.jsonl` (`other_pair_sums.py`: L1-L2 sums left per
partner, baseline 10-22), `board12-coverage.txt`.

Most forcing partners (L1-L2 sums left):
- **r3c7-r3c8-r4c8-r5c8-r6c8-r6c9** (2,4 via boxes 3, 6): L1 sum
  pinned at 18, and all nine digits appear across the four lines in
  every solution. 500+ solutions. Sample: L1 6,9,3 | 5,7,6; L2 9,6,3 |
  7,5,6; L3 8 | 4,1,2,1 | 8; L4 4,8 | 1,1,2,8.
- r9c5-r8c5-r8c6-r8c7-r9c7-r9c8 (boxes 8, 9): 17 or 19; exactly 8
  digits (6 missing).
- r7c8-r8c8-r8c7-r8c6-r8c5-r9c5 and three siblings (boxes 8, 9): 17-19;
  exactly 8 digits.
- r4c1-r4c2-r4c3-r5c3-r5c4-r5c5 and three siblings (boxes 4, 5, the
  r5c3-r5c5 tail): 14, 15, 17, 18; 8 or 9 digits.
- Everything else leaves 5 or more sums.

**Board 12, U vs the column-4 line (L2-L3), asked 2026-09-15.** INFEASIBLE
even with L1 removed and even without row/column uniqueness. Segment
model: (1,4,1) vs (3,3) needs S = 8 / 12 and only {8,8,1,2,2,3} splits
into 12-triples, {8,1,3} and {8,2,2}. The {8,2,2} triple cannot be
r6c4-6, whose copycat copies box 5 itself, so it is r7-9c4: a plain 2
in column 4 and a copycat 2 copied from r1-3c6. The U's quad {1,2,2,3}
also needs a copycat carrying 2, copied from r7c5, r7c6, r8c5 or r8c6,
which is a second digit 2 in box 8.

**Board 13** (`boards/board13-five-lines.json`, 2026-09-15): board 12
plus L4 = r3c7-r3c8-r4c8-r5c8-r6c8-r6c9 (the pick above), a fifth line
L5 = r2c1-r3c1-r4c1-r5c1 (2,2, unpaired), and a given 2 at r5c3.
INFEASIBLE, and the given is the reason: without it the board is valid
(L5 sample 7,6 | 8,5, sum 13). Candidates without the given
(`boards/board13-candidates.txt`): r5c3 is 3,5,6,7 or 9, because r5c2
is forced to 1 and the 2 of row 5 is forced into r5c4-6 (box 5 needs
its 2 there once L4's quad and L3's quad both carry 1,1,2). Forced
cells on that board: r2c3 = r3c8 = r6c9 = 8, r2c4 = 4, r3c4 = 1,
r3c5 = 2, r5c2 = 1, r4c4 = 6, r6c7 = 6, r4c8 = 1, r4c9 = 4, r6c8 = 2,
r6c6 = 1 (copycat), r8c5 = 1, r7c7 = 8, r3c7 = 4, r3c3 and r2c5 are
copycats, one of r5c8 (copycat) and r4c1/r4c2. The link's pencilled
2 at r8c5 is wrong: r8c5 is 1.

**Board 14** (2026-09-15): board 13 without the given and without L5,
pencilled r2c3 = 8, r3c8 = 8, r7c7 = 8, r8c5 = 1. VALID and all four
entries are forced (`boards/board14-candidates.txt`; same forced set as
board 13's grid, L5 changed nothing there).

**Board 17** (`boards/board17-six-lines.json`, 2026-09-15): board 14 plus
a third pair of 4-cell (2,2) lines, L5 = r8c6-r9c6-r9c7-r8c7 (boxes 8, 9)
and L6 = r2c6-r1c6-r1c7-r2c7 (boxes 2, 3). INFEASIBLE as a pair; each
line alone, both unpaired, and the pair on an empty grid are all fine.
On the board L5 can only sum 6, 9, 10 or 13 and L6 only 8, 9, 10, 11 or
16; the only sum both take at once is 10, and there L5 is always
8,2 | 1,9 and L6 always 7,3 | 7,3 (5000 sampled solutions), so the
multisets never match.

**Board 14, third pair of 4-cell lines (2026-09-15).** `find_pair4.py` on
`boards/board14-four-lines.json`: 324 orthogonal 4-cell paths off the
lines, 154 with 2+ segments, 117 feasible alone; 1516 disjoint pairs
sharing a value multiset, **448 feasible** as a pair
(`boards/board14-pair4.lines.jsonl`, `board14-pair4.pairs.jsonl`).
Ranking by forced cells: `rank_pair4.py` -> `board14-pair4.rank.jsonl`
(random-objective samples; plain enumeration only reshuffles copycat
placements and reports every cell constant).

First verified leader, **board 18** (`boards/board18-pair-r1c1.json`):
L5 = r1c1-r1c2-r1c3 | r1c4 (3,1) and L6 = r3c2 | r4c2-r5c2-r6c2 (1,3),
paired. Sum pinned at 7: singles r1c4 = r3c2 = 7, triples {1,2,4}.
Exact candidates (`boards/board18-candidates.txt`): about 50 cells
forced, the copycat digits pinned (r2c5 = 5, r3c3 = 6, r4c2 = 8,
r8c4 = 2, r6c6 = 1, r5c8 in {3,9}), r6c4 = 5, r6c5 = 7, r4c5/r4c6 = {3,9}.
Still 5000+ solutions at the cap: the remaining freedom is 3/9 pairs
across the grid and the empty box 7 / column 9 region.

**Board 14, (2,2)+(2,2) pairs, exact (2026-09-15).** Of the 448 feasible
pairs, 243 have both lines shaped (2,2). Ranking finished
(`boards/board14-pair4.rank.jsonl`, 12 random-objective samples a pair,
sample score = new constant cells over board 14's 16). The top five by
sample, each verified with `--candidates`
(`boards/board19-pair22-{1..5}.json`, `-candidates.txt`), all leave the
grid nearly solved: every one pins about 60 of 81 digits, and what is
left is one bivalue swap running through the whole grid.

| # | L5 | L6 | forced digits | left open |
|---|----|----|---------------|-----------|
| 1 | r2c1-r3c1-r4c1-r4c2 | r7c7-r8c7-r8c6-r8c5 | 63 | 18 cells, all 5/7 |
| 2 | r2c1-r3c1-r4c1-r5c1 | r7c5-r7c6-r7c7-r7c8 | 61 | 20 cells, 3/9 (three are 3/4/9) |
| 3 | r5c2-r6c2-r7c2-r8c2 | r8c6-r9c6-r9c7-r9c8 | 60 | 21 cells, 5/7 (three are 3/5/7) |
| 4 | r2c2-r3c2-r4c2-r5c2 | r8c5-r8c6-r8c7-r8c8 | 59 | 22 cells, 3/9 (some 1/3/9, 3/4/9) |
| 5 | r5c2-r6c2-r7c2-r7c3 | r7c7-r8c7-r8c6-r8c5 | 58 | 23 cells, 5/7 and 3/9 |

The sample score matched the exact count for the leader (47 new cells
both ways). The full (2,2) top 25 is in the rank file; the leaders are all
a column-1/2 vertical in boxes 1/4 or 4/7 paired with a row-7/8/9
horizontal in boxes 8/9. Cost: a third pair this shape is not a nudge,
it is the whole puzzle minus one deadly-pattern-sized swap, so it would
need one given (or a shorter/weaker third pair) to finish.

Speed for later passes: `copycat_rsl_solver.py --candidates --forced-out
boards/board14-forced.json` writes the exact forced facts (16 digits, 4
copycats, 58 non-copycats); `find_pair4.py --shape 2,2 --seed` and
`rank_pair4.py --shape 2,2 --seed` (two-stage: 4 samples on every pair,
12 on the top 30) use them. Seeding cut a pair sample from about 2.5 s to
0.2 s on a 5-pair bench with identical scores, so a full (2,2) ranking is
minutes rather than the 112 minutes the unseeded 12-sample pass took.

**Top five, one given to uniqueness? (2026-09-15)** `distinct_grids.py`
enumerates the distinct digit grids (a nogood per found grid, so copycat
shuffles are not counted) and tests every single given.

| # | distinct grids | one given suffices? |
|---|---|---|
| 1 | 2 | yes, any of the 18 open cells (one 18-cell 5/7 swap) |
| 2 | 6 | only r1c2 or r6c3 (3 or 9); a 6-cell 3/9 loop, an 18-cell 3/9 loop and a 4/9 triangle overlap |
| 3 | 4 | r1c2, r1c9, r2c2, r2c6, r3c6 or r3c9 (5 or 7); two independent loops, 6-cell 3/7 and 18-cell 5/7 |
| 4 | 6 | r1c1, r1c3, r1c7, r2c1 or r6c1 as 3 or 9; a 1/3 4-cell loop, a 1/3/4 loop and an 18-cell 3/9 loop |
| 5 | 8 | no: three independent swaps (14-cell 5/7, 4-cell 5/7 in r4-5 c3/c7, 4-cell 3/9 in r1/r4 c5-6) need three givens |

Pair 1 is the cleanest: exactly two solutions, and any one of the 18 open
cells as a given finishes it.

Re-run with the copycat placement counted as part of the solution
(`distinct_grids.py` now adds a nogood over digits and flags together):
the counts are unchanged on all five boards. Every digit grid has exactly
one copycat placement, so the single-given lists above hold for full
uniqueness, placement included.

**Why pair 1 forces so much (2026-09-15).** Each line alone does almost
nothing (`boards/board19-pair22-1-L6only-candidates.txt`: r8c6 loses
2, 3, 6; `-L5only-`: r2c1 loses 2). The pairing pins five digits and two
copycat facts, and board 14 does everything else: board 14 plus givens
r2c1 = 1, r3c1 = 9, r4c1 = 8, r8c6 = 9, r8c7 = 2, copycat r4c2, plain r7c7
(`boards/board19-pair22-1-step5.json`, no L5/L6) gives the identical
63-cell candidate grid. The chain to those seven facts:

1. r8c5 = 1 is plain, so L6 carries value 1 and L5 must too. r3c1 has no
   1, and r4c1/r4c2 cannot show 1 (box 4's 1 is r5c2; as copycats they
   show r6c9 = 8 or r6c8 = 2). So r2c1 = 1.
2. Box 1's copycat is r3c3, so r2c1, r3c1 are plain: segment 1 + r3c1,
   r3c1 in {3,5,6,7,9}.
3. r4c3 cannot be a copycat (it would show r6c7 = 6, and row 4 has 6), so
   box 4's copycat is r4c1 (shows 8) or r4c2 (shows 2). The box-4 segment
   is 8 + d or 2 + d with d in {2,3,5,7,8,9}. Equal sums: 10 (r3c1 = 9,
   {8,2}), 7 (r3c1 = 6, {2,5}) or 4 (r3c1 = 3, {2,2}). Sum 4 needs
   L6 = {1,3,2,2}: r8c6 = 3 and r7c7 worth 2, impossible (digit 8; as
   copycat it shows r3c3 in {3,5,6,7,9}). Sum 7 needs r8c6 = 6, which
   board 14 already forbids: L2's C segment (r7-9c4) carries a value 6
   (the v of the sum-18 proof), column 4 already has its 6 at r4c4, so
   that 6 is box 8's copycat copying r1c6/r2c6/r3c6, which puts column
   6's 6 in box 2. So both lines are {1,9 | 8,2}, sum 10.
4. L6: r8c6 = 9; r7c7 worth 8 means plain (not 2 either way), r8c7 = 2 plain.
5. r4c1 as the copycat is infeasible on the pair (feasible if either the
   distinct-copycat-digits rule or one-per-row/col is dropped, so the
   contradiction is a copycat-digit clash). Hence r4c2 is the copycat
   showing 2 and r4c1 = 8 plain.

Board 14 was already one push from collapse: its 16 forced digits plus
sum 18 plus four pinned copycats leave the rest hanging on column 1 and
box 4, which is exactly where these five digits land.

**(2,2) pairs that can carry a repeated value (2026-09-15).**
`find_repeats.py`: of the 243 (2,2)+(2,2) pairs, 7 share a multiset with
a repeat at the line stage and 3 survive an exact check, all with
L5 = r1c5-r1c6 | r1c7-r2c7 (boxes 2, 3) and L6 a loop around r6c1/r7c2.
Two are the same cells in a different order, so two distinct boards:

| board | L6 | multisets | solutions | forced |
|---|---|---|---|---|
| `board20-repeat-A` | r6c1-r6c2 \| r7c2-r7c1 | {3,3,9,9} or {5,5,7,7} only | 48 | 41: every 1, 2, 4, 6, 8 placed; all 40 open cells are 3/5/7/9 |
| `board20-repeat-B` | r6c2-r6c1 \| r7c1-r8c1 | {3,3,9,9}, {5,5,7,7} or {3,5,7,9} | 64 | ~39, a few 2s still open |

Pair A is forced to repeat: both segments carry the same two odd digits
as a pair, sum 12 on every option, so the line reads as two matched
pairs rather than a sum. Sample rank put these at 26 and 20 new cells,
mid-table, so they are a nudge rather than a collapse. Candidate grids in
`boards/board20-repeat-{A,B}-candidates.txt`.

**Shortest pair whose segments can shuffle (2026-09-15).** Brute force
over segment shapes and distinct-value multisets from 1-9. Up to length
6, two lines of the same shape always match segment to segment (with
distinct values): any alternative split forces two values equal, so
shuffling needs different shapes. From length 7 the same shape can
shuffle too (see below).

- Length 4: never (only with repeated values, as board 20 A).
- Length 5: (1,2,2) against (2,3). Example values {1,2,4,5,6}:
  6 | 1,5 | 2,4 against 4,5 | 1,2,6 (segment sums 6 and 9).
- Length 6, two segments each: (2,4) against (3,3), same segment sum on
  both lines. Example {1,2,3,4,5,7}: 4,7 | 1,2,3,5 against 1,3,7 | 2,4,5
  (sum 11). Also (1,2,3) against (2,4) or (3,3), and (2,2,2) against
  (2,4) or (3,3).

- Length 7 (board 14 already uses a shuffled length 6, L3 (1,4,1) against
  L4 (2,4)): **(3,4) against (3,4)** shuffles, 20 of the 36 seven-value
  multisets have two to four different splits. {1,2,3,4,5,6,7} at sum
  14 has four: 3,5,6 | 1,2,4,7; 3,4,7 | 1,2,5,6; 2,5,7 | 1,3,4,6;
  1,6,7 | 2,3,4,5. Every multiset of seven distinct digits with an even
  total has at least two splits except sixteen with one or none. Also
  (2,5) against (3,4) (5 multisets), (2,2,3) against (2,5) or (3,4), and
  (1,2,2,2) against (3,4) or (2,2,3). The full split table is in
  `boards/length7-splits.txt`.

**Board 14's residual set, enumerated once (2026-09-15).** Following
`docs/agents/grid-finder-lessons.md` ("search the smallest object"):
board 14 with its forced facts has exactly **120,000 solutions**, one
copycat placement per digit grid, enumerated to OPTIMAL in 2 minutes.
Two things made that possible. The checker's model never constrained
the digit-0 slot of its per-cell booleans (162 free variables), so
CP-SAT's solution enumeration multiplied every real solution by them:
1.59 M "solutions" in 15 minutes were 17 real ones. `copycat_rsl_solver.py`
now pins those slots (no other behaviour changes; the capped `n`
columns in the older `*.pairs.jsonl` catalogues were inflated by this
and are not counts). A nogood loop over digit grids alone managed 3,766
grids in 2.5 hours before it was replaced.

`residual.py build board.json grids.txt out.npz --seed forced.json`
takes the grid list and re-derives every placement with a DFS (one
copycat per box, one per row and column, nine different digits, the
board's lines and pairs); on board 14 the 120,000 placements it finds
are exactly CP-SAT's 120,000. Every later question is then a numpy
filter over the set: a line's region sums, a pair's multiset match, an
exact survivor count, exact forced cells. `rank_residual.py` does that
for the quad and pair searches below; both agree with the CP-SAT runs on
every row, which is the independent verification the lessons ask for.
The `.npz` is 2 minutes to regenerate (`.scratch/copycat-rsl/enum_b14.py`
then `residual.py build`) and stays out of git.

**Four (2,2) lines with a deducible pairing (2026-09-15).** Asked: drop
to four 4-cell (2,2) lines whose 2+2 pairing is unique and whose grid is
unique. `find_quad4.py` takes the 243 feasible (2,2) pairs, forms the
7,171 cell-disjoint 4-sets, and solves each with a matching variable
(AB|CD, AC|BD, AD|BC). Results (`boards/board14-quad4.{0,1}.jsonl`,
exact re-rank in `boards/board14-quad4.rank.jsonl`):

- 66 feasible 4-sets; in every one only a single pairing admits any
  solution. 21 have a unique solution in digits and placement.
- The lines do the work, not the pairing: with the four lines' region
  sums alone and no pairing, the 66 sets leave at most 41 of the 120,000
  solutions (median 5), and the 21 unique ones at most 26.
- In 19 of the 21 the wrong pairings are already killed by segment sums.
  Only two sets keep a sum-compatible wrong pairing: r1c5-r1c8 (row),
  r3c1-r3c2 | r4c2-r4c1 (or reversed), r5c2-r8c2 (column), r5c5-r5c4 |
  r5c3-r6c3; lines alone leave 3 solutions, all three pairings
  sum-compatible in some, AC|BD the only one that holds (values 3719 /
  3728 / 1937 / 8273).

So the pairing deduction is a small last step, the same "no interesting
ambiguity" as the single (2,2) pairs: four lines of two sums each pin
the grid before the pairing matters.

**Two (3,4) 7-cell lines with shuffled splits (2026-09-15).** Asked: if
the 4-cell lines go, can board 14 take two (3,4) lines whose 3-segments
carry different multisets? `find_pair7.py` (4 shards, exact value-vector
enumeration per line, `boards/board14-pair7.lines.{0..3}.jsonl`, 514
lines) then a pair stage with the "small segments differ" constraint:
27,976 candidate pairs, **2,255 feasible**, all confirmed by the residual
filter. Exact rank in `boards/board14-pair7.rank.jsonl`:

- 341 pairs give a **unique** puzzle (one residual solution), all 81
  digits forced, and the two 3-segments differ in that solution.
- 2,116 of 2,255 pairs are shuffled in every surviving solution, so the
  shuffle is a property of the placement, not luck of the sample.
- Survivor counts: 1 (341 pairs), 2 (472), 3 (182), 4 (288), then a long
  tail; nothing over a few dozen.
- The unique ones sit almost entirely in the corners: 187 pair a line
  through boxes 4-7 with one through 8-9, 117 pair boxes 1-4 with 8-9;
  the rest spread over 2-3 with 4-7 or 8-9, and 1-2 with 4-7 or 8-9.
- Example (first in rank order): X = r1c1-r1c2-r2c2 | r3c2-r4c2-r5c2-r6c2
  with 3-segment {1,8,9}, Y = r7c6-r7c5-r8c5 | r8c6-r8c7-r9c7-r9c8 with
  3-segment {2,7,9}; same seven values, different split, unique grid.

Answer to the question: yes, two (3,4) lines fit, in hundreds of ways,
and 341 of them are unique puzzles in which the split genuinely
shuffles. Next: pick by shape and box coverage, then verify the chosen
board with `copycat_rsl_solver.py --candidates` and hand-check the break-in.
