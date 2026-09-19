# Counting shaded, all visible and orthogonally connected

Target: a grid whose shaded cells are all visible (every shaded cell shows its
shaded-neighbour count as a given), those givens alone make the sudoku unique,
and the shaded cells form one orthogonally connected region. The 8-given
requirement is off for this hunt.

Prior state: 234 verified examples with no connectivity requirement
(`docs/research/counting_shaded/examples-verified.jsonl`, 25-33 shaded cells). Zero of them
are connected, so they validate nothing about this target.

## The ceiling: 26 shaded cells, proven

`finders/counting_shaded/joint.py --maximize` puts the digits, the shaded cell booleans, the
all-visible link and exact flow connectivity in one model and maximizes the
shaded cell count. **OPTIMAL at 26 shaded cells in 50s.** No connected all-visible shaded cell
set of 27 or more exists on any grid.

That is the number that decides how hard this is. Against the 234
unconstrained examples:

| shaded cells | 25 | 26 | 27 | 28 | 29 | 30 | 31 | 32 | 33 |
|---|---|---|---|---|---|---|---|---|---|
| unique examples | 1 | 8 | 17 | 41 | 51 | 60 | 40 | 15 | 1 |

Only **9 of 234** sit at 26 or below. Connectivity confines the search to the
thin tail of the distribution where uniqueness is already rarest, and then adds
a constraint on top. Not proven impossible; the hardest corner of the space.

The first 26-cell shape found had **2 solutions** — one short of the target,
which is why the band is worth enumerating rather than abandoning.

## Connectivity: flow beats lazy cuts here

Both encodings are in `finders/counting_shaded/connected.py` behind `--conn flow|lazy`.

| encoding | result |
|---|---|
| lazy flood-fill cuts | 2073 cuts in 120s, never returned a connected shape |
| single-commodity flow | connected shape in 77s |

Lazy cuts lose because each cut kills one component layout and the solver finds
another — the whack-a-mole failure the grid-finder lessons warn about, where a
cut has to kill a family to pay for itself. Flow is one encoding, solved once.
The earlier ruling to use lazy cuts was for the pinned-infeasibility question,
which is unaffected.

## Shape-only search cannot see solvability

`connected.py` returns connected shapes with admissible givens and **0 sudoku
solutions**: no grid completes them. The distinct-givens rule is necessary, not
sufficient. Any connected hunt has to hold the grid as a variable, which is
what `joint.py` does — every shape it returns is solvable by construction,
the grid being the witness.

## A sampler that only samples one grid (recorded so it is not rebuilt)

`finders/counting_shaded/gridfirst.py` fixes a solved grid, then solves for a shaded cell set
inside it. Sound idea, broken generator: `random_grid()` builds grids by
relabelling, in-band row moves, band and stack swaps and transposition of one
`BASE` grid. Those are exactly the sudoku-preserving symmetries, so every
"random grid" it produces is isomorphic to `BASE` — one equivalence class out
of 5.47 billion.

The shaded-count constraint is not invariant under those symmetries, so the
constraint does vary and the bug hides: 38,064 grids reported a maximum
connected shaded set size of 9, with 37,576 admitting none at all. **Those
numbers are artefacts of one orbit and must not be quoted.** The joint model
proves the true ceiling is 26.

Lesson, general: a grid sampler built from the puzzle's own symmetry group
samples one orbit, not the space. Check a sampler by asking whether two of its
outputs are isomorphic, not whether they look different.

## What "all visible" buys, and why this is the easiest variant

All shaded cells visible means the puzzle reduces to a plain sudoku whose givens are
the shaded cell digits. Any two solutions agree on every shaded cell cell, since those
digits are givens, so the shaded cell rule has the same truth value in all of them
and cannot separate a true solution from a false one. That is why
`count_solutions` is a plain bitmask sudoku solver with no shaded cell logic in it:
correct, not an oversight.

