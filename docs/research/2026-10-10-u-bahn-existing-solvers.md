# U-Bahn: does a solver or generator already exist?

**Date:** 2026-10-10
**Question.** The first U-Bahn note
(`docs/research/2026-10-10-u-bahn-cpsat-finder.md` § 5) reported "no solver or
generator found" after a file-name pass over six solver collections and a
rate-limited code search. Chris asked for a much harder look: does a solver or
generator for U-Bahn exist anywhere, under any name?

**Method.** Reading and searching only. No downloaded code was executed and no
solver was run on this box. I read source files through the GitHub API at a
named commit, downloaded the source tarballs of eleven repositories and
grepped every file's *contents*, ran GitHub code, repository and issue
searches, and read the web pages cited. Each claim is tagged `[read]` (I read
it in the cited file or page), `[ran]` (the result of a grep, search or HTTP
probe I ran today) or `[inferred]` (my reasoning). Source numbers `[E1]`…
refer to the list at the end. The search log in § 4 says what each search
matched against, because a miss on a file name is not a miss on contents.

## 1. Verdict

**One exists.** `JWKNT/logical-solver` `[E1]` is a public JavaScript U-Bahn
solver with exact search, a two-solution uniqueness check, a per-segment
"true candidates" mode, a human-rule stepper and a random-puzzle button. It
went up on 8 July 2026 and is served at https://jehlp.net/logical-solver/. The
first pass missed it because the word `ubahn` is in its README and build
script, not in a file name inside any of the collections that were searched.

It is a solver with a thin generator on top: the "random puzzle" draws one
random network and writes out its full clue set, and does not check that the
result is unique or strip clues `[read]`. So the piece Chris's finder is
meant to add — search for unique puzzles, with a quality bar — I did not find
anywhere.

It has **no licence file**, so its code cannot be copied into this repo
without the author's permission. Running it locally as a cross-check oracle
is a separate question, and is Chris's to rule on (§ 2.1).

**Nothing else solves U-Bahn** in the places listed in § 4: no hit in the
contents of cspuz_core, cspuz, cspuz-solver2, noqx, nikoli-puzzle-solver, noq,
grilops, puzzlekit, Puzzlink_Assistance or penpa-edit; one more repository
lists U-Bahn in its rule catalogue as *not implemented* (§ 2.2). That is
"none found in those places". § 5 lists what I did not cover.

## 2. Candidates found

### 2.1 JWKNT/logical-solver — a real U-Bahn solver

Repository https://github.com/JWKNT/logical-solver, read at commit
`0603a978ed86af43bdd872d90d9882b0c63c1e8f` (9 October 2026) `[E1]`.

