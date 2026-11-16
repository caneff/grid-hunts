# 9x9 Skyscraper Sudoku clued only with 5s

Question (Chris, 2026-11-15): the unique 9x9 Skyscraper Sudoku (3x3 boxes) with
the most clues, where every clue is a 5: given 5s inside the grid and outside
skyscraper clues equal to 5.

## Result: 25 clues (16 outside + all 9 inside 5s), and 25 is the maximum

- **Upper bound by hand: 29.** A line clued 5 at both ends needs 4 visible
  buildings before its 9 and 4 after, so its 9 is the middle cell; only one
  row (and one column) can hold its 9 in the middle, so at most 10 row clues
  and 10 column clues.
- **Solver bound: 16.** Maximising the number of lines that show 5, over all
  9x9 sudokus, solved OPTIMAL at 16 on the first pass (`scripts/sky5.py`), so
  no grid shows more than 16 fives on its frame.
- **That optimum is unique.** The first 16-line grid, with every 5 given and
  all 16 outside 5s shown, has exactly one solution, so no cut was needed.

Grid (rows):

    671239458
    342518967
    985647231
    216753849
    834921576
    759864123
    123496785
    598372614
    467185392

Outside 5-clues: c1B r2L r3R c3T r4L c4T c4B c5T r6R c6B r7L c7B r8R c8T r9L c9B
(rN = row N from the Left/Right, cN = column N from the Top/Bottom).
Inside givens: every 5.

## Verification

`scripts/sky5_verify.py` re-checks on sudokumaker-custom-constraints'
`examples/skyscraper/build_size.py` `add_visibility` and `sky`, with
`sudoku_kit.cpsat.solve_unique`: every listed clue reads 5, the grid shows
exactly 16 fives, and the board is unique. The hunt model itself
(`scripts/sky5.py`) is a scratch model; the re-check is on the repo model.
Run from the custom-constraints checkout:
`uv run --project ~/src/grid-hunts python <path>/sky5_verify.py`.