The reason visibility matters is sharper than "it supplies clues". **A shaded cell
marker only becomes a given digit if the shaded cell status of its entire 3x3
neighbourhood is known**, because the digit is that neighbourhood's shaded cell
count. Under the original rule, where some shaded cells are hidden, a visible shaded cell
is a marker whose value the solver cannot compute -- not a given at all.

So all visible is the maximally clued variant, not the hardest: every shaded cell
carries a digit precisely because nothing is hidden. Scarcity of connected
unique examples is a real property of the target, not an artefact of choosing
a hard variant, and moving to the hidden-shaded rule would make it strictly
worse -- fewer clues, and the surviving clues stop being digits.

## The size window: 17-21, closed on both sides by proof

Every shaded cell digit is a neighbour count, so it lies in 1-8 and **9 can never
appear on a shaded cell**. Combine that with a standard fact: a sudoku whose givens
omit two or more digits always has several solutions, because swapping the two
missing digits throughout any solution relabels it into another solution that
agrees with every given. So a unique puzzle needs at least 8 distinct given
digits -- and since 9 is unavailable, **all eight of 1-8 must appear**. No
slack.

That is cheap to post as a constraint (`joint.add_all_digits`) and it decides
the whole question. Asking the solver one size at a time, with symmetry
breaking on:

| shaded cells | all eight digits possible? | basis |
|---|---|---|
| <=16 | irrelevant | below the 17-given minimum (all-visible reduces to plain sudoku) |
| 17 | yes | witness, 5s |
| 18 | yes | witness, 23s |
| 19 | yes | witness, 6s |
| 20 | yes | witness, 21s |
| 21 | yes | witness, 13s |
| 22 | **no** | INFEASIBLE |
| 23 | **no** | INFEASIBLE |
| 24 | **no** | INFEASIBLE |
| 25 | **no** | INFEASIBLE |
| 26 | **no** | INFEASIBLE |
| >=27 | no configuration at all | INFEASIBLE, three encodings |

**A unique connected all-visible counting shaded puzzle has between 17 and 21 shaded cells, or
does not exist.** The wall at 22 is structural: a connected blob that large has
a high-count interior, so its digits crowd into 5-8 and the low counts vanish.
A big connected region and a 1 or 2 on it are incompatible.

This also closes the earlier hunt at 25-26 -- which the corpus had suggested was
the only viable band, itself an artefact of a generator floor. See the decision
log, entries 9 and 15.

## No connected all-visible-unique shading exists under sudoku rules (exhaustive)

Every size in the 17-21 window enumerated to exhaustion with
`finders/counting_shaded/shapeenum.py --symmetry` (native CP-SAT enumeration,
shape-determined BFS connectivity, one of each shape's 8 images, all eight
digits required, the C counter judging each shape at cap 2):

| size | shapes (up to symmetry) | with a grid | unique | time |
|---|---|---|---|---|
| 21 | 13 | 4 | 0 | 50 s |
| 20 | 16 | 6 | 0 | 42 s |
| 19 | 34 | 12 | 0 | 52 s |
| 18 | 32 | 16 | 0 | 60 s |
| 17 | 26 | 12 | 0 | 76 s |

