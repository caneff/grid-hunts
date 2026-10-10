# U-Bahn: emitting a found puzzle as a Penpa+ link

**Date:** 2026-10-10
**Question.** Chris ruled that the U-Bahn finder
(`docs/research/2026-10-10-u-bahn-cpsat-finder.md`) emits each found puzzle as
a Penpa+ link carrying the full clue set: four numbers per row and per column,
one per piece type. How exactly can a Python finder produce such a link, and
how can the link check the solver's drawn network?

**Method.** I read the penpa-edit source at one commit `[P1]`, resolved the
Penpa+ short links on five published Rätselportal puzzles and decoded them
offline with a throwaway Python script kept outside the repo, and read the
source of the Python tools I cite. **No browser was run**: nothing below was
confirmed by loading a link in Penpa+. Each claim is tagged `[read]` (I read
it in the cited file or decoded it from the cited link), `[ran]` (a result of
my offline script on a published link) or `[inferred]` (my reasoning). Every
recommendation is mine and is a flag-if-you-disagree proposal, not a settled
decision. Penpa line numbers are for commit `34e3fe9` and will drift. No full
link or decoded blob is reproduced here; only short field excerpts.

## 1. The wire format

### 1.1 URL shape and parameters

- A link is the Penpa+ page URL plus a parameter string. Penpa+ now writes it
  after `#` (`maketext_solve` returns `url + "#m=solve&p=" + ba`,
  `class_p.js:2226-2277`), and on load reads `location.search` first and falls
  back to `location.hash` (`general.js:29-31`). So both `?m=solve&p=…` and
  `#m=solve&p=…` load `[read]`. All five published links use `?` `[ran]`.
- Parameters are split on `&` and then on `=`, keeping only the piece after
  the first `=` (`general.js:1970-1977`). That drops base64 `=` padding
  `[read]`; the browser's `atob` accepts unpadded input `[inferred]`, and all
  five published payloads arrive unpadded `[ran]`. Nothing URL-decodes the
  value, so `+` and `/` travel literally.

| Param | Meaning | Source |
| --- | --- | --- |
| `m` | `edit` (setter view, both layers) or `solve` (solver view) | `general.js:2236`, `:2368` |
| `p` | the puzzle payload (§1.2, §1.3) | `general.js:1986` |
| `a` | the answer payload for auto-checking (§3) | `general.js:2406-2415` |
| `l` | `solvedup` — an edit-format clone opened in solve mode | `general.js:2282` |
| `q`, `r` | solver info and replay, written by `maketext_replay` | `class_p.js:2331-2353` |

  If `p` starts with `http`, it is treated as a URL to import instead
  (`general.js:1979-1983`) `[read]`.

### 1.2 Compression and encoding chain

Encoding, in order `[read]`:

1. Build the payload text: lines joined with a line feed (§1.3).
2. Apply the abbreviation table `COMPRESS_SUB` (`class_p.js:61-93`) to the
   **whole text**, in table order, each as a global replace
   (`class_p.js:2269-2271`). The first entry escapes every `z` as `zZ`; the
   rest replace quoted keys with two-character tokens; the last replaces the
   bare word `null` with `zO`.