| Point | Finding | Basis |
| --- | --- | --- |
| What it solves | Standard U-Bahn, an exact rule match: edges between adjacent cell centres, cell degree 0, 2, 3 or 4 (degree 1 is rejected), one connected component and at least one line, and per row and column an exact count for each given clue of cross (degree 4), branch (3), straight (2 opposite) and turn (2 adjacent). A crossroads is a real 4-way junction. Any clue may be blank | `[read]` `js/engine.js:106-112` (degree and shape), `:81-88` (one component at the end), `:15-27` (clue arrays, `-1` = no clue) |
| Variants it also takes | Blocked ("shaded") cells, and an optional fifth clue per line counting **empty** cells (a blocked cell counts as empty) | `[read]` `js/engine.js:15-27`, `:108-109`; rules text on the hosted page `[E2]` |
| Variants it does not take | Summation U-Bahn, Haltestellen, and the hybrids of the first note's § 1.4: no code path reads anything but the count clues and the blocked mask | `[inferred]` from reading `makeEngine` and `gatherConfig` (`js/app.js:232-247`); I did not read the 171 KB `js/stepper.js` |
| Engine | Hand-written depth-first search in plain JavaScript, run in a Web Worker. No SAT, CP or ILP library: `js/engine.js` never references the vendored SAT runtime, which the README assigns to the Cave tab | `[read]` `js/engine.js:2-4`, README "Layout"; `[ran]` `grep -n 'logic-solver\|Logic\.' engine.js` returns nothing |
| Encoding | Cells in row-major order; at each cell it branches on two booleans, "edge right" and "edge down" (four options), with the left and up edges already fixed by earlier cells | `[read]` `js/engine.js:59`, `:89-105` |
| Connectivity | Frontier union-find with a count of open ends per component (`pending`). When a component's last open end closes while another component exists, the branch dies; once one component has closed, no later cell may hold a line, and the closure is refused while any piece clue is still unmet. A leaf is a solution only with exactly one component | `[read]` `js/engine.js:32-53` (`connect`), `:108`, `:137-146`, `:81-88` |
| Pruning | Per-line clue overshoot, and "remaining clue deficit exceeds remaining cells in this row or column" | `[read]` `js/engine.js:113-126` |
| Uniqueness | Yes. `runSolve` searches for up to **two** solutions; the page has one status for "Solved — the solution is unique" and another, "Uniqueness not verified", for when the time limit was reached while checking for a second solution | `[read]` `js/engine.js:169-178`, `js/app.js:295-297` |
| True candidates | For every edge and cell: in all solutions, some, or none, by one satisfiability search per segment with the segment forced, not by enumeration. Undetermined results on timeout are reported as such | `[read]` `js/engine.js:6-11`, `:180-447`; hosted page text `[E2]` |
| Generation | A "Random puzzle" button: one search with a shuffled branch order and no clues, first network found, then every clue (including the empty count) derived from it. **No uniqueness check, no clue stripping, no difficulty filter** in that path; the status line tells the user to "clear some clues and re-run True candidates" by hand | `[read]` `js/app.js:347-372`, `js/engine.js:173`; `randomize` at `:96-99` |
| Human-style solving | "Take step": about 36 named deduction rules, simplest first, with prose explanations | `[read]` README and hosted page `[E2]`; the rule code itself (`js/stepper.js`) not read |
| Its own tests | The engine's statuses and exact solution counts are compared with a brute force over all edge subsets on 2x2, 3x3 and 3x4 boards and on 60 random 3x4 puzzles with full and partial clues and blocked cells | `[read]` `tests/engine.test.js:1-130`. I did not run them, so "the tests pass" is unverified |
| Time limit | Default 10 s, user-settable 1-600 s | `[read]` `js/engine.js:28`, `js/app.js:245` |
| Import and export | None found: no Penpa+, puzz.link or pzprv3 reader or writer. Clues are typed into the page | `[ran]` `grep -n -i 'penpa\|puzz.link\|pzpr\|import\|export'` over `js/app.js` returns no match |
| Licence | **None.** The API reports `license: null`, the root listing has no `LICENSE` or `COPYING`, and the one licence file in the tree covers the vendored SAT runtime only (MIT, Meteor Development Group) | `[ran]` `gh api repos/JWKNT/logical-solver`; root listing; `[read]` `js/vendor/logic-solver.LICENSE` |
| History | First commit `71c3a8c1` "U-Bahn solver: engine, human-rule stepper, UI, and test batteries", 8 July 2026; 89 commits; last 9 October 2026 | `[ran]` commits API |
| Author | GitHub user `JWKNT`, display name "jw", profile bio "KNT". That this is the Rätselportal setter KNT (author of "U-Bahn (1)" and "U-Bahn with Empty Clues (4)") is my inference from the bio, the README naming "KNT's *Extraterrestrial Japanese Sums*" as a reference puzzle, and the empty-count clue matching that puzzle series | `[inferred]`; `[E1]`, `[E7]` |

**Could it run here as an oracle?** Technically yes `[inferred]`:
`tests/engine-node.js` is a 26 KB copy of the engine ending in
`module.exports = { runAny, runSolve, runCandidates, runStep }` with no
`require` or `import` (`[ran]` grep count 0), so it needs Node and nothing
else. A config is `{ R, C, rowClue, colClue, blocked, mode, timeLimit }` with
`rowClue` a flat `R*4` array in the order cross, branch, straight, turn and
`-1` for no clue `[read]`. What stands in the way:

- **No licence.** Vendoring it under `examples/` or `finders/` would be
  copying unlicensed code. A cross-check that fetches it at a pinned commit
  into a scratch directory is not redistribution, but it is still someone
  else's unlicensed code and a new outside input to a test. Flag for Chris;
  asking the author for a licence is the clean route.