With the theorem sides (below 17 too few givens; above 21 no shape carries
all of 1-8) this closes the question: **no orthogonally connected shading
exists whose neighbour counts, taken as the only givens, force a sudoku.**
Since any counting-shaded puzzle's solution shading must have that property
(a second grid agreeing on the shaded cells is a second solution), no
counting-shaded puzzle exists under sudoku rules. Solver caveat as
throughout: three CP-SAT encodings agree; no second engine yet (#506).

Solve-then-forbid on the same size 21 found 70 of the at most 104 images in
10 minutes on 8 workers without finishing; native enumeration is the tool.

## Latin squares (no boxes), r9c1 + r9c2 pinned, all eight digits

Chris asked for the high-count cases again as Latin squares. `--latin` on the
C counter, the joint model and `shapeenum.py` drops the box constraint
everywhere (the C side gives every cell its own box, so the box masks are
vacuous; verified on a shape whose only clash is inside a box). Native
enumeration, one worker, each size exhausted in under 25 s:

| size | shapes | with a grid | unique |
|---|---|---|---|
| 21 | 14 | 14 | 0 |
| 22 | 22 | 22 | 0 |
| 23 | 16 | 16 | 0 |
| 24 | 48 | 48 | 0 |
| 25 | 63 | 60 | 0 |
| 26 | 86 | 83 | 0 |
| 27 | 95 | 70 | 0 |
| 28 | 130 | 102 | 0 |
| 29 | 137 | 100 | 0 |
| 30 | 128 | 83 | 0 |

Two things differ from sudoku: the counts grow with size rather than
collapsing (the sudoku ceiling of 26 is a box effect), and a Latin square is
far looser, so a unique completion from 20-30 givens is even less likely.
None found. Continued upward until a size came back empty:

| size | shapes | with a grid | unique |
|---|---|---|---|
| 31 | 101 | 59 | 0 |
| 32 | 61 | 24 | 0 |
| 33 | 33 | 12 | 0 |
| 34 | 17 | 4 | 0 |
| 35 | 2 | 0 | 0 |
| 36 | 2 | 0 | 0 |
| 37 | 0 | - | - |

**Under Latin rules with r9c1 + r9c2 pinned: largest shading with a grid is
34; no size 21-36 carries a unique one.** Every size exhausted in about 20 s.

## Symmetry

The symmetry group is the 8 dihedral images and nothing else: they preserve the
sudoku houses and both adjacencies, king for counting and orthogonal for
connectivity. Band and stack swaps preserve houses but scramble adjacency;
digit relabelling is not a symmetry because digits are counts.

`joint.add_symmetry_breaking` keeps only the lexicographically smallest image,
verified against explicit enumeration (`joint.py --check-symmetry`): 300/300
agreement, and 200/200 orbits keep exactly one representative, which is the
property that makes it lossless. **Never combine it with pinned cells** -- a pin
already fixes the orientation, so demanding canonical form on top forbids real
solutions. `build()` raises rather than allowing the combination.

Before it existed the corpus carried 29 symmetric duplicates in 197 rows.

## Pinned cells: r9c1 + r9c2

| | max shaded cells | digits | solutions |
|---|---|---|---|
| connected | 22 (proved) | 1-7, no 8 | 1000+ |
| connected, all digits required | 21 (proved) | 1-8 | 1000+ |
| not connected | **34** (proved) | 1-8 | **9** |

The unconnected 34 is the closest anything has come to unique. Connectivity
costs 12 shaded cells here, and at the maximum it also costs the digit 8, which alone
makes that configuration permanently non-unique.

Separately, r9c1+r9c2+r9c8 with r7c4 banned is infeasible outright -- no valid
grid at all, at any shaded cell count, connected or not. That is an existence result,
not a uniqueness one: `recheck_pins.py` posts only necessary conditions (counts
1-8, digits distinct within each house) and so is a relaxation of the real
problem, which makes its INFEASIBLE carry up to the real problem.

Re-asked 2026-09-16 under the shown-shading-only rules (`joint.build` with
`force`/`ban`, 4 workers, each answer in under 3 s). The ban is not what kills
it; the pair r9c1 + r9c8 already is, and only under connectivity:

| pins (all shaded) | connected | result |
|---|---|---|
| r9c1 r9c2 | yes | feasible |
| r9c1 r9c2 r9c8 | yes | INFEASIBLE |
| r9c1 r9c2 r9c8 | no | feasible, 23 shaded |
| r9c1 r9c2 r9c8, r7c4 unshaded | no | INFEASIBLE |
| r9c1 r9c8 | yes | INFEASIBLE |
| r9c2 r9c8 | yes | INFEASIBLE |
| r9c1 r9c5 | yes | feasible, 21 shaded |
| r9c1 r9c7 | yes | INFEASIBLE |
| r9c1 r9c9 | yes | INFEASIBLE |

A connected shading cannot hold two bottom-row cells six or more columns
apart. Not hand-proved; the solver's INFEASIBLE is the record.

### The 22-cell maximum for r9c1 + r9c2, the grid itself

`joint.build(2, 26, maximize=True, force=(72, 73))`, 8 workers, OPTIMAL in 8 s
with objective 22 and bound 22. Checked by an independent rule-text checker
(sudoku, connectivity, digit == shaded king-neighbours). `*` marks shaded.

```
3  1  2  9  4  6  7  8  5
6  7  4  3  8  5  9  2* 1
5  9  8  7  1  2* 4* 3* 6
4  6  3  2  9  8  5* 1  7
7  8  5  1  3* 4* 2* 6  9
9  2* 1  5* 6* 7  8  4  3
8  4* 7* 6* 5* 3* 1* 9  2
1  5* 6* 4* 2  9  3  7  8
2* 3* 9  8  7  1  6  5  4
```

shape (0-based cell indices): 16 23 24 25 33 40 41 42 46 48 49 55 56 57 58 59
60 64 65 66 72 73. Digits 1-7 only; no 8, as the table above says.

### No unique shading exists under r9c1 + r9c2 (exhaustive)

Question (Chris): the largest connected shading containing r9c1 and r9c2 whose
digits, as the only givens, force the sudoku. Answer: **none, at any size.**

- 22 and above: no shape carries all of 1-8 (table above), so none is unique.
- 16 and below: fewer givens than the 17 minimum for a plain sudoku.
- 17-21: `finders/counting_shaded/pinharvest.py --enumerate` (joint model, all
  digits required, solve-then-forbid until INFEASIBLE) exhausts every size in
  under 2 s each. Re-counted by the independent distance-label encoding: same
  shapes.

| size | shapes with all of 1-8 | unique |
|---|---|---|
| 21 | 2 | 0 |
| 20 | 2 | 0 |
| 19 | 0 | - |
| 18 | 0 | - |
| 17 | 0 | - |

The four shapes are one family: a blob in rows 4-9, columns 1-7, differing by
r5c1 vs r6c1 and by r7c8 present or not (0-based indices 36/45 and 61). Each
has 1000+ sudoku solutions. Shapes on record in
`counting_shaded/pinned-r9c12-alldigits.jsonl`.

A 21-cell witness with an 8 (r6c4 ringed), 1000+ solutions:

```
5  6  8  2  9  4  1  3  7
4  7  1  3  8  6  5  9  2
9  2  3  5  1  7  6  4  8
8  1  9  4* 3* 2  7  6  5
2* 4* 6* 7* 5* 9  3  8  1
3  5* 7* 8* 6* 1  9  2  4
7  8  5* 6* 4* 3* 2* 1* 9
6  9  4* 1  2  5  8  7  3
1* 3* 2* 9  7  8  4  5  6
```

## Method, and why

Following the idiom that produced the 234 examples and the repo's other
working finders: CP-SAT states everything except uniqueness, and uniqueness is
decided outside it by the bounded bitmask counter. `finders/counting_shaded/jointharvest.py`
enumerates joint seeds by solve-then-forbid within a fixed shaded cell count and
counts solutions for each.

Note on reading its output: CP-SAT `UNKNOWN` is a timeout, not a proof that
the size band is exhausted. Only `INFEASIBLE` proves that.

## 6x6 sudoku (2x3 boxes): six unique puzzles exist

Chris (2026-09-16): "Can we try exploring 6x6?", sudoku with 2x3 boxes, and
"just 5 distinct" counts on the shading (the uniqueness floor for a 6-digit
grid; a sixth distinct digit is allowed but not required). Tool:
`finders/counting_shaded/gridenum.py`, the shape-only native enumeration of
`shapeenum.py` generalised to an N x N grid with any box shape, plus a Python
bitmask counter (checked against CP-SAT on 200 random givens sets, zero
mismatches). Symmetry breaking keeps one of the 4 images that preserve 2x3
boxes (half turn and the two axis flips). Every size from 8 (the 6x6 givens
floor) to 36 exhausted, each in about a second.

| shaded | shapes | with a grid | unique |
|---|---|---|---|
| 8 | 62 | 58 | 0 |
| 9 | 85 | 73 | 0 |
| 10 | 59 | 38 | 0 |
| 11 | 58 | 32 | 0 |
| 12 | 66 | 19 | **2** |
| 13 | 54 | 16 | **1** |
| 14 | 40 | 11 | **3** |
| 15 | 3 | 0 | 0 |
| 16 | 7 | 0 | 0 |
| 17 | 6 | 1 | 0 |
| 18-36 | 0 | 0 | 0 |

So under 6x6 sudoku rules, unlike 9x9, the shading alone can force the grid:
six shapes up to symmetry, at 12, 13 and 14 shaded cells, none larger (17 is
the largest shading with any grid at all). Each of the six was re-checked by an
independent CP-SAT model written from the rule text: shading fixed, digits
free, exactly one grid, every shaded digit equal to its shaded king-neighbour
count, shape orthogonally connected. Shapes with their grids in
`counting_shaded/six-by-six-unique.jsonl`; sheet
`counting_shaded/six-by-six-unique.png` (top row: the two 12s and the 13;
bottom row: the three 14s).

Caveat: these are all-visible uniques. A playable puzzle shows only some
shaded cells, and which subset still forces the shading is the next question.

## 6x6 with both colours connected and no 2x2 of either: nothing exists

Chris (2026-09-16): "do any solutions at all exist under the condition that
all shadeds are connected, all unshadeds are connected, and no 2x2 of either",
6x6 only. `gridenum.py` gained `--unshaded-connected` (a second BFS-distance
connectivity on the complement) and `--no-2x2` (every 2x2 window holds both
colours). Sizes 8-36 exhausted with symmetry: 0 shapes at every size, each in
under a second. The distinct-count floor is not the cause; isolating the rules
in one CP-SAT model (size free, 1-35):

| rules on the shading | result |
|---|---|
| no 2x2 + shaded connected, no counting | feasible (25 cells) |
| no 2x2 + both connected, no counting | feasible (18 cells) |
| no 2x2 + shaded connected + counts 1-6 on shaded cells, no house rule | feasible (24 cells) |
| no 2x2 + shaded connected + counts + distinct within row/column/box | INFEASIBLE |
| unshaded connected only (no 2x2 rule), 5 distinct | feasible at 7 sizes |

So the no-2x2 rule and the house-distinct rule are incompatible on 6x6 with
counting-shaded digits: a shading with no solid 2x2 is thin, its cells mostly
count 2 with ends counting 1, and every row must still hold distinct counts.
All verdicts are CP-SAT (single encoding); no second engine.

### Dropping the boxes changes nothing

Chris: "what about dropping the region part". `gridenum.py --latin` drops the
box from the house rule and from the counter (counter checked against CP-SAT
on 150 random Latin givens sets, zero mismatches; the first Latin sweep was
invalid because a formatter had collapsed `same_house` before the edit landed,
and was rerun after the fix). 6x6 Latin, both colours connected, no 2x2 of
either, sizes 8-30 exhausted with symmetry: 0 shapes at every size. The
free-size model without boxes agrees: no 2x2 + shaded connected + counts 1-6
+ distinct within row and column is INFEASIBLE on its own; the row/column
rule alone already clashes with the thin shapes no-2x2 forces.

### Both colours connected, 2x2 allowed

Chris: "what if we drop 2x2". `gridenum.py --unshaded-connected` without
`--no-2x2`, sizes 8-30 exhausted with symmetry, at least 5 distinct counts.

| shaded | sudoku 2x3: shapes / with a grid / unique | Latin: shapes / with a grid / unique |
|---|---|---|
| 5-6 | (below the 8-given floor) | 0 |
| 7 | (below the floor) | 10 / 10 / 0 |
| 8 | 45 / 43 / 0 | 36 / 36 / 0 |
| 9 | 53 / 46 / 0 | 41 / 41 / 0 |
| 10 | 19 / 13 / 0 | 26 / 26 / 0 |
| 11 | 19 / 16 / 0 | 19 / 19 / 0 |
| 12 | 2 / 2 / 0 | 6 / 6 / 0 |
| 13 | 1 / 1 / 0 | 5 / 5 / **2** |
| 14-30 | 0 | 0 |
| 31-36 | (not run) | 0 |

Requiring the unshaded cells to be connected too keeps shadings alive (the
unshaded region needs a path around the shape), but under sudoku boxes none
of them forces the grid: the six 12-14 uniques above all cut the unshaded
region in two. Under Latin rules two 13-cell shadings are all-visible unique,
re-checked by the independent CP-SAT model (rows and columns only). Shapes with
grids in `counting_shaded/six-by-six-latin-both-connected-unique.jsonl`, sheet
`counting_shaded/six-by-six-latin-both-connected-unique.png` (outer border only,
no box lines). Latin sizes 5-36 are all exhausted, so these two are the
complete list of all-visible-unique both-connected 6x6 Latin shadings, up to
the 8 dihedral images.

### The two Latin uniques as cave-clue puzzles

Chris: "circle all valid cave clues" on both colours, then "either of those
unique by just some cave clues being given". A cave clue is a cell whose digit
equals the number of same-colour cells it sees orthogonally, itself included.
Sheet `counting_shaded/six-by-six-latin-cave-clues.png`.

Puzzle model (`.scratch/counting_shaded/six/tools/cave_unique.py`, CP-SAT,
solutions are grid+shading pairs, solve-then-forbid at cap 2): Latin square
1-6; shaded and unshaded each orthogonally connected; a shaded cell's digit is
its shaded king-neighbour count; every given digit is a cave clue in whichever
colour it lands. No shading is shown and no distinct-count floor is imposed.
With no clues the model has 3+ solutions, and with any single clue 3+, so it
is not over-constrained.

| grid | cave clues | unique from all | minimal unique subsets |
|---|---|---|---|
| 1 | r1c3=6, r4c4=5, r4c5=4, r6c1=2, r6c3=4 | yes | {r4c5, r6c1}; {r1c3, r4c4, r4c5}; {r1c3, r4c4, r6c1}; {r1c3, r6c1, r6c3}; {r4c4, r4c5, r6c3}; {r4c4, r6c1, r6c3} |
| 2 | r2c5=2, r4c5=4, r5c3=5, r6c3=4 | yes | {r2c5, r6c3} |

Both puzzles are unique from two given digits and nothing else shown.

### Cave marks without digits

Chris: "no without givens in the clues". Same model, but a marked cell only
promises that its digit is a valid cave clue; the digit itself is not shown
and no shading is shown.

| grid | marks | unique from all marks | notes |
|---|---|---|---|
| 1 | r1c3, r4c4, r4c5, r6c1, r6c3 | **yes** | minimal: {r1c3, r4c4, r4c5, r6c1} and {r1c3, r4c4, r4c5, r6c3}; no 3-mark set works |
| 2 | r2c5, r4c5, r5c3, r6c3 | no (4+ solutions, the others on a different 8-cell shading) | unique once r6c3 is also shown shaded |

So grid 1 is a puzzle with four circled cells and nothing else; grid 2 needs
its four marks plus one shaded cell revealed.

## 6x6, self-counting variant

Chris: "also count ourselves in the count", 6x6 only. `gridenum.py --self`:
a shaded cell's digit is its shaded king-neighbour count plus one. Sizes 5-36
exhausted with symmetry, at least 5 distinct digits; shapes / with a grid /
unique, only non-empty sizes shown.

| shaded | sudoku 2x3 | sudoku, both connected | Latin | Latin, both connected |
|---|---|---|---|---|
| 7 | 14 / 12 / 0 | 12 / 11 / 0 | 12 / 12 / 0 | 10 / 10 / 0 |
| 8 | 36 / 32 / 0 | 23 / 21 / 0 | 26 / 26 / 0 | 17 / 17 / 0 |
| 9 | 30 / 27 / 0 | 11 / 10 / 0 | 18 / 18 / 0 | 6 / 6 / 0 |
| 10 | 24 / 20 / 0 | 3 / 3 / 0 | 20 / 20 / 0 | 4 / 4 / 0 |
| 11 | 38 / 20 / 0 | 11 / 9 / 0 | 34 / 30 / 0 | 9 / 9 / 0 |
| 12 | 10 / 1 / **1** | 0 | 23 / 16 / 0 | 0 |
| 13 | 1 / 0 / 0 | 0 | 4 / 2 / 0 | 0 |
| 14 | 6 / 5 / **1** | 0 | 9 / 6 / 0 | 0 |

Two uniques, both under plain sudoku boxes: the 12-cell shape [3, 9, 10, 11,
15, 20, 21, 22, 26, 30, 31, 32] and the 14-cell shape [3, 4, 5, 7, 9, 13, 14,
15, 16, 20, 26, 32, 33, 34], the same two cell sets that were unique under
the plain count (every digit one higher). Nothing under both-connected or
Latin.

### The two Latin uniques cut into six regions

Chris: "do either of the 2 unique LS ones we found before permit a division
into 6 irregular regions". Both do, abundantly: CP-SAT (region labels,
six cells each, every digit once per region, BFS-distance connectivity,
regions ordered by first cell) found 50 partitions for each grid before the
cap, the trivial rows and columns among them. Example irregular partitions:

