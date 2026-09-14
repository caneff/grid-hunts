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
Lines chosen. The line pairs are **not** mirror images; the mirror lives
only in the copycat rule.

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