- **I did not run it**, so every statement about its speed, and that its tests
  pass, is unverified. A row-major search with clue-deficit pruning is
  `[inferred]` to be fine at 6x6 with full clues and to degrade on larger or
  sparser boards; the page's own 600-second ceiling and "undetermined (time
  limit)" status suggest the author met that.
- It shares nothing with a CP-SAT model, which is what makes it interesting as
  the "verify with code that shares nothing with the finder" seat
  (`docs/agents/grid-finder-lessons.md:130-132`). The repo's own brute-force
  or flood-fill oracle fills that seat without the licence question.

### 2.2 Chtho11y/logic-solver-skill — U-Bahn catalogued, not implemented

Repository https://github.com/Chtho11y/logic-solver-skill, `master` at
`a3e0c9f058cec6730584f01bf9ed0939339346a4` (29 September 2026), MIT `[E3]`.
A puzzle-rule DSL compiled to a cspuz back end, with a Penpa+ canvas front
end `[read]` README. Its rule catalogue `rules.txt` has a row `ubahn … U-Bahn
地铁` with the full rule in Chinese, including two extras: some cells may have
their connections given, and black cells take no line `[read]`. But
`IMPLEMENTATION_STATUS.md` lists `ubahn` under "尚未实现" (not yet
implemented), and the tree holds no `impls/ubahn.dsl` or `impls/ubahn.json`
`[read]`, `[ran]` (a grep of all 610 files hits only those two documents).

So: **not a solver today**, but the one general collection I found that has
U-Bahn on its to-do list, and it would get a cspuz (SAT) model if it lands.

## 3. Adjacent tools that are not solvers

- **pzprjs `ubahn` variety** — editor, URL and file codec and answer checker;
  the first note's S5. Pull request #724 "Add U-Bahn" by `x-sheep` (Lennard
  Sprong), opened 23 May 2026, merged 25 May 2026, has an empty description,
  no review and one bot comment; its 13 files are the variety, its test, an
  icon and UI lists — no solver or generator `[read]` `[E4]`.
- **puzz.link does not serve it.** The deployed site loads
  `pzpr.js?0fdc47e4…`, which is pzprjs commit `0fdc47e4` of 1 January 2024;
  that `pzpr.js` (380 KB) contains no `ubahn`, and
  `https://puzz.link/js/pzpr-variety/ubahn.js` is a 404 while
  `…/nurikabe.js` is a 200. The development deployment
  `https://pzprxs.vercel.app` does serve `js/pzpr-variety/ubahn.js` (200,
  7.6 KB) `[ran]` `[E5]`. A finder that wants a pzprjs link should target
  pzprxs, not puzz.link.
- **Lennard Sprong's other repositories** — `x-sheep/puzzles-unreleased`
  (13 unfinished games for Simon Tatham's collection: abcd, ascent, boats,
  bricks, clusters, crossing, mathrax, rome, salad, seismic, spokes, sticks,
  subsets) and `x-sheep/puzzles` (a Windows Store build of the collection).
  No file is named for U-Bahn `[ran]` (tree listing of `puzzles-unreleased`;
  the other 30 repositories judged by name and description only). Tatham-style
  games carry a generator and solver, so a U-Bahn game there would have been
  a hit; there is none by file name, and I did not read the C sources of
  `crossing`, `spokes` or `sticks` to rule out a U-Bahn rule under another
  name.
- **Icelom** (`ProximaCentauri0/Icelom`, MIT, commit `64259786`) — the
  repository behind `tools/json2penpa.py` in the Penpa note. It is a solver
  for one puzzle, Icelom (pzprjs `icelom`): a single-file C++ core
  (`icelom_solver.cpp`), a tkinter GUI, and a vendored pzprjs used as an
  answer oracle `[read]` (repository description and tree). Nothing in it
  solves or generates U-Bahn; its vendored pzprjs tree stops at the
  alphabetical listing I read (`…icebarn.js, icewalk.js, ichimaga.js`), so I
  did not confirm whether that copy includes `ubahn.js`.
- **Penpa+** — no U-Bahn genre tag, answer mode or solver hook: no file among
  the 507 at commit `34e3fe9` contains `u-bahn`, `ubahn`, `u_bahn`, `subway`
  or `underground` outside the icon font's CSS `[ran]`. U-Bahn puzzles in
  Penpa+ are generic line drawings with the generic line answer check, as the
  Penpa note already describes.