```
grid 1              grid 2
A A A A A A         A A A A A A
B C D D D D         B B B B B B
B C C D D E         C C C C C C
B C E E E E         D D D D E E
B C C F F E         D D E E E E
B B F F F F         F F F F F F
```

Tool `.scratch/counting_shaded/six/tools/regions.py`; the first 50 partitions
of each grid in `.scratch/counting_shaded/six/regions.json`.

## 6x6: two corners on one side cannot both be shaded

Chris: "find me any solution where there is a given shaded in r6c1 and r6c6,
and where one given somewhere (not on the given shadeds) makes it unique",
then "what about r1c1 and r6c1". Neither pair admits any solution at all.

- Puzzle model (`.scratch/counting_shaded/six/tools/pinpuzzle.py`: digits and
  shading jointly, shaded connected, r6c1 and r6c6 shaded, no distinct-count
  floor): 0 solutions with no given, under sudoku 2x3 with the plain count and
  with the self count.
- Shape-only encoding (`gridenum.build` with the pair forced, min_distinct 0),
  every size 2-36: INFEASIBLE for sudoku and Latin, plain and self count, for
  r6c1+r6c6 and for r1c1+r6c1.
- Cause: the digit cap. Rows-only distinct is feasible, columns-only is
  feasible, rows and columns with digits allowed up to 8 is feasible, rows and
  columns with digits capped at 6 is INFEASIBLE. Joining two corners of one
  side with a connected shading forces either a house clash or a cell with 7+
  shaded neighbours.