3. UTF-8 encode (`TextEncoder`), **raw deflate** (`Zlib.RawDeflate` from
   imaya's zlib.js, `docs/js/libs/zlib.js`; no zlib header, no checksum), then
   standard base64 with `+` and `/` (`window.btoa`) — `encrypt_data`,
   `general.js:3230-3236`.

Decoding is the reverse: `atob`, `Zlib.RawInflate`, UTF-8 decode
(`decrypt_data`, `general.js:3238-3245`), then the table applied **in reverse
order** (`general.js:1988-1991`), then a split on line feed `[read]`.

The table, in order (plain → token): `z`→`zZ`, `"qa"`→`z9`, `"pu_q"`→`zQ`,
`"pu_a"`→`zA`, `"grid"`→`zG`, `"edit_mode"`→`zM`, `"surface"`→`zS`,
`"line"`→`zL`, `"lineE"`→`zE`, `"wall"`→`zW`, `"cage"`→`zC`, `"number"`→`zN`,
`"symbol"`→`zY`, `"special"`→`zP`, `"board"`→`zB`, `"command_redo"`→`zR`,
`"command_undo"`→`zU`, `"command_replay"`→`z8`, `"numberS"`→`z1`,
`"freeline"`→`zF`, `"freelineE"`→`z2`, `"thermo"`→`zT`, `"arrows"`→`z3`,
`"direction"`→`zD`, `"squareframe"`→`z0`, `"polygon"`→`z5`,
`"deletelineE"`→`z4`, `"killercages"`→`z6`, `"nobulbthermo"`→`z7`,
`"__a"`→`z_`, `null`→`zO` `[read]`. The plain side includes the double quotes;
the token has none.

The `a` payload goes through step 3 only — no table
(`maketext_solve_solution`, `class_p.js:2322-2329`) `[read]`.

A first character of line 0 that is a digit routes to a legacy loader
(`loadver1`, `general.js:1993-1996`, `:2681`). A current link's line 0 starts
with the grid type word, so this never triggers `[read]`.

### 1.3 Payload structure (solve mode)

Lines as `maketext_solve` writes them (`class_p.js:2226-2277`) and `load`
reads them (`general.js:1969-2560`) `[read]`. The "published" column is what
the decoded links hold `[ran]`.

| Line | Content | Loader | Published example |
| --- | --- | --- | --- |
| 0 | comma-separated header (below) | required | — |
| 1 | `space`: JSON `[over, under, left, right]` | required (`JSON.parse`) | `[0,0,0,0]` |
| 2 | grid mode, then `~` answer tool, then `~` its settings | first part required | `["1","2","1"]~"line"~["1",3]` |
| 3 | `pu_q`, the question layer, JSON | required | — |
| 4 | empty in solve mode (`pu_a` in edit mode) | ignored in solve | empty |
| 5 | `centerlist`, delta-encoded JSON array | required | — |
| 6 | tab settings | optional | `[]` |
| 7 | answer-check flags, AND set (§3) | optional | — |
| 8, 9 | placeholders `"x"`; line 9 holding `comp` turns on contest mode | optional | `"x"` |
| 10 | Penpa version, JSON | optional; missing means `[0,0,0]` | `[3,1,3]` |
| 11 | full `mode` object (tool and style per layer) | optional | — |
| 12 | theme placeholder | optional | `"x"` |
| 13 | custom colours on: `0` or `1` | optional | `0` |
| 14 | `pu_q_col`, custom colours layer | optional | empty shell |
| 15 | `x` in solve mode | ignored | `x` |
| 16 | answer-check flags, OR set | optional | all false |
| 17 | genre tags, JSON array | optional | `[]` |
| 18 | custom success message, or `false` | optional | `false` |

Dandelo's 2021 link stops after line 7 and has a 20-field header `[ran]`; the
loader guards every optional line with an `if` `[read]`, so a short payload is
tolerated by design.

**Header fields** (`__export_text_shared`, `class_p.js:1932-1962`) `[read]`:

| # | Field | Value for a square board |
| --- | --- | --- |
| 0 | grid type | `square` |
| 1, 2 | `nx`, `ny` — board columns and rows, clue strips included | — |
| 3 | cell size in px | 38 or 40 in the published links |
| 4 | `theta` rotation | `0` |
| 5, 6 | reflect flags | `1`, `1` |
| 7, 8 | `canvasx`, `canvasy` | `(nx+1)*size`, `(ny+1)*size` — holds on all five links `[ran]` |
| 9, 10 | `center_n`, `center_n0` | index of the point nearest the board centre (below) |
| 11-14 | sudoku option flags | `0,0,0,0` |
| 15 | `Title: ` + title | commas as `%2C` |
| 16 | `Author: ` + author | commas as `%2C` |
| 17 | source URL | may be empty |
| 18 | rules text | `,`→`%2C`, line feed→`%2D`, `&`→`%2E`, `=`→`%2F` |
| 19 | border button | `ON` or `OFF` |
| 20 | multisolution | `false` unless the OR flag set is used |
| 21 | background image, itself `encrypt_data` of JSON | may be absent |

The header is split on `,` with no quoting, so an unescaped comma in title or
rules shifts every later field `[read]`.

### 1.4 Point indices on a square board

`Puzzle_square.create_point` (`class_square.js:47-186`) `[read]`. The board has
a hidden margin of **two** cells on every side: `nx0 = nx + 4`,
`ny0 = ny + 4`, and `S = nx0 * ny0`. With `x`, `y` counted from 0 over the
padded board (so the first real board cell is `x = 2, y = 2`):

| Point | Index | Position |
| --- | --- | --- |
| cell centre | `x + y*nx0` | centre of cell (x, y) |
| vertex | `S + x + y*nx0` | bottom-right corner of cell (x, y) |
| edge midpoint, horizontal edge | `2*S + x + y*nx0` | middle of the bottom edge of cell (x, y) |
| edge midpoint, vertical edge | `3*S + x + y*nx0` | middle of the right edge of cell (x, y) |

Four corner points and four compass points per cell follow from `4*S` on; a
U-Bahn link does not need them.

- **`center_n`** is the point nearest the middle of the board's bounding box
  (`search_center`, `class_p.js:764-798`; called before `space` trims the cell
  list, `class_square.js:200-210`) `[read]`. For even `nx = ny` that is the
  vertex `S + (nx/2 + 1) + (ny/2 + 1)*nx0`; for odd, the cell
  `(nx//2 + 2) + (ny//2 + 2)*nx0` `[inferred]`. Both formulas reproduce the
  five published headers: 375 (12x12), 286 (10x10), 476 (14x14, twice) and 84
  (9x9) `[ran]`.
- **`centerlist`** is the list of cell indices that make up the board. Line 5
  stores the first index and then successive differences
  (`__export_list_tab_shared`, `class_p.js:1966-1981`; undone at
  `general.js:2127-2136`) `[read]`. A full rectangle is
  `2 + space[2] ≤ x < nx0 - 2 - space[3]`, likewise for `y` with `space[0]`
  and `space[1]` (`class_square.js:206-210`). The list need not be a
  rectangle or sorted: Niverio's ends with three negative deltas that append
  three extra cells `[ran]`.
- **The frame** is derived from `centerlist` on load: every edge of a listed
  cell is a grid line, and an edge with a listed cell on one side only is the
  thick outline (`make_frameline`, `class_p.js:453-478`) `[read]`. A link does
  not carry the grid lines.

### 1.5 The `pu_q` object

A JSON object with these keys in every decoded link `[ran]`: `command_redo`,
`command_undo`, `command_replay` (each `{"__a":[]}`), `surface`, `number`,
`numberS`, `symbol`, `freeline`, `freelineE`, `thermo`, `arrows`,
`direction`, `squareframe`, `polygon`, `line`, `lineE`, `wall`, `cage`,
`deletelineE`, `killercages`, `nobulbthermo`. The loader re-creates the three
`command_*` stacks if missing and adds `polygon` if missing
(`general.js:2376-2399`) `[read]`. The fields a U-Bahn link uses:

- **`number`**: cell index → `[text, colour, submode]`. Every clue in the
  published links is `["3",1,"1"]`-shaped: the digit as a string, colour `1`
  (black), submode `"1"` (normal, centred) `[ran]`; the writer is
  `class_p.js:7997` `[read]`.
- **`symbol`**: cell index → `[value, name, layer]`; drawn for every key
  whether or not the cell is in `centerlist` (`draw_symbol`,
  `class_square.js:1471-1485`) `[read]`. The `cross` symbol takes four 0/1
  flags and draws a half-line from the cell centre for each
  (`draw_cross`, `class_square.js:2561-2571`). Working the angles through,
  the flags are **[right, down, left, up]** `[inferred from the code]`; the
  published icons agree (§2).
- **`line`**: `"a,b"` → style, with `a < b`, both cell-centre indices of
  adjacent cells for a centre-to-centre segment (`re_linemove`,
  `class_p.js:9139`) `[read]`. A key pairing a cell index with an edge-midpoint
  index is a half-segment (Niverio's icons, §2).
- **`lineE`**: `"v1,v2"` → style, both vertex indices: a segment drawn on a
  grid edge. KNT and Niverio use style `21` and Dandelo style `2` for the
  dividers `[ran]`.

## 2. How published U-Bahn puzzles are laid out

Three pure U-Bahn links decoded `[ran]`, plus two "Summation U-bahn" links
used only as examples of the answer check and of `space`.

| Puzzle | Link host and form | Board `nx` | Grid | Icons | Answer check |
| --- | --- | --- | --- | --- | --- |
| "U-Bahn (1)", KNT `[P2]` | swaroopg92, `?m=solve`, 1720 chars | 12 | 8x8 | `cross` symbols | none (no `a`, all flags false) |
| "U-Bahn 3", Dandelo `[P3]` | swaroopg92, `?m=solve`, 1556 chars | 10 | 6x6 | `cross` symbols | none; the page says "penpa+ ohne Lösungsüberprüfung" |
| "U-Bahn with Empty Cells", Niverio `[P4]` | swaroopg92, `?m=solve`, 2567 chars | 14 | 10x10 | half-lines in `line` | `a` present, `sol_loopline` |

The 6x6 for Dandelo matches the setter's own statement quoted in the first
note. The 8x8 and 10x10 are my reading of the divider lines and of where the
clues sit `[inferred]`; for Niverio the embedded answer confirms it (all drawn
cells lie in the 10x10 block) `[ran]`.

**The common layout** — all three agree `[ran]`:

- `space` is `[0,0,0,0]`; the clue cells are ordinary board cells inside the
  frame, so the board is `(n+4) x (n+4)` for an `n x n` grid.
- **Four clue rows above** the grid and **four clue columns to its left**;
  nothing on the right or below. In padded coordinates the clue rows are
  `y = 2..5`, the clue columns `x = 2..5`, and the grid is `x, y ≥ 6`.
- The 3x3 block at the top-left corner (`x, y = 2..4`) is **left out of
  `centerlist`**, so the board is an L-shaped table with a notch.
- **Header icons**: the icon for a clue row sits in column `x = 5` of that
  row, and the icon for a clue column in row `y = 5` of that column. Cell
  (5, 5) holds one icon that serves both the innermost row and the innermost
  column.
- A clue for grid column `c`, piece row `y`, is the number at cell `(6+c, y)`;
  for grid row `r`, piece column `x`, at `(x, 6+r)`.
- Thick `lineE` dividers run along the right of column 5 and the bottom of row
  5, separating icons and clues from the grid (KNT and Niverio in style `21`;
  Dandelo draws a similar set in style `2`).
- **None gives all the clues**: 19 numbers on KNT's 8x8 (of 64), 18 on
  Dandelo's 6x6 (of 48), 25 on Niverio's 10x10 (of 80). A blank clue is simply
  an absent key. A full-clue-set link in this layout is the same structure
  with every clue cell filled; I found no published example of one.

**Piece order differs by setter** `[ran]`, reading from the outside in:

| Setter | Position 2 (outermost) | 3 | 4 | 5 (innermost, shared cell) |
| --- | --- | --- | --- | --- |
| KNT | crossroads | T-junction | straight | corner |
| Niverio | crossroads | T-junction | straight | corner |
| Dandelo | T-junction | straight | crossroads | corner |

The corner is innermost in all three. For Niverio I checked the reading
against the embedded answer: classifying every answer cell by its degree and
counting per row and column reproduces all 25 clue numbers with the order
crossroads, T, straight, corner, zero mismatches `[ran]`. KNT and Dandelo
carry no answer, so their order is read from the icon cells alone.

**How the icons are drawn** `[ran]`:

- KNT and Dandelo use the `cross` symbol with flags [right, down, left, up]:
  crossroads `[1,1,1,1]`; T `[1,1,1,0]` in the row header and `[1,1,0,1]` in
  the column header; straight `[1,0,1,0]` (horizontal) in the row header and
  `[0,1,0,1]` (vertical) in the column header; corner `[0,0,1,1]` (KNT) or
  `[1,1,0,0]` (Dandelo). Layer is `1` for KNT and `2` for Dandelo.
- Niverio draws each icon as half-segments in `pu_q.line`, style `2`, each key
  a cell index paired with one of its edge-midpoint indices.

**Which tool the solver opens in** `[ran]`: KNT and Dandelo have line 2 ending
`~"surface"~["",1]`, so the link opens in the shading tool and the solver
switches to Line by hand. Niverio has `~"line"~["1",3]`: it opens in Line,
normal submode, style 3 (green). Line 2's second and third parts set the
answer tool and its settings on load (`general.js:2481-2491`) `[read]`.

**An alternative seen on the Summation links** `[P5]` `[ran]`: `space` is
`[3,0,3,0]` and `centerlist` is the plain grid rectangle, so the clue cells
are outside the frame and the numbers float beside it. This also loads
numbers and, by `draw_symbol`, symbols in those cells; no notch or divider
lines are needed.

## 3. Answer check

- **Where it lives.** `maketext_solve_solution` (`class_p.js:2322-2329`)
  appends `&a=` plus `encrypt_data(JSON.stringify(this.make_solution()))`.
  On load the inflated text is stored as `pu.solution`
  (`general.js:2406-2415`) `[read]`.
- **What it compares.** After solver input, `check_solution`
  (`class_p.js:13375-13410`) recomputes `JSON.stringify(make_solution())` from
  the solver's layer and fires the success dialog when it is **string-equal**
  to `pu.solution`. So the `a` text must match Penpa's own serialisation
  byte for byte `[read]`.
- **The solution value** (`make_solution`, `class_p.js:2606-2800`) is an array
  of six arrays: shading, lines, edges, walls, numbers, symbols. Each is
  filled only if its flag is on, and each is sorted with JavaScript's default
  string sort `[read]`.
- **The flags** are line 7: an object keyed by the ids of the "all
  constraints" checkboxes. The current page has twenty: `sol_surface_exact`,
  `sol_surface`, `sol_number`, `sol_loopline_exact`, `sol_loopline`,
  `sol_ignoreloopline`, `sol_loopedge_exact`, `sol_loopedge`,
  `sol_ignoreborder`, `sol_wall`, `sol_square`, `sol_circle`, `sol_tri`,
  `sol_arrow`, `sol_math`, `sol_battleship`, `sol_tent`, `sol_star`,
  `sol_akari`, `sol_mine` (`docs/index.html`) `[read]`. The loader looks each
  checkbox up by id, so key order is free and a missing key reads as off
  (`general.js:2416-2422`) `[read]`. If **no** flag is on, every category is
  checked (`checkall_status`, `class_p.js:2355-2384`).
- **Lines only.** With `sol_loopline` on and the rest off, slot 1 is filled by
  `get_line_solution(false, false)` (`class_p.js:2457-2503`): for each key in
  the solver's `line`, a segment in style `3` (green) contributes
  `"a,b,1"` and style `30` (double) `"a,b,2"`; other styles are ignored unless
  the solver has the personal setting "ignore line style" on `[read]`. The
  published check payloads are exactly this shape: `[[],[…],[],[],[],[]]` with
  entries like `"114,115,1"` `[ran]`.
- **It checks drawn segments, not the rules.** The comparison is the set of
  segments. That is the right test only for a puzzle with one solution, which
  the finder's uniqueness check must already guarantee `[inferred]`.
- **Published precedent**: Niverio's U-Bahn variant and both Summation links
  carry `a` with `sol_loopline: true`, every other flag false (seventeen keys
  in Niverio's older link, twenty in the Summation ones), the OR set all
  false and header field 20 `false` `[ran]`.
- **`sol_loopline_exact`** instead records each segment's actual style number
  (`"a,b,<style>"`), so the solver must draw in the one style the answer
  names `[read]`.
- **A conflicting third-party report.** The Icelom generator `[P8]` says in
  its header comment that in a headless-Chrome test on 2026-09-18 a link with
  `sol_loopline` never reported solved, and that only `sol_loopline_exact`
  with style 9 did. That contradicts my reading of `get_line_solution` and the
  three published links above, which Penpa+ itself generated. I could not
  tell from its source which pen its test drew with. Unresolved until a
  browser check (§6).

## 4. Existing tooling

**In this repo: none.** `rg -uu -i penpa` over the worktree hits eight files:
this topic's first note, one table row in
`docs/research/connectivity-techniques.md:29`, a page-text pattern
"Solve in Penpa" in `finders/copycat-scan/parse_copycat.py:34`, the
identifier `openPage` in `examples/dutch-flatmates/app-open.mjs`, and four
`PUZZLE_LINK*.txt` files where the five letters occur by chance inside a
SudokuMaker base64 blob. No encoder, decoder or index helper `[ran]`.

**Outside**, each read at the cited commit:

- **Icelom `tools/json2penpa.py`** `[P8]` — the closest match: a
  standard-library-only Python script that builds a `#m=solve&p=…&a=…` link
  **from nothing** for a loop puzzle on a square board. It carries the
  `COMPRESS_SUB` table (with the `z` escape), the index formulas of §1.4, a
  `search_center` port, delta-encoded `centerlist`, a blank-padded 19-line
  payload and `zlib.compressobj(9, zlib.DEFLATED, -15)`. No licence checked;
  I read it as evidence, not as code to copy.
- **noqx `noqx/puzzle/penpa.py`** `[P6]` (Apache-2.0) — decodes an
  `m=edit&p=` payload, writes a solver's answer into line 4 and re-encodes
  with `compress(...)[2:-4]` (zlib output with header and checksum sliced
  off). It round-trips a link Penpa+ made; it does not build one. Its table
  renames some keys and omits the `z` escape, so it is not a faithful copy of
  `COMPRESS_SUB`.
- **puzzlekit `src/puzzlekit/formats/penpa_converter.py`** `[P7]` (MIT, on
  PyPI as `puzzlekit` 0.3.4) — decodes Penpa+ links and builds `m=edit` links
  from a per-genre template. No `a` parameter in the file.
- **`semiexp/penpa-edit-py`** `[P9]` — described as a "Python interface for
  penpa-edit" but the repository holds a `LICENSE` file only.

**Not found on PyPI under these exact names** (each returned 404 from
`https://pypi.org/pypi/<name>/json`): `penpa`, `penpa-edit`, `pypenpa`,
`penpa-tools`, `penpaplus`, `penpy`, `noqx`. I did not read the PyPI search
results page.

**Seen in search results but not opened**: `bay-puz/penpa-helper`,
`marktekfan/sudokupad-penpa-import` (JavaScript),
`kevinychen/collaborative-penpa`, `AniviaFlome/super-sudoku`
(`scripts/decode_penpa.py`, `craft_mini_penpa.py`),
`Chtho11y/logic-solver-skill` (`puzzle/importing/penpa.py`),
`miguelbper/jane-street-puzzles` and `nmay231/everything_else` (one file
each naming penpa-edit). The GitHub searches were `gh search repos` for
"penpa" (40 results listed), for "penpa-edit" (6) and for "penpa" with
language Python (20), matched on repository name and description, and
`gh search code "penpa-edit"` with language Python (18 file hits in 7
repositories); GitHub code search is not exhaustive.

## 5. What an encoder must do, step by step

Recommendations here are mine; flag any you disagree with. For an `n x n`
grid with all `8n` clues:

1. **Board.** `nx = ny = n + 4`, `nx0 = n + 8`, `S = nx0 * nx0`,
   `space = [0,0,0,0]`. Grid cell (r, c) is padded cell `(x, y) = (6+c, 6+r)`,
   index `x + y*nx0`. *Recommendation:* the KNT/Niverio layout of §2 — it is
   what a U-Bahn solver has seen before. The `space = [4,0,4,0]` layout is
   less work (no notch, no dividers) and is the fallback.
2. **Piece order.** *Recommendation:* crossroads, T, straight, corner from the
   outside in (two of the three setters). Chris's brief lists them the other
   way round (corner first); only the corner-innermost part is common to all
   three published puzzles, so this is his call.
3. **`centerlist`.** Rows `y = 2..4`: cells `x = 5..n+5`. Rows
   `y = 5..n+5`: cells `x = 2..n+5`. Write the first index, then differences.
4. **`number`.** For every grid column and every piece row, and every grid
   row and every piece column, `index → [str(count), 1, "1"]`. Zero is the
   string `"0"`, as published.
5. **`symbol`.** Seven `cross` icons: (5,2), (5,3), (5,4) for the rows, (2,5),
   (3,5), (4,5) for the columns, (5,5) for the corner, each
   `[[r,d,l,u], "cross", 1]`.
6. **`lineE`** (optional decoration). Vertex pairs along the right of column 5
   and the bottom of row 5, style `21`. The outline needs nothing.
7. **Lines of the payload.** Header per §1.3 with `canvasx = (nx+1)*size`,
   `center_n = center_n0` per §1.4, rules text escaped, `OFF`, `false`. Line
   2 `["1","2","1"]~"line"~["1",3]` so the link opens in the green Line tool
   the check counts. Line 7 the twenty flags with only `sol_loopline` true.
   Line 10 the version of the Penpa source this note read, `[3,2,4]`
   (`class_p.js:208`), or `[3,1,3]` as published. Line 11 a `mode` object
   whose `pu_a.edit_mode` is `line`. *Recommendation:* write all 19 lines in
   the published shape rather than the minimal set; the loader tolerates
   less, but the published shape is the one known to work.
8. **Serialise** each JSON line compactly (no spaces), join with line feeds,
   apply `COMPRESS_SUB` in order, UTF-8 encode, raw-deflate
   (`zlib.compressobj(wbits=-15)`), base64, strip `=`.
9. **Answer.** For each adjacent pair of grid cells joined in the network,
   the string `"<min index>,<max index>,1"`. Sort the strings, wrap as
   `[[],[…],[],[],[],[]]`, serialise with no spaces, raw-deflate, base64,
   strip `=`. No abbreviation table.
10. **URL.** `https://swaroopg92.github.io/penpa-edit/#m=solve&p=<p>&a=<a>`.
11. Write the link to a file, never to chat — it is a multi-KB blob, like a
    SudokuMaker link.

**Is it straightforward?** Yes `[inferred]`: standard library only (`json`,
`zlib`, `base64`), no new dependency, roughly the size of Icelom's
`build_text` plus an index helper.

## 6. Round-trip risk and verification

**What must match byte for byte:**

- The **inflated `a` text**. It is string-compared with
  `JSON.stringify(make_solution())`. Three things carry the risk: no
  whitespace (`json.dumps` needs `separators=(",", ":")`), key order
  smaller-index-first, and sort order. JavaScript's default sort compares
  UTF-16 code units; Python's `sorted` on these all-ASCII strings gives the
  same order `[inferred]`. Regenerating Niverio's published answer text that
  way from its own parsed entries reproduced it exactly `[ran]`.
- The **`COMPRESS_SUB` table**, entries and order. A wrong or missing entry
  yields text that does not parse as JSON on load.
- The **header field order** and the escapes inside it.

**What Penpa+ tolerates:**

- **The deflate bytes.** Any valid raw-deflate stream inflates to the same
  text; the compressor need not match zlib.js. Re-encoding Niverio's payload
  with Python's `zlib` gave a different, shorter base64 string (1892
  characters against the published 1955) that my decoder inflated back to
  the identical text `[ran]`. That Penpa's `Zlib.RawInflate` accepts Python's
  stream is `[inferred]` from the format being standardised and from
  noqx, puzzlekit and Icelom all shipping Python-compressed links; I did not
  run zlib.js.
- Base64 padding present or absent; `?` or `#`; missing optional lines; key
  order inside JSON objects; flag-object key order.

**What a test can verify without a browser** (proposals, mine):

- Round trip: decode(encode(model)) equals the model, with an independent
  decoder written from §1.2.
- Layout: decode the emitted link, classify each answer cell by degree,
  recount per row and column through the §2 mapping, and compare with the
  `number` field — the same check that confirmed Niverio's link.
- Answer text: assert the exact string for a small hand-built network.
- Header arithmetic: `canvasx` and `center_n` against the five published
  values in §1.4.
- Structural: every `number` and `symbol` key is in `centerlist`; every answer
  endpoint is a grid cell; `centerlist` deltas rebuild the intended set.

**What only a browser can confirm:**

- That Penpa+ renders the board where expected (a wrong `center_n` or canvas
  size shifts or clips the drawing rather than failing).
- That the icons look right and face the right way.
- That the link opens in the green Line tool.
- That drawing the network fires the success dialog — and so which of the
  §3 readings is right, mine or Icelom's. `pu.sol_flag` becoming `1` is the
  observable (`class_p.js:13400`); Icelom's comment describes reading it
  from headless Chrome.
- That the link survives whatever shortener or chat client carries it.

## 7. Not verified

- **Anything in a browser.** No link, published or generated, was opened in
  Penpa+.
- **The `sol_loopline` disagreement** with Icelom's report (§3).
- That `atob` and `Zlib.RawInflate` behave as I assume on unpadded input and
  on Python's deflate output.
- The `[right, down, left, up]` flag order is derived from the drawing code
  and agrees with the published icons, but I did not see it drawn.
- The meaning of line style numbers `2`, `21` and of symbol layer `1` versus
  `2` beyond what the excerpts show.
- Whether a full `8n`-clue board in this layout is legible at Penpa's default
  cell size; no published puzzle gives every clue.
- KNT's and Dandelo's grid sizes and piece order beyond what the icon and
  divider positions imply (they embed no answer to cross-check).
- The Puzzlewiki pages (still blocked to the local crawler) and whether LMD
  documents a standard clue order.
- Licences of Icelom and of the unopened repositories in §4.
- Line numbers against any Penpa commit other than `34e3fe9`; the deployed
  site may run a different revision.
- Forks: the two Summation links point at `zwegner.github.io/penpa-edit`; I
  did not compare that fork's loader with `[P1]`.

## 8. Browser check, 2026-10-10 (#774)

Ran in the local session with `finders/ubahn/penpa-browser-check.mjs`
(Playwright, headless Chromium) against the live swaroopg92 page, which
announced Penpa+ v3.2.4, on links `finders/ubahn/penpa.py` made: a 4x4 hand
network, the same with the blank option, a 3x5 board and a 6x6 network from a
real hunt. All four passed every check. Results, each settling a § 7 item:

- **Python's deflate output loads.** The page inflated `zlib.compressobj`
  streams, unpadded base64 and the `#m=solve&p=…&a=…` form.
- **The embedded check works headless.** Drawing the answer's edges with the
  mouse in the green Line tool set `pu.sol_flag` to 1 and showed the
  "Congratulations!" dialog; the answer with one edge missing, and a network
  of the same size with one edge moved, did not. That is the § 3 reading, not
  Icelom's. Its test may have drawn in another line style; I did not find out.
- **The link opens in Line**, normal submode, green, in solving mode ("Solver
  Mode (Answer Checking Enabled)").
- **Icon flags are [right, down, left, up]**: the row strip's branch icon
  draws left, right and down, the column strip's draws right, down and up.
  The arms reach the cell edges, so an icon looks like a piece of track.
- **The ruled order renders as ruled.** From the outside in, rows and
  columns alike: hollow square (only with the blank option), cross, branch,
  straight, turn. The script reads this from the page's own question layer
  and the screenshots agree.
- **The blank icon** is a number cell whose text is U+25A1; it renders as a
  small hollow square.
- **The centre point matches Penpa+'s own.** The script sets `pu.center_n` to
  0, calls `pu.search_center()` and compares: 209 (8x8 table), 84 (9x9), 71
  (9x7), 383 (9x8) and 545 (8x9) all agree with § 1.4's rules, which covers
  the mixed-parity edge-midpoint cases the five published headers could not.

## Sources

Repo files are cited inline as `path:line`. Outside sources:

- **P1** — penpa-edit, swaroopg92, commit
  `34e3fe97804e518288870b70d919e7e76ee18b4d` ("typo fix in line", 2 June
  2026). Files read: `docs/js/class_p.js`, `docs/js/general.js`,
  `docs/js/class_square.js`, `docs/index.html`, header of
  `docs/js/libs/zlib.js`.
  https://github.com/swaroopg92/penpa-edit/tree/34e3fe97804e518288870b70d919e7e76ee18b4d
- **P2** — "U-Bahn (1)", KNT, LMD Rätselportal, 15 April 2023; Penpa+ link via
  the page's `tinyurl.com/246thhlq`.
  https://logic-masters.de/Raetselportal/Raetsel/zeigen.php?chlang=en&id=000DKS
- **P3** — "U-Bahn 3", Dandelo, LMD Rätselportal, 31 January 2021; Penpa+ link
  via `t1p.de/ubahn3rep` in the setter's comment of 1 February 2021 (the
  link's author field reads Michael Niermann-Rossi).
  https://logic-masters.de/Raetselportal/Raetsel/zeigen.php?chlang=en&id=0005BN
- **P4** — "U-Bahn with Empty Cells", LMD Rätselportal, 28 June 2024; Penpa+
  link via `tinyurl.com/2oqstlm2` (the link's author field reads Niverio).
  https://logic-masters.de/Raetselportal/Raetsel/zeigen.php?chlang=en&id=000IPE
- **P5** — "Classic Summation U-bahn", Playmaker6174, LMD Rätselportal,
  6 November 2025; Penpa+ links via `tinyurl.com/22sjxn96` (6x6 example) and
  `tinyurl.com/26zm3lpo`.
  https://logic-masters.de/Raetselportal/Raetsel/zeigen.php?chlang=en&id=000PZY
- **P6** — `noqx/puzzle/penpa.py`, T0nyX1ang/noqx, commit
  `706540dfb4c7d67919bb5029e4741838c5981501` (7 July 2026).
  https://github.com/T0nyX1ang/noqx/blob/706540dfb4c7d67919bb5029e4741838c5981501/noqx/puzzle/penpa.py
- **P7** — `src/puzzlekit/formats/penpa_converter.py`, SmilingWayne/puzzlekit,
  commit `9ef8ebbb262039401d72e37af0d23f9c9b46a5b0` (24 May 2026).
  https://github.com/SmilingWayne/puzzlekit/blob/9ef8ebbb262039401d72e37af0d23f9c9b46a5b0/src/puzzlekit/formats/penpa_converter.py
- **P8** — `tools/json2penpa.py`, ProximaCentauri0/Icelom, commit
  `642597865a05e051e81cfc91aa76fae2459bea85` (21 September 2026).
  https://github.com/ProximaCentauri0/Icelom/blob/642597865a05e051e81cfc91aa76fae2459bea85/tools/json2penpa.py
- **P9** — semiexp/penpa-edit-py, commit
  `d90cf27b08c5da98a97024d662b116efdca02eec` (22 August 2022); file tree read,
  one file.
  https://github.com/semiexp/penpa-edit-py/tree/d90cf27b08c5da98a97024d662b116efdca02eec
