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