- Feasible partners for r6c1 (sudoku, plain count, at least 5 distinct, sizes
  8-18): every cell except r1c1, r1c6, r2c1 and r6c6.

### 7x7 Latin: the same two corners are feasible, at one size only

Chris: "is that also true for a 7x7 latin square?" Shape-only model
(`gridenum`, geometry 7 with Latin mode, pair forced, no distinct floor),
sizes 2-49: r7c1+r7c7 is feasible at size 17 and at no other size; r1c1+r7c1
likewise only at 17. Witness (digits are counts, 7 allowed now):

```
. . . . . . .
. . . . . . .
. . . . . . .
. . 3 5 4 . .
. . 6 7 5 4 2
. 5 7 6 . . 3
2 4 5 3 . . 1
```

The extra digit (7) and the extra column are what the 6x6 argument lacked:
the two corner wedges still collide in the bottom rows, but a 7 absorbs the
cell that had to see seven shaded neighbours.

### 8x8 Latin: feasible at sizes 21, 23 and 24

Same shape-only model, geometry 8 Latin, sizes 2-64: r8c1+r8c8 feasible at
21, 23, 24 only; r1c1+r8c1 the same. Size-21 witness:

```
. . . . . . . .
. . . . . . . .
. . . . . . 2 .
. . . . 4 5 3 .
. . 3 4 5 6 . .
. 5 6 . . 3 4 2
4 6 5 2 . . . 3
3 4 . . . . . 1
```