SudokuMaker link (built with the skyscraper example's `RingGlobal` lane, so it carries the two-clue DP component; opens with nothing entered, 16 of 40 frame cells shown, 25 givens):

https://sudokumaker.app/p/jhdKnQBbk8

## More 25-clue boards, by clumping (2026-11-15)

Every hunt fixes 16 outside 5s, needs a unique solution, and bans rotations and reflections of each board it finds.
Scores are maxima proved by an OPTIMAL master solve:

- **Neighbouring clued frame cells** (side neighbours plus the 4 corner pairs, 36 pairs in all): max **8**, and exactly one unique board reaches it, up to symmetry. `scripts/sky5b.py` hit its 40-minute cap at score 7 after 225 passes, so more score-7 boards may exist.
- **Clues whose first cell is in one corner box**: max **3** of the 6 possible (`scripts/sky5c.py`).
- **Edge boxes that are the first box of 2 or more clues**: max **7** of 8 (`scripts/sky5d.py`).

`scripts/sky5_all.py` re-checks every board below on the custom-constraints `add_visibility` model (all unique) and builds each link through the skyscraper example's `RingGlobal` lane.

| id | group | score | link | outside 5s |
|---|---|---|---|---|
| orig | First find | neighbours 4, two-clue boxes 6 | https://sudokumaker.app/p/jhdKnQBbk8 | c1B r2L r3R c3T r4L c4T c4B c5T r6R c6B r7L c7B r8R c8T r9L c9B |
| adj1 | Most neighbouring clues | neighbours 8 (max, only one) | https://sudokumaker.app/p/gQ8gM6WKMJ | r2R c2T r3L c3B r4L c4B r5R c5T r6L r6R c6T r7L c7T c8B r9R c9B |
| adj2 | Most neighbouring clues | neighbours 7 | https://sudokumaker.app/p/jDp88QPFg7 | r1R r2R c2B r3L c3T r4L r5L c5T r6R c6T c6B r7L c7B r8R c8B c9T |
| adj3 | Most neighbouring clues | neighbours 7 | https://sudokumaker.app/p/b8j7fLdz88 | r2R c2B r3L c3T r4L c4T c4B r5R c5B r6R c6T r7R c7T r8L c8B r9L |
| adj4 | Most neighbouring clues | neighbours 7 | https://sudokumaker.app/p/k8fddkbWGd | c1B r2R c2T c3T r4L c4B r5L c5T r6R c6B r7R c7B r8L c8T r9L c9T |
| box1 | Most clues into one corner box | 3 into one box (max) | https://sudokumaker.app/p/D9LTBDDbMn | r1L c1T r2R c2B c3T r4L c4B r5R c5B r6R c6T r7L c7B r8R r9L c9T |
| box2 | Most clues into one corner box | 3 into one box (max) | https://sudokumaker.app/p/h8f6KrD9zr | r1L c1T r2L c2B c3B r4R c4B r5R c5T r6L c6B r7R c7T r8L c8B c9T |
| box3 | Most clues into one corner box | 3 into one box (max) | https://sudokumaker.app/p/hM8DjnHLzR | r1R c1B r2L c2T r3R c3T r4L c5T r6R c6T c6B r7L r8R c8B r9L c9T |
| box4 | Most clues into one corner box | 3 into one box (max) | https://sudokumaker.app/p/6tKzNLMc6n | r1L c1T r2R c2B r3L r4R c4B r5R c5T r6L c6B r7R c7T c8B r9L c9T |
| box5 | Most clues into one corner box | 3 into one box (max) | https://sudokumaker.app/p/R87FCcBgwn | c1B r2L c2T r3R c3T r4L c4B r5R c5T r6L c6T r7L c7B c8T r9R c9B |
| two1 | Most edge boxes with two clues | 7 of 8 boxes (max) | https://sudokumaker.app/p/KgmB6M8ghB | r2R c2T r3L c3B r4R c4T r5L r5R c5B r6L c6B r7R c7B r8L c8T c9T |
| two2 | Most edge boxes with two clues | 7 of 8 boxes (max) | https://sudokumaker.app/p/kjFgwbgbb7 | r1R r2R c2T r3L c3B r4L c4B r5L c5T r6R c6T c6B r7R c7B r8L c9T |
| two3 | Most edge boxes with two clues | 7 of 8 boxes (max) | https://sudokumaker.app/p/tfMLHWkFCj | r1R c2T r3L c3B r4L r4R c4T r5L c5B r6R c6B c7T r8R c8B r9L c9T |
| two4 | Most edge boxes with two clues | 7 of 8 boxes (max) | https://sudokumaker.app/p/B8K79WWz9W | r1R c1B c2B r3L c3T r4R c4T r5L r5R c5T r6L c6B r7R c7T r8L c8B |
| two5 | Most edge boxes with two clues | 7 of 8 boxes (max) | https://sudokumaker.app/p/bCWcjbTnhf | r1R r2L c2T r3L c3B r4R c4T r5L c5B r6L c6T c6B r7L c7T r9R c9B |

Grids (rows, in order):

- orig: `671239458 342518967 985647231 216753849 834921576 759864123 123496785 598372614 467185392`
- adj1: `528914376 739826514 461537289 342651798 987243165 156798432 213469857 675182943 894375621`
- adj2: `691834752 782965413 453217896 365178924 124359687 879426531 246583179 918742365 537691248`
- adj3: `682193475 791584632 453672198 314726589 876945321 529831764 968417253 245369817 137258946`
- adj4: `642937815 951846732 873152946 234519687 516278394 789364521 498725163 125693478 367481259`
- box1: `341672985 692851743 785394126 136245897 574986231 829713654 213569478 968437512 457128369`
- box2: `156739284 237648195 498512376 785963421 619824753 324157968 973486512 562371849 841295637`
- box3: `942813765 563724891 871956432 235147986 486539217 719268543 124695378 698372154 357481629`
- box4: `367518294 498732165 125469387 683927541 759841632 214356978 972685413 841293756 536174829`
- box5: `951834726 263715849 874926531 126347958 789652413 345189672 412568397 637491285 598273164`
- two1: `617385924 938427615 245619837 879236541 124598763 356174298 793861452 462753189 581942376`
- two2: `649852731 718963542 352714896 467138925 123549687 985627413 891276354 236485179 574391268`
- two3: `649387152 817452396 235169487 123598764 456273918 978641523 384916275 792835641 561724839`
- two4: `983247165 671359284 254168397 892471653 367895421 145632978 738916542 516724839 429583716`
- two5: `928471365 367582419 145693287 879364521 234159678 516728934 453217896 782946153 691835742`

## The same with 6s (2026-11-15)

Every 6 in the grid given, every outside clue a 6. A line cannot read 6 from both ends (5 visible buildings each side of the 9 needs 11 cells), so the hand bound is 18 outside.
The solver bound is **11 outside 6s** (20 clues), and a unique board reaches it (`scripts/sky6.py`, which cuts up to 20 rival grids per pass).

Clumping at 11 outside, maxima from an OPTIMAL master solve:

- **Neighbouring clued frame cells**: max 5, but every score-5 frame (16 of them) has a second solution; the best unique boards score 4 (`scripts/sky6b.py`).
- **Clues into one corner box**: max 2 (`scripts/sky6c.py`).
- **Edge boxes with 2 or more clues**: max 4 of 8 (`scripts/sky6d.py`, 20-minute cap, 3 boards found).
- six-adj2 and six-box1 are the same board, found by both hunts.

All re-checked unique on the custom-constraints `add_visibility` model (`scripts/sky6_all.py`).

| id | group | score | link | outside 6s |
|---|---|---|---|---|
| six1 | Most outside 6s | 11 outside (max) | https://sudokumaker.app/p/gbR79KC9LK | r1L r2R r3R c3T r4R c4B r6L c6T r7L r9R c9B |
| six-adj1 | Most neighbouring clues | neighbours 4 (max 5, none unique) | https://sudokumaker.app/p/JgB7Bj9nwP | r1L r2R r3R c3T r4R c4B c5T r6L r7L r9R c9B |
| six-adj2 | Most neighbouring clues | neighbours 4 (max 5, none unique) — same board as six-box1 | https://sudokumaker.app/p/hTLMHwKTD6 | r1R c1B c2T c3T r4L c4T r6R c6B r7L c7B c9T |
| six-adj3 | Most neighbouring clues | neighbours 3 | https://sudokumaker.app/p/LMGRcDCzN9 | c1T c2B r3L c3B r4R c4B r6L c6T c8T r9R c9B |
| six-adj4 | Most neighbouring clues | neighbours 3 | https://sudokumaker.app/p/bCGkf6fdKf | r1R r3L c3B r4L c4T r5R c5B r7R r8R r9L c9T |
| six-adj5 | Most neighbouring clues | neighbours 3 | https://sudokumaker.app/p/Kn7NpwjDtj | r1L c1T c2B c3B r4R c4B c5T r6L c7T r8R c8B |
| six-box1 | Most clues into one corner box | 2 into one box (max) — same board as six-adj2 | https://sudokumaker.app/p/hTLMHwKTD6 | r1R c1B c2T c3T r4L c4T r6R c6B r7L c7B c9T |
| six-box2 | Most clues into one corner box | 2 into one box (max) | https://sudokumaker.app/p/HCD7CRnw6G | r1R c1T c2B c3T c4T r5L c5B r7R c7B r8L c9T |
| six-box3 | Most clues into one corner box | 2 into one box (max) | https://sudokumaker.app/p/PJRdnnmQMT | r1L c1B r2R r3L c4B r5R c5T r6L r7R c7T r9L |
| six-box4 | Most clues into one corner box | 2 into one box (max) | https://sudokumaker.app/p/KwJpHNhGJM | r1R c1B r2L r3L r4L c5T r6R c6B r7R c7T r9L |
| six-box5 | Most clues into one corner box | 2 into one box (max) | https://sudokumaker.app/p/Ct8DzKFGmd | r1R c1B c2T c3T r4L c4T r6R c6B r7L c8B r9R |
| six-two1 | Most edge boxes with two clues | 4 of 8 boxes (max) | https://sudokumaker.app/p/89dDpTqKBT | r1L c1T r3R r5R c5B r6L r7L c7T r8R r9L c9B |
| six-two2 | Most edge boxes with two clues | 4 of 8 boxes (max) | https://sudokumaker.app/p/bznLHnTjgQ | r1R c1T c2B c3T c4T r5L c6B r7R c7B r8L c9T |
| six-two3 | Most edge boxes with two clues | 4 of 8 boxes (max) | https://sudokumaker.app/p/CbmHLndDqT | r1R c2B r3L c3T r5L c5B r6R r7R r8L r9R c9T |

Grids (rows, in order):

- six1: `452631789 913872654 786954321 891726543 567493218 234518967 125347896 348269175 679185432`
- six-adj1: `452613789 913827654 786954321 897261543 365749218 124538967 231475896 648392175 579186432`
- six-adj2: `941387652 852416973 763529814 124638795 375291468 689745321 236174589 518963247 497852136`
- six-adj3: `418962537 597813246 236754819 689475321 375291468 124638975 763529184 852146793 941387652`
- six-adj4: `579186432 648392175 231475896 124538967 897261543 365749218 786954321 913827654 452613789`
- six-adj5: `235648197 496751283 187923456 579864312 628139574 314572869 763415928 952387641 841296735`
- six-box1: `941387652 852416973 763529814 124638795 375291468 689745321 236174589 518963247 497852136`
- six-box2: `491387652 582461973 673529814 764198325 235674198 819253746 927846531 156732489 348915267`
- six-box3: `456728139 987631254 123459678 865943712 792816543 341572896 679385421 518294367 234167985`
- six-box4: `987316254 456728319 123459687 345162798 812947563 769835421 698574132 571293846 234681975`
- six-box5: `941287653 852346197 763519284 124638975 375192468 689475321 236754819 518923746 497861532`
- six-two1: `234586179 571294368 698317542 719843625 862975431 345162897 123459786 987631254 456728913`
- six-two2: `491387652 582146973 673529814 764298135 235614798 819735426 927863541 156472389 348951267`
- six-two3: `791685432 683492175 245713896 526348917 134579268 978261543 867954321 452136789 319827654`

## Middle-edge boxes, and duplicates (2026-11-15)

Score: how many of the 4 middle-edge boxes (not corners) are the first box of 2 or more clues (`scripts/sky5e.py`, `scripts/sky6e.py`). Maxima from an OPTIMAL master solve: **3 of 4** for 5s (16 outside), **1 of 4** for 6s (11 outside).

| id | score | link | outside |
|---|---|---|---|
| mid1 | 3 of 4 middle-edge boxes (max) | https://sudokumaker.app/p/RD7n6h7KKb | c1B c2B r3L c3T r4R c4T r5L c5T r6L r6R c6B r7R c7T r8L r9R c9T |
| mid5 | 3 of 4 middle-edge boxes (max) | https://sudokumaker.app/p/CgzG7mjkrW | r1R c1T r3L c3B r4L r4R c4T r5R c5B r6L c6B r7R c7B r8L c8T c9T |
| six-mid1 | 1 of 4 middle-edge boxes (max) | https://sudokumaker.app/p/QBFGWnftgf | r2L r3R c3T c4B r5R c5T r6L c6B r7L r8R c8B |
| six-mid2 | 1 of 4 middle-edge boxes (max) | https://sudokumaker.app/p/WNwJHW7mzP | r2L r3R c3T r4L r5R c5T r6R c6B r7L c7B r8R |
| six-mid3 | 1 of 4 middle-edge boxes (max) | https://sudokumaker.app/p/ptbftNqg7T | r1L c2T r3R r4L c4T r5R c5B c6T r7L r8R c8B |

Grids:

- mid1: `674529183 985137246 231648597 892713654 143256978 567894321 758961432 426375819 319482765`
- mid5: `589374621 617285943 234169857 123498765 798652314 456731298 861947532 345826179 972513486`
- six-mid1: `671349285 234658197 985721643 816932574 597864312 342517869 123476958 769285431 458193726`
- six-mid2: `741239865 235648917 986751243 412563789 567984321 398127654 123476598 679815432 854392176`
- six-mid3: `235174896 816295374 947386521 352467189 679851432 481923765 123648957 598712643 764539218`

Hunts with different scores land on the same board. Up to rotation and reflection (grid and clue layout together), these are one board each:

- 5s: adj1 = two2; adj3 = mid2; two1 = mid3; two3 = mid4 (mid2-mid4 are rotations, no separate links).
- 6s: six1 = six-adj2 = six-box1; six-adj1 = six-box4; six-box2 = six-two3.

No two boards share a clue layout up to symmetry with different grids. That leaves 29 distinct boards: 17 for 5s, 12 for 6s.

## Outside 5s with box-numbered givens (2026-11-15)

Testers found the all-5s and all-6s boards too hard. Chris's next theme: outside clues all 5, and inside each box k shows only its own digit k, one given per box. With all 9 box givens and the 16 outside 5s the hunt (`scripts/sky5k.py`) finds unique boards at once: 5 in about 2 minutes, each its first or second pass. A rotation moves the box numbers, so rotations count as different puzzles here; found boards are banned by clue layout only.

All 5 re-checked unique on the custom-constraints `add_visibility` model (`scripts/skyk_all.py`). Not rated for difficulty: no whole-board difficulty rater exists in these repos yet.

| id | link | outside 5s |
|---|---|---|
| box-k1 | https://sudokumaker.app/p/pQPfHgntBH | r1R r2R r3L c3B r4L c4B r5L c5T c5B r6R c6T r7L c7B r8R c8B c9T |
| box-k2 | https://sudokumaker.app/p/7hBMPwf7dH | r1L c1T c2B r3R c3T r4L r5L c5T r6R c6B r7L r7R c7T r8L r9R c9B |
| box-k3 | https://sudokumaker.app/p/TDGdHgCCcC | r1L c1T r2R r3L c3B r4R c4T c4B c5T r6L c6B r7R c7T r8L c8T c9B |
| box-k4 | https://sudokumaker.app/p/ntJD6CbcqL | r1R r2L c2T c3B r4R c4T r5L r5R r6L c6B r7R c7T r8R c8B r9L c9T |
| box-k5 | https://sudokumaker.app/p/zt9KdNg7hP | r1L c1B r2R c2T r3L c3B r4R c4T r5L r6L r6R c6B r7R c7T c8B r9L |

Grids:

- box-k1: `569843721 718962543 342175896 156284937 234791685 897356412 425638179 981527364 673419258`
- box-k2: `452738169 693541278 781962543 235489617 146327985 879156432 567894321 314275896 928613754`
- box-k3: `467158329 598237461 231469578 759813642 846925137 123746985 985674213 314582796 672391854`
- box-k4: `829376154 357418296 614259387 978531642 246897531 135624978 781965423 492183765 563742819`
- box-k5: `145269378 928374165 367158294 879615423 516432789 234897651 781946532 693521847 452783916`

## Outside clues equal to their box number (2026-11-15)

Each outside clue must equal the number of the box it looks into first (rows 1-3 from the left read 1, columns 4-6 from the top read 2, ... columns 7-9 from the bottom read 9); inside, each box k shows its own digit k. `scripts/skybx.py` maximises the outside clues: **17** is the most (OPTIMAL on the first pass), so 26 clues in all, and unique boards come at once (5 found, 56 passes). No board uses a clue of 8 or 9. bx2 and bx3 share their outside clues but differ inside.

Hand reasoning: a box-1 clue of 1 puts a 9 on the edge, and two 9s in box 1 clash unless one 9 at r1c1 serves both a row and a column, so box 1 takes at most 2 clues; a box-9 clue of 9 means the line climbs 1-9, at most one row and one column.

All 5 re-checked unique on the custom-constraints `add_visibility` model (`scripts/skybx_all.py`).

| id | link | outside |
|---|---|---|
| bx1 | https://sudokumaker.app/p/7tgpTcwbFr | r1L r1R c1T c1B r2R r3R r4R c4T r5L r5R c5T r6L c6T c7T c8T r9L c9T |
| bx2 | https://sudokumaker.app/p/jfBmTdQjPG | r1L r1R c1T c1B r2R r3R r4L r4R c4T r5R c5T r6L c6T c7T r8L c8T c9T |
| bx3 | https://sudokumaker.app/p/K9qpLcwgzh | r1L r1R c1T c1B r2R r3R r4L r4R c4T r5R c5T r6L c6T c7T r8L c8T c9T |
| bx4 | https://sudokumaker.app/p/G9tkCNcNG6 | r1L r1R c1T c1B r2R r3R r4L r4R c4T r5R c5T r6L c6T r7L c7T c8T c9T |
| bx5 | https://sudokumaker.app/p/WPJDj6P9Lb | r1L r1R c1T c1B r2R r3R r4R c4T r5L r5R c5T r6L c6T c7T r8L c8T c9T |

Grids:

- bx1: `953748126 647291583 812536974 789165432 234987651 561324798 496852317 378419265 125673849`
- bx2: `952783146 746219835 813546972 678954321 391872654 524631798 469328517 235167489 187495263`
- bx3: `916783245 824569713 753421986 678954321 392817654 541236879 467192538 135678492 289345167`
- bx4: `963781245 852349716 714526983 678954321 329817654 541263879 135678492 497132568 286495137`
- bx5: `954728136 726193485 813465972 391287654 678954321 542316798 469832517 235671849 187549263`

## The same with 7s (2026-11-15)

Every 7 in the grid given, every outside clue a 7. Hand bound **12**: a 7 read from the left puts that row's 9 in columns 7-9, which hold only three 9s, so at most 3 rows per side, and no line takes a 7 at both ends. Solver bound **7** (OPTIMAL on the first pass of `scripts/sky7.py`, the rival-batching hunt). The one unique 7-clue board the hunt reached, after 37 passes, has 16 clues; re-checked unique on the custom-constraints `add_visibility` model (`scripts/sky7_all.py`).

- seven1: https://sudokumaker.app/p/Q8pfzLWfQp
- outside 7s: r1L c3B r4L c4T r5R r7R r8L
- grid: `234167895 719385462 568249137 123458976 987621543 456793218 695874321 342516789 871932654`

| digit | most outside clues | clues in all |
|---|---|---|
| 5 | 16 | 25 |
| 6 | 11 | 20 |
| 7 | 7 | 16 |

## With no givens inside the grid (2026-11-15)

Question (Chris): the same boards with nothing given inside, outside clues only. Blank outside cells carry no information, so each board shows every line of its grid that reads the clue value; the most-clues bounds (16 / 11 / 7, jigsaw 10) do not depend on givens.

A whole-grid 1-2 swap is always another sudoku and changes only a line that starts `12` or `21`, so a unique no-givens board needs a clued line starting with that pair.

Every board on the page was re-solved with its inside givens removed (`scripts/nogiv.py` on the custom-constraints `add_visibility` model, solutions counted to 20), and each unique result re-checked on an independent visibility encoding (`scripts/nogiv_x.py`, counted to 3). The two agree on every board checked. Board data: `scripts/page_boards.json`.

Unique with outside clues only:

- **5s, 16 clues** (11 of 16): adj2, adj3, box1, box3, box5, two1, two3, two4, two5, mid1, mid5. orig, box2, box4 have 2 solutions; adj1, adj4 have 3.
- **6s, 11 clues** (10 of 13): six1, six-adj1, six-adj3, six-adj4, six-box2, six-box3, six-box5, six-two1, six-two2, six-mid2. six-mid1 has 2, six-mid3 5, six-adj5 6.
- **7s on a jigsaw, 10 clues**: jig1 is unique. On 3x3 boxes seven1 (7 clues) has 2.
- **Box-numbered themes**: none. box-k1..k5 have 2 to 20+; bx1..bx5 all 20+.

So the givens were never needed for most of the 5s and 6s boards: an 11-clue all-6s board is unique on its frame alone. The links on the page still carry the givens; no-givens links are not built yet.

## Jigsaw boards, all 7s (2026-11-15)

Every 7 given, every outside clue a 7, but the 9 regions are drawn too: 9 connected 9-cell regions each holding 1-9, in place of the 3x3 boxes.
A plain 9x9 Latin square shows at most **10** outside 7s (OPTIMAL), so 10 is the ceiling on any layout; on 3x3 boxes it is 7.

- **jig1** (19 clues): https://sudokumaker.app/p/qTKjJdp7nd. Unique, and still unique with no givens inside (https://sudokumaker.app/p/LmJL8D77MG). Chris rejected its look: rows 1 and 9 are whole regions, and the layout is too symmetric.
- **jig2** (19 clues): https://sudokumaker.app/p/PjfnRCJzbq. Exactly one straight region (column 9). Regions `AAAABBBBC DAAEBBFBC DGAEEBFHC DGAAEBFHC DGGGEFFHC DDGEEFHHC DGGEIFFHC DIGEIIFHC DIIIIIHHC`, grid `345791268 426983175 659874321 798165432 987612543 134527689 213456897 572348916 861239754`, outside `r3R c3B r4R c4B r5R c5B r6L c6T r7L c7T`. Unique on an independent encoding.

What did not work, so the next hunt does not repeat it:

- **One model for grid, regions and clues** (`sky7J.py`, the other session's): finds boards, but the regions come out as straight rows and columns.
- **The same with region rules** (each region spans at least 3 rows and 3 columns, no 3x3 box, no rotation or reflection symmetry): its first 15-minute pass reached only 7 outside 7s.
- **Grid first, then regions with those rules** (`sky7J2s.py`): none of 60 grids (30 at 10 outside, 30 at 9) has such a tiling. On jig1's grid, a tiling needs at least 2 straight regions; with span 2 or more in both directions it is infeasible. The rules themselves are not the bug: the same model tiles a regular sudoku solution under all three rules at once. Why these grids resist is not established; a line reading 7 is nearly increasing, which pushes the grid toward shifted rows.
- **Regions first, drawn without digits**: 61 layouts in a row could not be filled as a sudoku at all.

What worked (Chris's rule: valid Latin squares, any tiling with at most one straight region):

- `sky7Jlat.py` tiles the first 5 grids it tries in 61 seconds, but the other regions come out as near-straight stripes.
- `sky7Jloop.py` keeps a grid and its 10 clues and lets the tiling change, cutting each rival by putting two of its equal digits in one region. One grid had no unique tiling (proved in 12 s); the next gave jig2 on pass 2. `sky7Jhunt` (the same over many grids) found 3 more unique boards in 38 seconds; they were not kept, because Chris switched the hunt to no givens.
- `sky7Jng.py` is that hunt with no inside givens: the 10 outside 7s alone must make the board unique.

The scripts read `sky5lib.py` and `sky7J2s.py` from this directory and run from the grid-hunts checkout (`uv run python <path>`).

## Jigsaw boards with no givens (2026-11-15)

Chris's rules: nothing given inside (the 10 outside 7s and the regions alone fix the grid), at most one straight region (all nine cells in one row or column), and no other region with 8 or more cells in one row or column; the last pass tightened that to 7 or more.
Each board below has exactly 1 solution on an independent encoding with no givens.

| id | link | straight region | most cells of another region in a line |
|---|---|---|---|
| jng1 | https://sudokumaker.app/p/WJJtMPGKPB | none (row 1 short by one cell) | 8 |
| jng2 | https://sudokumaker.app/p/mLKGbmpMrL | column 1 | 8 |
| jng3 | https://sudokumaker.app/p/Tg6g9GpPjm | row 1 | 6 |
| jng4 | https://sudokumaker.app/p/khfTTTBtGB | column 1 | 6 |
| jng5 | https://sudokumaker.app/p/DwLmmGDgFc | column 9 | 6 |
| jng6 | https://sudokumaker.app/p/ntQNJcR7HQ | column 9 | 6 |

Regions (rows), grid (rows), outside 7s:

- jng1: `AAAAAAAAB CCCABBBBB CCDDBEEBB FCCDEEEGG FCCDEGGGG FFFDEHHGG FFDDEEHHG FDDIIIIHH FIIIIIHHH`; `345621789 476912358 529843167 698754231 213467895 134578926 752389614 861295473 987136542`; r1L c1T r4R c4B r5L c5T r6L c6T r9R c9B
- jng2: `ABBBBBBBC ADDEBEEFC ADGEBEFFC ADGEEEFFC ADGGHEFCC ADDGHHFFC ADGGIHHFC ADGGIIHHC AIIIIIIHH`; `745391268 426983175 659874321 398765412 987612543 134527689 213456897 572148936 861239754`; r3R c3B r4R c4B r5R c5B r6L c6T r7L c7T
- jng3: `AAAAAAAAA BBBCCCCCC BBDDCEECC FBBDEEEGG FBBDEEEEG FFFDGGGGG FFDDHHHHG FDDIIHIHH FIIIIIIHH`; same grid and outside 7s as jng1
- jng4: `ABCCCCCCD ABBCBCDDD ABBBBCDDE AFFBDDDEE AFFFFGEEE AFHHHGGGE AFHIHHGGE AFHIIHHGE AIIIIIIGG`; `345621789 452913678 569834217 698745321 214567893 123478956 736289145 871392564 987156432`; r1L c1T r4R c4B r5L c5T r6L c6T r9R c9B
- jng5: `AAAAAABBC DAEEEAEBC DAFFEEEBC DDDFEEBBC DDFFFFBGC DFFHHHBGC DHHHIIBGC HHIIIIIGC HIIGGGGGC`; `487592163 716983254 569874321 698715432 345621789 234167895 123458976 852349617 971236548`; r3R c3B r4R c4B r5L c5B r6L c6T r7L c7T
- jng6: `AAABCCCCD AAABCBBCD EAABBBCCD EEAFBBCGD HEEFGGGGD HHEFGIGGD HHEFIIIGD HHEFIFIID HHEFFFIID`; `754293168 216984375 639875421 498716532 987651243 345162789 123547896 562438917 871329654`; r3R c3B r4R c4B r5R c5B r6L c6T r7L c7T

The hunts (`sky7Jng.py`, `sky7Jng2.py`, `sky7Jng3.py`, each reading `sky7J2s.py`) take a Latin square showing 10 outside 7s with a clued line starting 12 or 21, then search tilings of it, cutting each rival solution by putting two of its equal digits in one region:

| run | rule on other regions | grids tried | grids with a unique tiling | time |
|---|---|---|---|---|
| sky7Jng | none | 10 | 5 | 88 s |
| sky7Jng2 | at most 7 cells in a line | 14 | 5 | 191 s |
| sky7Jng3 | at most 6 cells in a line | 41 | 5 (one repeats jng4) | 357 s |

Without the line limit the solver hides straightness in near-straight regions (8 of 9 cells in one row or column); each tightening rejects more grids but still finds boards in minutes.

### More, from a second hour of the same hunt (2026-11-16)

`sky7Jng4.py` is `sky7Jng3.py` started from other seeds: 301 grids in an hour, 6 with a unique tiling, all checked on the independent encoding. Chris kept three; one of the others was a near-twin of jng9.

| id | link | straight region | most cells of another region in a line |
|---|---|---|---|
| jng7 | https://sudokumaker.app/p/jjDCBHJ6cq | none | 6 |
| jng8 | https://sudokumaker.app/p/g6bWBmDGGb | column 9 | 6 |
| jng9 | https://sudokumaker.app/p/FPgfRrCwpQ | column 1 | 6 |

- jng7: `AAABBBBBB AAAAABBBC DEEAEEEEC DDEEECCCC DDDFFFFCC DFFFGHFFC DIIIGHHHH DIGGGGHHH IIIIIGGGH`; `751289643 862395174 123478965 234517896 987164532 498756321 619843257 576932418 345621789`; r3L c3T r4L c4T r5R c5B r6R c6B r9L c9T
- jng8: `AAABBBBBC AAADBBDBC AEADDBDDC FEAGDDDGC FEEGGGGGC FEEHHHHGC FFEHHIHGC FFEIHIHIC FFEIIIIIC`; `546193278 712984365 369875421 498761532 987652143 125346789 234517896 653428917 871239654`; r3R c3B r4R c4B r5R c5B r6L c6T r7L c7T
- jng9: `ABBBBBBCC ADBEBEBCC ADDEEEEFC AGDEEEFFC AGDDDFFCC AGDGDHFFC AGGGHHHFF AGHHHIHII AGHIIIIII`; `145793268 436982175 659874321 798165432 987621543 324516789 213457896 562348917 871239654`; r3R c3B r4R c4B r5R c5B r6L c6T r7L c7T

## Jigsaw boards with complex regions, inner 7s given (2026-11-16)

Question (Chris): more jigsaw all-7s boards with complex regions, every inner 7 given.
Rules applied: no straight region, no region with more than 6 cells in one row or column, every region spanning at least 2 rows and 2 columns. Complexity is counted as region edges: cell sides that are region borders (3x3 boxes have 36; the earlier jigsaw boards have 62 to 69, mostly from long stripes).

What the 10-outside grids allow (`sky7Jcxp.py`, `sky7Jcxk.py`; tiling only, no uniqueness check):

- 8 fresh Latin squares from stage 1: none can be tiled under these rules (each INFEASIBLE in 6-15 s).
- The 10 grids on the page: jig2, jng1, jng7 and jng8 can; jig1, jng2, jng4, jng5, jng6 and jng9 cannot. None of the 10 can be tiled with at most 5 cells of a region in a line (each INFEASIBLE in 6-20 s).
- One model for grid and regions together (`sky7Jcxj.py`) returned UNKNOWN in 300 s at every level, including the one jng7 shows is feasible, so it settles nothing.

`sky7Jcx.py` then hunts on the four tileable grids with the inner 7s given: it cuts each rival by putting two of its equal digits in one region, and after each unique board demands more region edges. On jig2's grid no tiling is unique (proved in 26 s). Each other grid's chain ends INFEASIBLE, so its last board has the most region edges any unique board on that grid reaches under these rules.
Every board below has exactly 1 solution on an independent encoding (`sky7Jcx_verify.py`); "no givens" is the count with the inner 7s removed.

| id | link | region edges | narrowest region span | no givens |
|---|---|---|---|---|
| jcx1 | https://sudokumaker.app/p/Qtg9jHmjWm | 64 | 3 | unique |
| jcx2 | https://sudokumaker.app/p/LPPBGDNB66 | 66 | 2 | unique |
| jcx3 | https://sudokumaker.app/p/T9GJk8ncHf | 67 | 3 | unique |
| jcx4 | https://sudokumaker.app/p/btTbLdctRq | 68 | 3 | unique |
| jcx5 | https://sudokumaker.app/p/QPPqgKLwht | 64 | 2 | unique |
| jcx6 | https://sudokumaker.app/p/PWqM7WCTbG | 66 | 2 | 2 solutions |

jcx1-jcx4 are on jng1's grid (outside r1L c1T r4R c4B r5L c5T r6L c6T r9R c9B), jcx5 on jng7's, jcx6 on jng8's. Regions (rows):

- jcx1: `AAAAABBBB CCCAABDBE CCCADBDBE FFCADBDEE FCCGDDDDE FFFGHIEEE FFGGHIIIE FGGHHIIII GGGHHHHHI`
- jcx2: `AAAAABBBB CACAABDBE CCCABBDBE FFCCDDDEE FCCGDHIEE FFFGDHIEE FFGGDHIIE FGGHDHHII GGGHHHIII`
- jcx3: `AAAAABBBB CACAABDBE CCCADBDBE FFCCDBDEE FCCGDDDDE FFFGHIEEE FFGGHIIIE FGGHHIHII GGGHHHHII`
- jcx4: `AAAAABBBB CACAABDBE CCCADBDBE FFCCDBDEE FCCGDDDDE FFFGGHEEE FFGGIHHHE FGGIIHIHH GGIIIIIHH`
- jcx5: `AAABBBBBB AAAAABBBC DEEAEEEEC DDEEECCCC DDDFFFFCC DGGFHIFFC DGFFHIIII DGHHHHIII GGGGGHHHI`
- jcx6: `AABBCCCCC AAABBCBCC AADDBBBBC EAADDDDDF EEEEEDGDF EGGGGGGFF EEHHHHGGF IIHIHHHFF IIIIIIHFF`

Open: a grid that takes regions with at most 5 cells in a line was not found; more stage-1 grids, or 9 outside 7s, would be the next places to look.
