# Copycat sudokus on LMD — rulesets, setters, and pencil-puzzle hybrids

Date: 2026-09-14. Companion to `2026-09-14-puzzle-genre-survey.md` and
`2026-09-14-lmd-hybrid-scan.md`. Scripts: `finders/copycat-scan/`.

## Method

- LMD has no Copycat tag and no title search that works without a login, so
  the catalogue comes from three sources: (1) every one of Scojo's 196
  published puzzles (author list `Benutzer/eingestellt.php?name=Scojo`, 10
  pages), each puzzle page fetched and its rules text searched for "copycat";
  (2) web search for "copycat" on logic-masters.de to find other setters;
  (3) the series list Scojo keeps on every Copycat puzzle page.
- One request per 10 s, no retries. Pages live in `.scratch/copycat/pages/`
  (gitignored). `parse_copycat.py` classifies each page.
- Result of source (1): all 196 pages read (one 503 on 000GR2 "Target
  Acquired", refetched once by hand, no copycat rule). No Scojo puzzle uses
  the modifier under a title without "Copycat" other than Déjà Vu.
- "Pencil hybrid" below means the rules require the solver to shade cells,
  draw a loop or path, or divide the grid into regions. Line, dot and cage
  variants are not pencil hybrids.

## Two different rulesets share the name

**1. Copycat Cells — Scojo's modifier (first puzzle 24 June 2023).** Canonical
wording, from every puzzle in the series from Copycat Collaboration onward:

> Copycat Cells: Place 9 Copycat Cells into the grid so that there is exactly
> one Copycat Cell in each row, column, and 3x3 box. Each Copycat Cell must
> contain a different digit. The value of a Copycat Cell is the digit in the
> cell rotationally opposite itself in the grid (180° rotation about the
> center of the grid). For example, if r2c3 is a Copycat Cell containing the
> digit 5, and r8c7 contains the digit 9, the value of r2c3 is the digit in
> r8c7, which is 9.

Every other constraint in the puzzle reads values, not digits. Variations
Scojo has used:

- **Copies value, not digit** (Copycat Copycat, 2023): the opposite cell may
  be a Doubler, so a Copycat copies the doubled value. Extra clauses:
  Doubler and Copycat may not share a cell; a Copycat may not be opposite
  another Copycat.
- **Copies digit** (2024 onward): the canonical wording above. Copycat
  opposite Copycat is then allowed and self-consistent (each takes the other's
  digit).
- **Placement replaced by a pencil-puzzle answer**: "All shaded cells act as
  copycat cells" (Copycat Yin Yang, Copycat Choco Banana); "Any cell Poppy
  visits acts as a Copycat Cell" (Copycat Fun). Here the one-per-row/col/box
  and all-different clauses are dropped; the shading or path decides which
  cells copy.
- **Multi-grid**: 6 per 6x6 grid (Scoj-tocopy, Déjà Vu, There's Strength in
  Numbers); in the samurai and the four-grid puzzle the opposite cell is
  taken across a dotted centre between grids.

**2. Copycat lines — Phistomefel (28 March 2024).** Unrelated mechanic with
the same name:

> Copycat: The two lines have the same composition of digits. If, for
> example, one line has two 3s, five 4s and one 9, so does the other. The
> order of the digits is not necessarily the same.

Copycat Confusion (Aug 2024) adds: four lines pair up into two copycat pairs,
and which line is the thermo / average arrow / region-sum / whisper is to be
deduced.

Not the mechanic: GM Puzzles "Copycat Killer" (Philip Newman, 17 Jan 2026) is
a plain Killer whose theme name is "Copycat"; Bill Murphy's GAS "Copycats"
(26 Nov 2025) is a German Whispers sudoku.

## Catalogue — Copycat Cells (Scojo's modifier)

Ordered by date. "Pencil" = shading / loop-path / region answer required.

| # | Date | Title | Setter | LMD | Other constraints | Pencil hybrid? |
|---|------|-------|--------|-----|-------------------|----------------|
| 1 | 2023-06-24 | Copycat Copycat | Scojo | [000E9P](https://logic-masters.de/Raetselportal/Raetsel/zeigen.php?id=000E9P) | Doublers, Slow Thermos, Entropic Lines | no |
| 2 | 2024-05-17 | Copycat Yin Yang | Scojo | [000I3V](https://logic-masters.de/Raetselportal/Raetsel/zeigen.php?id=000I3V) | Yin Yang (shaded = copycat), Sight Lines circles, Killer | **yes — Yin Yang shading** (LMD tags: Yin and Yang, Killer) |
| 3 | 2024-06-28 | Copycat Collaboration | Scojo (with Flinty, juggler, palpot, Ratfinkz, gdc) | [000IP9](https://logic-masters.de/Raetselportal/Raetsel/zeigen.php?id=000IP9) | Zipper Lines, Odd Lots | no |
| 4 | 2024-07-20 | Copycat Blues | Scojo & Marty Sears | [000J0S](https://logic-masters.de/Raetselportal/Raetsel/zeigen.php?id=000J0S) | Region Sum Lines, Same Difference Lines | no |
| 5 | 2024-08-06 | Copycat Choco Banana | Scojo | [000J8B](https://logic-masters.de/Raetselportal/Raetsel/zeigen.php?id=000J8B) | Choco Banana (shaded = copycat), Arrows whose circle also counts its shaded/unshaded group | **yes — Choco Banana shading** |
| 6 | 2024-08-12 | Copycat Cipher | Scojo | [000JBO](https://logic-masters.de/Raetselportal/Raetsel/zeigen.php?id=000JBO) | Cipher, X-Sums, Killer | no |
| 7 | 2024-09-10 | Can't Copy This Cat | juggler (Michael Lefkowitz), Scojo-style impostor entry | [000JR6](https://logic-masters.de/Raetselportal/Raetsel/zeigen.php?id=000JR6) | Cipher, Killer, Little Killer | no |
| 8 | 2024-09-27 | Copycat Kropki | Scojo | [000JZB](https://logic-masters.de/Raetselportal/Raetsel/zeigen.php?id=000JZB) | Kropki | no |
| 9 | 2024-10-11 | The Answer to the Ultimate Question | ViKingPrime (Hitchhiker series) | [000K8F](https://logic-masters.de/Raetselportal/Raetsel/zeigen.php?id=000K8F) | Arrows, Kropki, Renban, German Whispers, Killer, Fog | no |
| 10 | 2024-10-28 | Copycat Mates | Scojo | [000KH4](https://logic-masters.de/Raetselportal/Raetsel/zeigen.php?id=000KH4) | Dutch Flat Mates, Dutch Whispers, XV | no |
| 11 | 2025-05-09 | Scoj-tocopy | ChinStrap | [000NA9](https://logic-masters.de/Raetselportal/Raetsel/zeigen.php?id=000NA9) | 6x6; Index Lines, Renban, X-Sums | no |
| 12 | 2025-07-31 | Déjà Vu (5-part 6x6 series; Part 5 is "Copycat Cells", Part 4 "Pseudo Cells") | Scojo | [000OH0](https://logic-masters.de/Raetselportal/Raetsel/zeigen.php?id=000OH0) | Modifiers, Region Sum, Renban, Nabner, Thermo, Kropki, XV, Quadruple | no (CTC video 2025-09-06, ctc-catalogue #7586) |
| 13 | 2025-09-14 | Copycat Banner | Scojo | [000P4T](https://logic-masters.de/Raetselportal/Raetsel/zeigen.php?id=000P4T) | Renban, Nabner | no |
| 14 | 2025-12-08 | Copycat Fun | Scojo | [000QGR](https://logic-masters.de/Raetselportal/Raetsel/zeigen.php?id=000QGR) | Rat-Run-style path (Poppy the cat, r1c1 to r5c5, walls, diagonal moves through 2x2 gaps); visited cells = copycat; Kropki | **yes — path drawing** |
| 15 | 2026-01-21 | RAT RUN 22: Copyrat | marty_sears | [000QZU](https://logic-masters.de/Raetselportal/Raetsel/zeigen.php?id=000QZU) | Two rat paths through a maze; 9 copycat cells (one per row/col/box); blackcurrant, redcurrant, grape; per-box equal path sums | **yes — two paths** |
| 16 | 2026-03-26 | BYO Samurai | Chad | [000S1Z](https://logic-masters.de/Raetselportal/Raetsel/zeigen.php?id=000S1Z) | Build-your-own samurai; grid C is Copycat, copies stay inside that grid | no (tags: Samurai, Modifier Cells) |
| 17 | 2026-03-29 | Copycat Sausage | Scojo | [000S30](https://logic-masters.de/Raetselportal/Raetsel/zeigen.php?id=000S30) | Sausages (linked sausage sums differ by chain length) | no — sausages are given regions, not drawn |
| 18 | 2026-04-13 | Copycat Burgh-lars | Scojo, ChinStrap, Calvinball, Sotehr, MathGuy_12 | [000SAR](https://logic-masters.de/Raetselportal/Raetsel/zeigen.php?id=000SAR) | Periodic Pill Sums, Tentropy Lines | no |
| 19 | 2026-05-09 | There's Strength in Numbers | SennyK | [000SQ6](https://logic-masters.de/Raetselportal/Raetsel/zeigen.php?id=000SQ6) | Four 6x6 grids (Doubler, Negator, Sesquifer, Increaser); copycats copy across grids; Renban, Arrows, Region Sum | no |

Scojo's own list on each series page names twelve "official" entries:
Copycat Copycat, Yin Yang, Collaboration, Blues, Choco Banana, Cipher,
Kropki, Mates, Banner, Fun, Sausage, Burgh-lars. Déjà Vu is outside the
series but uses the modifier in Part 5. Cat Fun (000KVA, 2024-11-24) is the
path-drawing predecessor of Copycat Fun and has no copycat rule.

Off-LMD: Rat Run 22 is also on crackingthecryptic.com (sudoku?id=3083,
credited GeorgeTheToad there).

## Catalogue — Copycat lines (Phistomefel)

| Date | Title | Setter | LMD | Other constraints | Pencil hybrid? |
|------|-------|--------|-----|-------------------|----------------|
| 2024-03-28 | Copycat | Phistomefel | [000HGS](https://logic-masters.de/Raetselportal/Raetsel/zeigen.php?id=000HGS) | Palindrome line and Zipper line share a digit multiset; Kropki | no |
| 2024-08-19 | Copycat Confusion | Phistomefel | [000JEO](https://logic-masters.de/Raetselportal/Raetsel/zeigen.php?id=000JEO) | Four lines, two copycat pairs, line types (average arrow / thermo / region sum / German whisper) to be deduced | no |

## Pencil-puzzle hybrids among Copycat puzzles

Four of nineteen. In every one the pencil answer *is* the copycat placement:

- **Copycat Yin Yang** — the Yin Yang shading decides which cells copy; a
  Sight Lines circle counts same-colour cells seen, using values.
- **Copycat Choco Banana** — Choco Banana shading decides which cells copy;
  arrow circles double as group-size counts.
- **Copycat Fun** — a single path (Rat Run mechanics) decides which cells copy.
- **RAT RUN 22: Copyrat** — two paths; the copycats are placed
  one-per-row/col/box independently of the paths, and the paths' per-box
  value sums must match.

No Copycat puzzle uses a region-division genre yet (Copycat Sausage's
sausages are given). Chocona / Choco Banana and Yin Yang have been used;
Nurikabe, Cave, LITS, Star Battle, loops (Masyu, Slitherlink) have not.

## CP-SAT note

The modifier is cheap: 81 copycat bools, exactly-one per row / column / box,
all-different on the copycat digits (9 optional-int channels or a
`digit==d & copy` pairwise exclusion), and `value[c] = digit[c]` if not
copycat else `digit[opp(c)]`, expressed with two implications per cell (no
element needed since the opposite cell is fixed). Downstream constraints read
`value`. The pencil-hybrid form replaces the 27 exactly-one constraints with
`copy[c] == shaded[c]` (or `== on_path[c]`), which is even cheaper; the cost
then sits entirely in the shading / path genre (see the survey §6).