- **croco-puzzle** had a U-Bahn *player applet* with a "Rätselautomat" (LMD
  forum, 14 April 2009 `[E8]`; UK Puzzle Association translation of the
  applet rules, 13 April 2011 `[E9]`). Whether its puzzles were machine-made
  or machine-checked the threads do not say. `croco-puzzle.com` today
  redirects to a parking page `[ran]`, so nothing there can be inspected.
- **wooferzfg's site** — six U-Bahn puzzle pages
  (`puzzles/ubahn*.html`) with Penpa+ and SudokuPad links; a puzzle set, not
  a tool. None of the author's 40 most recently pushed repositories is named
  for a U-Bahn solver `[ran]` (judged by name and description).
- **Uniqueness by hand.** On "U-Bahn 3" a solver (uvo) reported multiple
  solutions about six hours after publication and the setter replied that he
  had "even given it to a test solver" `[read]` `[E10]` — evidence that this
  setter checked uniqueness through people, not a program. One data point.
- **History, corrected.** The WPC unofficial wiki says the puzzle "is
  probably of a Hungarian origin and dates back to at least 2005", appearing
  at the 2005 Hungarian Nationals and at WPC 2005 Part 7 (Zoltán Horváth) and
  WPC 2019 Round 2 (Jürgen Blume-Nienhaus); only the name is German `[read]`
  `[E6]`. The first note recorded inventor and first appearance as "not
  found".

## 4. Search log

"Contents" means every file's text was searched; "name" means paths only.
GitHub code search is the legacy REST endpoint that `gh search code` uses.

**A calibration failure to read the global rows by.** Global code search with
two or more terms returned nothing even where a match is known to exist:
`ubahn puzzle` and `"U-Bahn" "dead ends"` both miss `JWKNT/logical-solver`'s
README, which contains all of those words, while the one-word query `ubahn`
finds it. So every multi-term global row below is **inconclusive**, not a
miss. One-word global queries work but return at most 100 files and are
swamped by public-transport code, so each is **capped**. Forks are not
indexed (`--owner x-sheep` finds nothing although his pzprjs fork has the
file). Repository-scoped search did find the known files in `robx/pzprjs` and
`JWKNT/logical-solver`.

### 4.1 Source trees grepped in full (contents)

Tarball of the default branch, extracted to a scratch directory,
`grep -r -i -l -E 'u-?bahn|u_bahn'` and a second pass for
`subway|metro|underground|tube map`.

| Repository | Commit | Files | Result |
| --- | --- | --- | --- |
| `semiexp/cspuz_core` | `d88f99c8` (6 Oct 2026) | 445 | no match |
| `semiexp/cspuz` | `1d074431` (27 Jul 2025) | 90 | no match |
| `semiexp/cspuz-solver2` | `0ab2725f` (24 Oct 2025) | 30 | no match |
| `T0nyX1ang/noqx` | `706540df` (7 Jul 2026) | 251 | no match |
| `kevinychen/nikoli-puzzle-solver` | `b02b4015` (11 Jan 2024) | 189 | no match |
| `mstang107/noq` | `22945620` (12 Oct 2025) | 344 | no match |
| `obijywk/grilops` | `18a66412` (19 Nov 2023) | 106 | no match |
| `SmilingWayne/puzzlekit` | `9ef8ebbb` (24 May 2026) | 280 | no match |
| `LeavingLeaves/Puzzlink_Assistance` | `22ac9eed` (20 Sep 2026) | 5 | no match |
| `swaroopg92/penpa-edit` | `34e3fe97` (3 Jun 2026) | 507 | no match (second pass hits the icon font CSS only) |
| `Chtho11y/logic-solver-skill` | `a3e0c9f0` (29 Sep 2026) | 610 | `rules.txt`, `IMPLEMENTATION_STATUS.md` — § 2.2 |

`jenna-h/puzzlink-assistance` in the brief does not exist (the tarball URL
returns 404); a repository search for the name found
`LeavingLeaves/Puzzlink_Assistance`, which is the row above. `hackerb9` has
no puzzle-solver repository by name or description across two pages of his
repository list (one unrelated hit, a Spelling Bee clone).