### 9x9: infeasible again, Latin and sudoku alike

Chris: "9x9?" then "any 9x9 with sudoku regions?". Shape-only model, geometry
9, pairs r9c1+r9c9 and r1c1+r9c1, sizes 2-50, no distinct floor, 120 s per
solve: every size INFEASIBLE, none timed out, for Latin and for sudoku 3x3.
The Latin verdict was cross-checked with the flow-connectivity encoding
(`shapeenum.build`, Latin, sizes 10-44): also INFEASIBLE throughout.
Scripts and logs in `.scratch/counting_shaded/corners9/`.

| grid | same-side corners both shaded |
|---|---|
| 6x6 | never |
| 7x7 Latin | size 17 only |
| 8x8 Latin | sizes 21, 23, 24 |
| 9x9 Latin | never (sizes 2-50) |
| 9x9 sudoku | never (sizes 2-50) |

Not monotone in the grid size: on 9x9 the digit cap no longer binds (counts
are at most 8) but the corners are eight columns apart, so the connecting
band is longer and puts more cells with near-equal counts into each row.

### r6c1 + r6c5 shaded on 6x6

Chris: "can you show a 6x6 where r6c1 and r6c5 are both shaded". Shape-only
enumeration with the pair forced, no distinct floor, sizes 4-24. Sudoku 2x3:
one shape (size 12) and it has no grid. Latin: two shapes at 12 and two at 13,
all four with a grid (none unique), plus two grid-less shapes at 17. Sheet
`counting_shaded/six-by-six-r6c1-r6c5.png` (Latin, outer border only), shapes
in the doc's scratch folder `.scratch/counting_shaded/six-pin3034/`.

