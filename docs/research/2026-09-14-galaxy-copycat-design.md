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
| Copycat opposite a copycat | values swap, definition recurses | impossible: at most one per galaxy |
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
- A perfect digit match means no copycat on the pair, or two copycats at
  mirror positions swapping each other. Forbid "a copycat opposite a copycat"
  to keep the reading single-valued.
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