### 4.2 Repository-scoped GitHub code search (contents, indexed default branch)

| Repository | Query | Result |
| --- | --- | --- |
| `robx/pzprjs` | `ubahn` | 11 files, all the known variety (calibration) |
| `JWKNT/logical-solver` | `ubahn` | 7 files (calibration) |
| `hakank/hakank` | `ubahn`; `u_bahn`; `subway` | none; none; two unrelated probabilistic-programming files ("you have a train to catch") |
| `MiniZinc/minizinc-benchmarks` | `ubahn`; `subway` | none; none |
| `SmilingWayne/puzzlekit-dataset` | `ubahn` | none |
| `icsearch/ICS` | `ubahn` | none |
| `logicpuzzle-app/puzzle-kit` | `ubahn` | none |
| `approximatelabs/pencil-puzzle-bench` | `ubahn` | none |
| `o0cht0o/LogicPuzzleSolver` | `ubahn` | none |
| `Nana-Ki7/phagent-toolkit` | `ubahn` | none |
| `c01dkit/awesome-puzzlehunt` | `ubahn` | none |
| `wooferzfg/wooferzfg.github.io` | `ubahn` | six puzzle pages (§ 3) |
| owner `x-sheep` | `ubahn` | none (forks are not indexed) |

### 4.3 Global GitHub code search

| Query | Filter | Result |
| --- | --- | --- |
| `ubahn` | none | **capped at 100.** Transit code, plus `JWKNT/logical-solver` README, `Chtho11y/logic-solver-skill` `rules.txt` |
| `ubahn` | file name `ubahn` | first 70 rows read: transit code, `robx/pzprjs src/variety/ubahn.js`, wooferzfg's puzzle pages; nothing else puzzle-related |
| `ubahn` | JavaScript | capped at 100; no puzzle file outside pzprjs among the 60 rows I read |
| `ubahn` | Python | capped at 100; none puzzle-related among the 60 rows read |
| `ubahn` | Rust | 40 rows read; none puzzle-related |
| `ubahn` | TypeScript | capped at 100; none puzzle-related among 40 rows read after dropping obvious transit paths |
| `ubahn` | C++ | 40 rows read; none puzzle-related |
| `ubahn` | C | 30 rows read; none puzzle-related |
| `ubahn` | Haskell | one unrelated file |
| `ubahn` | Prolog | 11 files, all database or coursework code |
| `ubahn` | MiniZinc language; extensions `.mzn`, `.lp`, `.smt2`, `.pi` | none in each |
| `u_bahn` | Python | 40 rows read; all transit |
| `ubahn puzzle`; `ubahn solver`; `"U-Bahn" puzzle solver`; `u_bahn puzzle`; `pzprv3 ubahn`; `ubahn nurikabe`; `ubahn masyu`; `"U-Bahn" masyu`; `"U-Bahn" fillomino`; `ubahn clue`; `ubahn rowClue`; `"U-Bahn" "dead ends"`; `U-Bahn Sackgassen Linienführungen`; `ubahn puzzle` in Python, C++, TypeScript; `ubahn clues` in Python | none | **inconclusive** — returned nothing, including where a match is known (see the calibration note) |

Rate limiting: three batches hit HTTP 403 (10 code searches per minute); each
blocked query was re-run after the window and is reported above from the
re-run. `ubahn checkOneLoop` was blocked and not re-run.

### 4.4 GitHub repository and issue search (name, description, README)

| Query | Result |
| --- | --- |
| `ubahn puzzle` in name, description, README | 1: `JWKNT/logical-solver` |
| `"u-bahn" puzzle` in name, description, README | 15: `JWKNT/logical-solver`, the rest transit games and word lists |
| `ubahn solver` | 4: `JWKNT/logical-solver`, three transit route solvers |
| `"u-bahn" solver` | 33: `JWKNT/logical-solver`, the rest transit and metro-map layout |
| `"u-bahn" "logic masters"` in README | 0 |
| `"puzz.link" solver`; `pzprjs solver`; `penpa solver` | 29, 12, 31 repositories listed; used to find the collections in § 4.2. None is named or described as a U-Bahn tool |
| issues `ubahn puzzle solver`; `"U-Bahn" puzzle genre` | this repo's own #773; 0 |
| `repo:robx/pzprjs ubahn OR U-Bahn` (issues, commits) | PR #724 and commit `19cc9d83` only |