### r2c6 + r6c1 shaded on 6x6

Chris: "r2c6 and r6c1?". Same enumeration (`.scratch/counting_shaded/six/tools/pairsheet.py`),
pair forced, no distinct floor, sizes 4-24. Sudoku 2x3: 10 shapes, 4 with a
grid, one unique (the 12-cell shape [3, 9, 10, 11, 15, 20, 21, 22, 26, 30,
31, 32], already on the unpinned unique list). Latin: 103 shapes, 38 with a
grid, four unique, all at 19 cells. Sheet
`counting_shaded/six-by-six-r2c6-r6c1.png`: top row sudoku (the unique first),
bottom row the four Latin uniques.

### Counting circles on 6x6: none

Chris: "are there any that follow counting circle rules?", read as the
Counting Circles rule: a digit in a shaded cell says how many shaded cells
hold that digit. Since shaded digits are the counts, it is a property of the
shape. None of the 694 6x6 shapes with a grid on record satisfy it (most miss
on 3-5 digits). Searched directly as a constraint in the shape model, sizes
2-36, no distinct floor: 0 shapes under sudoku 2x3, Latin, and both with the
unshaded cells connected. Still 0 with connectivity dropped and with digits
allowed up to 8. Dropping the row/column distinctness makes it trivially
feasible (two 2s and four 4s in a 2x4 block), so the house rule is what
forbids it: digit d must sit d times in d different rows and d different
columns while each of those cells sees exactly d shaded neighbours, and on a
6x6 that never closes. Probe output in `.scratch/counting_shaded/six/cc_probe.txt`.

### Counting circles on 7x7 and 8x8

7x7 Latin: 0 shapes, every size exhausted (`.scratch/counting_shaded/six/cc7.txt`).
8x8 Latin: stopped by Chris after 33 minutes with no shape found and no
exhaustion proof (the script logged only hits, so the size reached is
unknown); the 8x8 2x4-box run never started. Open, not disproved.