### 4.5 Other code hosts

| Where | Query | Field | Result |
| --- | --- | --- | --- |
| Codeberg API | `ubahn`; `u-bahn` | repository name and description | 1 unrelated (a barometer logger); 0 |
| GitLab.com API | `ubahn`; `u-bahn` | project name and description | 5 unrelated (Indonesian words containing the letters); 0 |
| sourcehut `sr.ht/projects?search=ubahn` | page text | **inconclusive**: the page listed unrelated projects, so the query did not appear to filter |

No contents search was run on any of the three (none is offered without an
account).

### 4.6 Web pages read

| Page | What I looked for | Result |
| --- | --- | --- |
| WPC unofficial wiki, "U-Bahn" `[E6]` | history, references | origin and appearances (§ 3); no tool named |
| `jehlp.net/logical-solver/` `[E2]` | the hosted tool | live (HTTP 200), text matches the repository |
| LMD forum, "U-Bahn Lösetechnik" `[E8]` | any mention of a program | a player applet only |
| UK Puzzle Association, "Croco Puzzle rules" `[E9]` | applet description | a player applet only |
| LMD Rätselportal "U-Bahn 3" comments `[E10]` | uniqueness checking | by test solver (§ 3) |
| janko.at `Raetsel/index.htm` (761 links) and `Raetsel/Uebersicht.htm` | `u-bahn`, `ubahn`, `subway`, `metro` on the first; `bahn` on the second | no match on either; the first note's direct URL was already a 404. janko.at does not appear to carry the genre |
| Cross+A puzzle list (177 KB) `[E11]` | `u-bahn`, `subway`, `metro`, `underground`, then `dead end`, `t-junction`, `crossroad`, `branch` | no match — this solve-and-generate program does not list the genre |
| CSPLib problem index (98 problem ids on the page) | `u-bahn`, `subway`, `metro`, `underground` | no match |
| Simon Tatham's collection page | `bahn`, `subway` | no match (the first note already read its game list) |
| arXiv API | `all:"U-Bahn" AND all:puzzle`; `all:ubahn` | 0 results each |
| Crossref API | `U-Bahn pencil puzzle NP-complete` | 8 titles returned, none about this puzzle |
| Web search (Exa, three queries; WebSearch, three queries) on a U-Bahn solver, generator, uniqueness program, or complexity paper | page text | Rätselportal puzzles, wooferzfg, feadoor, Broken Sign, the WPC wiki, a WSPC 2025 24-hour instruction booklet, and metro-map layout theses; no tool beyond § 2.1 and no paper on the puzzle |

Blocked or failed: `hakank.org` timed out from this box on four index pages
by `curl` and by the headless crawler, so Hakan Kjellerstrand's models were
checked through his GitHub mirror instead (§ 4.2), not through his pages.
Semantic Scholar's API returned 429. `croco-puzzle.com` is a parked domain.

## 5. Not covered

- **Anything not on GitHub's default-branch index or not public**: private
  repositories, Discord-only bots and scripts (the CTC and puzzle Discords
  were not searched at all — no public tooling repository for them turned up
  in the repository searches, and I have no way to read the servers), gists,
  and code inside forks.
- **A solver under a name that never says U-Bahn, Subway, Metro or
  Underground.** The content greps and searches key on those words. The C
  sources of `x-sheep/puzzles-unreleased` (`crossing.c`, `spokes.c`,
  `sticks.c`) and the puzzle lists of the collections in § 4.2 were not read
  for the rule itself.
- **Global code search beyond the first 100 hits** of each one-word query, and
  every multi-word global query (inconclusive, § 4).
- **Contents on GitLab, Codeberg and sourcehut**; only project names and
  descriptions were matched, and sourcehut's result is inconclusive.
- **`js/stepper.js`** in the candidate (171 KB): the human-rule ladder was not
  read, so I cannot say which deductions it knows or whether it could grade a
  puzzle's difficulty. That is the part most relevant to open question 5 of
  the first note.
- **Running the candidate.** No timing, no confirmation that its tests pass,
  no check of its answers against the pzprjs fixtures.
- **The Logic Masters Puzzlewiki** (blocked to the local crawler in both
  earlier notes; not retried, since it is a rules page) and the bulk of
  Rätselportal U-Bahn comment threads: I read one thread for uniqueness talk,
  not all of them.
- **Hakan Kjellerstrand's own pages**, CSPLib beyond its index page, clingo
  and ASP puzzle collections as such (covered only by the `.lp` extension
  search), Google Scholar, and Semantic Scholar.
- **Commercial or closed puzzle generators** other than Cross+A, and the
  croco-puzzle generator, whose site is gone.
- **Chinese- and Japanese-language sources** beyond the one repository found;
  its catalogue row shows the genre is known there as 地铁.

## Sources

- **E1** — JWKNT/logical-solver, commit
  `0603a978ed86af43bdd872d90d9882b0c63c1e8f` ("Restore original tool
  typography and retain folio Home", jw, 9 October 2026). Files read:
  `README.md`, `AGENTS.md`, `js/engine.js` (lines 1-260 in full, the rest by
  function outline), `js/app.js` (lines 228-247 and 345-375, plus a keyword
  grep), `tests/engine.test.js` (lines 1-175), `tests/engine-node.js` (head
  and tail), `js/vendor/logic-solver.LICENSE` (head).
  https://github.com/JWKNT/logical-solver/tree/0603a978ed86af43bdd872d90d9882b0c63c1e8f
- **E2** — "Logical Solvers · jehlp.net", the hosted build of E1; no author or
  date on the page. https://jehlp.net/logical-solver/
- **E3** — Chtho11y/logic-solver-skill, commit
  `a3e0c9f058cec6730584f01bf9ed0939339346a4` (29 September 2026). Files read:
  `README.md`, `rules.txt` (the `ubahn` row), `IMPLEMENTATION_STATUS.md`.
  https://github.com/Chtho11y/logic-solver-skill/tree/a3e0c9f058cec6730584f01bf9ed0939339346a4
- **E4** — "Add U-Bahn", pull request #724, robx/pzprjs, x-sheep, opened
  23 May 2026, merged 25 May 2026 as commit `19cc9d83bb435ff37c760bc07afdd5395c4a076f`.
  https://github.com/robx/pzprjs/pull/724
- **E5** — HTTP probes of 10 October 2026:
  `https://puzz.link/p?ubahn/4/4` (script tag `pzpr.js?0fdc47e4c63218adf832b5ad3057b4c6282faa0d`),
  `https://puzz.link/js/pzpr-variety/ubahn.js` (404),
  `https://pzprxs.vercel.app/js/pzpr-variety/ubahn.js` (200); commit
  `0fdc47e4` dated through
  https://github.com/robx/pzprjs/commit/0fdc47e4c63218adf832b5ad3057b4c6282faa0d
- **E6** — "U-Bahn", WPC unofficial wiki; no author or date shown.
  https://wpcunofficial.miraheze.org/wiki/U-Bahn
- **E7** — "U-Bahn with Empty Clues (4)", KNT, LMD Rätselportal, 28 July 2023.
  https://logic-masters.de/Raetselportal/Raetsel/zeigen.php?id=000EMR
- **E8** — "U-Bahn Lösetechnik", Logic Masters Forum, thread started by
  Calavera, 14 April 2009 (the first note's S9, re-read for mentions of a
  program). https://forum.logic-masters.de/archive/index.php?thread-376.html=
- **E9** — "Croco Puzzle rules.", UK Puzzle Association forum, thread started
  by PuzzleScot, 12 April 2011; the U-Bahn entry is drsteve's post of
  13 April 2011. https://forum.ukpuzzles.org/viewtopic.php?t=279
- **E10** — "U-Bahn 3", Dandelo, LMD Rätselportal, 31 January 2021; comments
  by uvo and Dandelo of 1 February 2021.
  https://logic-masters.de/Raetselportal/Raetsel/zeigen.php?id=0005BN
- **E11** — "Cross+A :: Puzzles", Ilya Morozov; no date shown.
  https://www.cross-plus-a.com/puzzles.htm
- Repository commits in § 4.1 were read from each repository's
  `commits/HEAD` on 10 October 2026; Icelom is the Penpa note's P8
  (`ProximaCentauri0/Icelom`, commit
  `642597865a05e051e81cfc91aa76fae2459bea85`).
