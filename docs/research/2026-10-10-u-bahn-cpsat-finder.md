# U-Bahn: rules, prior art and a CP-SAT model for a grid finder

**Date:** 2026-10-10
**Question.** Chris wants a U-Bahn grid finder in CP-SAT, in the style of the
finders under `finders/`. What are the exact rules, what does this repo
already hold, what must a new finder match, and how should the network and its
connectivity be modelled?

**Method.** Reading only: no solver, hunt or timing was run, so every cost
statement below is a prediction, not a measurement. Each claim is tagged
`[source]` (I read the code, the rules page or the docstring), `[repo]` (read
in this tree, `file:line`), or `[inference]` (my own reasoning, unchecked by
any run). Everything under "recommendation" is mine and is a
flag-if-you-disagree proposal, not a settled decision. Source numbers `[S1]`…
refer to the list at the end.

## 1. The rules

### 1.1 The canonical text

The Logic Masters Deutschland Puzzlewiki states the rule in four sentences
`[source: S1]`:

> Zeichnen Sie in das Rätsel einen zusammenhängenden U-Bahn-Linienplan ein, der
> waagerecht und senkrecht von Feldmittelpunkt zu Feldmittelpunkt verläuft und
> das Diagramm nirgends verlässt. An den Feldmittelpunkten können die Linien
> verzweigen oder abbiegen, es gibt aber keine Sackgassen. Die Zahlen am Rand
> geben an, wie viele der entsprechenden Linienführungen in der entsprechenden
> Zeile oder Spalte vorkommen. Die Linienführungen dürfen dabei auch gedreht
> werden.

The English wording most current puzzles carry `[source: S3]`:

> Draw a totally connected loop network through the centers of some cells,
> which may branch or turn, but may not have any dead ends. A clue outside the
> grid indicates how many times the corresponding line shape (i.e. a cross,
> branch, straight line, or turn) appears in the corresponding row or column,
> irrespective of the line shape's rotation.

The one machine-checkable statement of the rule I found is the pzprjs answer
checker (`src/variety/ubahn.js`, `AnsCheck.checklist`) `[source: S5]`. It
checks, in order: some line exists; per row and column the count of curves,
straights, junctions (`lcnt === 3`) and crossings (`lcnt === 4`) equals each
clue that is given; no cell has exactly one line end; the line graph has one
component.

### 1.2 The rule, point by point

| Point | Answer | Basis |
| --- | --- | --- |
| Cell contents | One of five piece types: empty, corner (turn), straight, T-junction (branch), crossroads | `[source: S1, S3, S5]` |
| Lines | Run orthogonally between the centres of adjacent cells, never off the board | `[source: S1]` |
| Dead ends | Forbidden: no cell with exactly one line end | `[source: S1, S5 checkDeadendLine]` |
| Empty cells | Allowed: "through the centers of *some* cells" | `[source: S3]`; S1 says it only implicitly. The LMD beginner guide names the *Leerfeld* as a fifth piece `[source: S2]` |
| Connectivity | One connected network | `[source: S1 "zusammenhängenden", S5 checkOneLoop]` |
| Crossroads | A real 4-way junction, not a bridge: the checker counts it as a degree-4 cell in one line graph | `[source: S5]`; "not a bridge" is my reading of the checker, which defines no crossing exemption `[inference]` |
| Clues | Four numbers per row and four per column, one per non-empty piece type, counting cells of that type in any rotation | `[source: S1, S5]` |
| Empty count | Not clued. With all four numbers given it is the line length minus their sum | `[source: S2, tip 2]` |
| Are all clues always given? | pzprjs lets any clue be blank and then skips it. The LMD rule text does not say. The beginner guide's tip 2 assumes all four are present | `[source: S5, S1, S2]` |
| At least one line | pzprjs rejects the all-empty board (`checkLineExist`) | `[source: S5]` |

So the degree of a cell is 0, 2, 3 or 4, and of the 16 on/off patterns of a
cell's four half-edges, 12 are legal: 1 empty, 2 straights, 4 corners, 4 Ts,
1 cross; the 4 excluded are the dead ends `[inference from the rule; the
16-pattern count is also how the LMD applet author describes a cell, S9]`.

### 1.3 Where sources disagree, or are silent

- **"Loop network" versus "network".** S3 says "loop network", S1 and pzprjs's
  rules text (S6: "Draw horizontal and vertical lines to form a single
  network") say network. No extra rule hides in the word "loop": with no dead
  ends every used cell already lies on or between cycles. `[inference]`
- **Clue completeness.** See the table: only pzprjs is explicit, and it makes
  clues optional. Whether a finder may strip clues is therefore a ruling for
  Chris (§6), not something a source settles.
- **Clue order.** pzprjs puts the four clue lines above and to the left of the
  grid, nearest the grid first: curve, straight, junction, cross
  (`countFunctionGeneric(-1 / -3 / -5 / -7, …)`) `[source: S5]`. The LMD
  images were not read, so their order is unverified.
- **Grid size.** pzprjs's default board is 6x6 (`Board.cols/rows`) and its
  test fixtures are 4x4 `[source: S5, S7]`. One LMD puzzle is confirmed 6x6 by
  its setter's own comment `[source: S4]`. I did not open enough puzzles to
  state a standard size or a range.

### 1.4 Variants seen

All `[source]`, each read on the cited page:

- **Holes** — the rule text says the network runs through "unshaded cells"
  (S8; I read the text, not the grid image, so "some cells are blocked" is my
  reading). pzprjs has blocked cells as its `empty` edit mode (`ques = 7`,
  `noLP`) `[source: S5]`.
- **One empty cell per row and column** (S10).
- **Summation U-Bahn** — pieces are valued corner 1, straight 2, branch 3,
  cross 4, and the clues are Japanese-Sums-style run totals (S11).
- **Haltestellen** — numbered stations joined in order by a shortest path on
  the network (S12).
- **Hybrids** — Roundabouts (2x2 value sums, S13), Yin-Yang (S14), an embedded
  Latin square of piece types (S15), and one sudoku hybrid already in this
  repo's LMD scan (`docs/research/2026-09-14-lmd-hybrid-scan.md:317`).

### 1.5 Provenance

The task brief called U-Bahn "Nikoli-family". I found nothing supporting that.
The Puzzlewiki page carries the category tags Deutschland-2007,
Qualifikation-Deutschland-2012, Deutschland-2014, Deutschland-2016 and
Qualifikation-Deutschland-2017 `[source: S1]`, and a setter calls it "an old
genre which has often appeared in German competitions" `[source: S16]`.
**Inventor and first appearance: not found.** The wiki page has no history
section; I did not open any championship instruction booklet.

## 2. What exists in this repo

- **No U-Bahn example, component, board, finder, glossary term or ADR.**
  `rg -uu -i 'u-?bahn|ubahn|metro'` over the worktree (excluding `.git`,
  `node_modules`, `.venv`) returns one line: the LMD scan entry cited in §1.4.
- **No issue.** `gh issue list --state all --search 'bahn'`, `'metro'` and
  `'ubahn OR "U-Bahn" OR subway'` each returned nothing (matched against
  GitHub's default issue search fields, on 2026-10-10).
- **Not in the genre survey.** `docs/research/2026-09-14-puzzle-genre-survey.md`
  has no `bahn` hit; its loop section treats single loops only and recommends
  `AddCircuit` with self-loops for them (lines 2210-2319), which does not
  carry over to a branching network (§4.3).

**What a finder would have to emit to feed an example: nothing exists to
feed.** An example under `examples/` needs an `example.toml`, a `*Component.js`,
`main.js`, `build_link.py` and its test, a soundness harness and a link file
(`docs/example-layout.md:8-31`), and a non-sudoku board argues
`rules_prefix = "none"` and `houses = false` (`docs/example-layout.md:56-58`;
`examples/fillomino/example.toml` is the model). None of that exists for
U-Bahn, and I did not check whether SudokuMaker can hold a drawn network as a
solver decision at all: its cells hold digits. So the finder's output format is
an open question (§6), and the only ready-made external format I read is
pzprjs's (`Encode.decodePzpr`: `decodeNumber16ExCell` plus `decodeEmpty`,
and the `pzprv3/ubahn/…` file form in S7) `[source: S5, S7]`.

## 3. Finder conventions to match

All `[repo]`.

**Where things live.** Finder `.py` code under `finders/`; notes, hunt
outputs, catalogues and overnight `.sh` drivers under `docs/research/`
(`finders/AGENTS.md:3-6`). A new finder starts from `finders/hunt/`
(`finders/AGENTS.md:27-33`).

**The hunt protocol.** A finder is a class with `propose(rng)`,
`verify(candidate) -> Verdict`, `record(candidate) -> dict`,
`key(candidate)`, and optional `symmetry`, `config`, `save_state`/`load_state`,
`candidate_from_record`, `render` (`finders/hunt/protocol.py:35-121`). It ends
in `sys.exit(run(Finder(), sys.argv[1:]))`
(`finders/hunt/toy_finder.py:43-44`). `finders/qqrr/hunt/tie_finder.py` is the
one real finder on it: one CP-SAT solve per seed, `Empty("timeout")` versus
`Empty("infeasible …")` kept apart (lines 163-169), its own flags parsed with
`parse_known_args` and the rest handed to the driver (lines 242-274).

**The driver** (`finders/hunt/driver.py`) owns `--out`, `--seeds START:END`,
`--workers` (default `DEFAULT_WORKERS = 3`, `protocol.py:15`, set on the
finder as `self.workers`), `--force-load`, `--no-verify` (lines 161-168), and
the `verify DIR` subcommand. It refuses to start above a 1-minute load of 24
(`LOAD_LIMIT`, lines 85, 107-123). It writes `examples.jsonl`,
`progress.jsonl`, `summary.json`, `run.json`, `state.json` (lines 66-70),
resumes after a kill, and dedupes under `finder.symmetry`
(`finders/hunt/dedupe.py`, `D4` by default).

**Uniqueness is proved by a second solve with a blocking clause, never by
solution enumeration.**
- `finders/hunt/uniqueness.py:68-101` `check_uniqueness(model, variables, *,
  time_limit, workers)`: solve, clone, forbid the first assignment on the
  named variables, re-solve; returns one of `unique`, `not_unique`,
  `infeasible`, `timeout`, `invalid`.
- `examples/_shared/cpsat.py:60-91` `forbid` / `has_second_solution`, and
  `solve_unique` (lines 127-142); a timeout raises `TimeoutError`.
- A committed proof runs one worker, seed 0 (`cpsat.py:40-57`); a search for a
  fresh grid runs the portfolio with the caller's seed.
- `enumerate_all_solutions` gave a **wrong** count on fillomino because flow
  and region-id variables produce a second "solution" with the same grid
  (`docs/research/ortools-tuning.md:35-38`). U-Bahn's connectivity variables
  have the same hazard: forbid on the network variables only.

**Clue minimisation.** `finders/hunt/minimizer.py:10-27` `strip(items, keep,
test)`: greedy batch removal, halve on failure. A timeout must keep the clue
(`docs/agents/grid-finder-lessons.md:107-110`). When the full solution is
known, ask for a solution that *differs* instead of solve-then-forbid: one
solve per trial (`docs/research/ortools-tuning.md:39-43`).

**Generation shape.** Solution first, clues derived from it, then strip
(`docs/testing-and-generation.md:57-64`); `examples/fillomino/generate.py`
is the closest end-to-end example for a non-sudoku grid: `model` (76-112),
`sample` with random pins for diversity (140-173), `solutions`/`unique`
(176-207), `brute` (210-250) and `self_check` (257-280).

**Model checks the repo expects.**
- A geometric encoding is checked against a direct implementation: brute force
  on tiny boards (`generate.py:257-263`), flood fill on random shapes
  (`grid-finder-lessons.md:111-114`).
- A catalogue is verified by code that shares nothing with the finder
  (`grid-finder-lessons.md:130-132`); `verify` in the hunt protocol is that
  seat (`tie_finder.py:177-198` re-reads the grid with an oracle, never the
  model).
- A bound that will steer later search gets a second, unrelated encoding
  (`grid-finder-lessons.md:102-106`).
- `UNKNOWN` is never a verdict (`CODING_STANDARDS.md:84`).

**Before any hunt.** Answer the seven-question preflight in writing and keep a
decision log (`finders/AGENTS.md:40-48`, `grid-finder-lessons.md:8-52`). One
hunt at a time, `uptime` first, long runs under `job-run`, speedups listed in
the launch message (`AGENTS.md:41-68`).

**Tests.** Standalone scripts named `test_*.py` beside the code, run by glob
from `just test` with no justfile edit (`justfile:25-36`, `86-98`);
`finders/counting_shaded` is the one pytest suite. A test asserts an outcome
and must go red on the planted bug (`CODING_STANDARDS.md:72-80`). Lint is
`uvx ruff check finders` and `ruff format`.

**OR-Tools.** `ortools 9.15.6755` (`uv.lock:236-237`; unpinned in
`pyproject.toml:8`). Both `snake_case` and `PascalCase` method names exist on
a `CpModel` instance in this build `[source: checked with hasattr in the
project environment]`; the repo uses both (`joint.py` snake, `cpsat.py`
Pascal).

## 4. Modelling U-Bahn in CP-SAT

Everything in this section is `[inference]` unless tagged otherwise. None of
it was run.

### 4.1 Variables

For an `R x C` board:

| Variable | Count | Meaning |
| --- | --- | --- |
| `h[r,c]` bool | `R*(C-1)` | the edge between `(r,c)` and `(r,c+1)` carries a line |
| `v[r,c]` bool | `(R-1)*C` | the edge between `(r,c)` and `(r+1,c)` carries a line |
| `kind[p,t]` bool, `t` in corner/straight/T/cross | `4*R*C` | cell `p` holds piece type `t` |
| `used[p]` bool | `R*C` | cell `p` is not empty |

**Recommendation: edge booleans are the decision variables, piece types are
channelled from them.** The alternative, one 12-valued piece enum per cell
with compatibility constraints between neighbours, states the same thing with
more variables and a weaker link to connectivity, which lives on edges. Edge
variables also make "does not leave the diagram" free: an edge off the board
has no variable. A 9x9 has 144 edge booleans; the uniqueness clause forbids
on exactly those.

### 4.2 Degree and piece-type channelling, and the clues

- **No dead end:** for each cell, each incident edge implies the OR of the
  other incident edges (up to 4 clauses per cell).
- **Types:** one `add_allowed_assignments` per cell over its incident edges
  plus the four `kind` booleans, listing the 12 legal rows (fewer on the
  border). `[source: S17 for the constraint's contract]` The reified
  alternative is `deg == sum(edges)` with `kind` reified on `deg` and on
  "the two edges are opposite"; the table is one constraint and cannot
  half-channel.
- **Clues:** `sum(kind[p,t] for p in line) == clue` for each given clue. All
  clue constraints are linear over booleans.
- **Not empty:** at least one edge is on (pzprjs's `checkLineExist`).

### 4.3 Connectivity — the options

| Option | Extra variables (9x9) | Used in this repo | Notes |
| --- | --- | --- | --- |
| **Single-commodity flow** | 2 ints per edge (288), a root bool and a supply int per cell | Yes, three times: `examples/isofill/verify.py:85-93`, `examples/fillomino/generate.py:100-111`, `finders/counting_shaded/joint.py:51-75` | Root supplies, every used cell absorbs one unit, flow crosses only edges that are on |
| **Rooted spanning tree with level labels** | a parent bool per directed edge, a level int and a root bool per cell | Yes: `finders/counting_shaded/recheck_ceiling.py:31-47`, written as the independent re-proof of a flow result | Many trees per network; fine under forbid-on-edges, more search in a proof |
| **Exact BFS distance from the lowest cell** | a distance int per cell, reified steps | Yes: `finders/counting_shaded/gridenum.py:86-109` | Every helper is a function of the main variables, so it is safe under enumeration; heaviest to propagate |
| **`add_circuit` / `add_multiple_circuit`** | — | No Python call anywhere under `examples/` or `finders/` (`rg -i 'circuit' --type py`); the genre survey only proposes it for single loops | See below |
| **Lazy cuts on disconnected components** | none | Tried and rejected twice | See below |

**Circuit constraints do not fit directly.** `add_circuit` demands "a unique
Hamiltonian cycle in a subgraph", each node having one successor, with
self-loops for skipped nodes; `add_multiple_circuit` demands in-degree and
out-degree 1 at every node but node 0 `[source: S17, S18]`. A U-Bahn network
has cells of degree 3 and 4, so it is not a circuit over cells. A circuit can
still certify connectivity indirectly — as an Euler tour of a doubled spanning
tree over half-edge nodes — but that is my construction, I found no source
describing it for CP-SAT, and it adds a tree choice on top of the circuit.
Not recommended as a first model.

**Lazy cuts.** The repo's record: "2073 cuts in 120s with no connected shape,
against 77s for single-commodity flow" (`grid-finder-lessons.md:115-118`), and
fillomino rejected them because one solve becomes an unbounded loop of solves
(`docs/research/fillomino-cpsat.md:126-131`). One caveat in U-Bahn's favour:
those cuts were no-goods on a component layout, whereas here a cut can be the
general one — for a component `K`, "if a cell of `K` and a cell outside `K`
are both used, some edge leaving `K` is on" — which kills a family, the
condition `grid-finder-lessons.md:61-67` names for cuts to pay. That is an
argument for a measured comparison later, not for starting there.

### 4.4 Recommendation (mine, flag if you disagree)

**Single-commodity flow, with the root pinned to the lowest-indexed used
cell.**

- It is the device the repo has run and debugged in three models, and the
  lesson file says to prefer an encoding to cuts.
- `root[p]` = `used[p]` and no earlier cell is used (the prefix device in
  `gridenum.py:89-96`), so the root is a function of the network and there is
  no root-choice symmetry. `joint.py:59-60` uses a free `exactly_one` root
  instead; either is sound, the canonical one removes a symmetry.
- Directed arc flows `f[p->q]` in `0..N-1` with `f <= (N-1) * edge`, supply
  at the root only, and `inflow + supply == outflow + used[p]` per cell — the
  equation in `joint.py:72-75` with `g` replaced by `used` and the capacity
  gated by the edge rather than by both endpoints.
- Size the flow domain to the real maximum, not the cell count
  (`grid-finder-lessons.md:117-118`): with all clues given, the used-cell
  count is the sum of the clues over rows, a constant.
- Flows on a network with cycles are not unique, so the model has many
  internal solutions per network. That is harmless for solve-forbid-solve on
  the edge variables and is the reason to stay away from
  `enumerate_all_solutions`.

Then, as the repo's own lessons require: check it against a flood fill on
random small boards and against a brute-force enumeration of every legal
network on 2x2 to 4x4 (the `generate.py:257-263` pattern), and keep the
level-labelled tree as the second encoding for any bound that gets quoted.
The pzprjs fixtures in S7 give one 4x4 puzzle with its accepted answer and one
failing board per rule; they would make ready cross-checks, but I did not
decode them.

### 4.5 Redundant constraints and symmetry

All derived here, none tested; each is a necessary condition, so it is sound
to add, and whether it pays is a measurement.

- **Clue-set consistency, checked before any solve.** For each piece type the
  row clues and the column clues sum to the same total. The handshake identity
  `2*(corners + straights) + 3*T + 4*cross = 2*edges` makes the total number
  of T pieces even. Both are free rejects of a bad clue set
  (`grid-finder-lessons.md:48-52`).
- **Per-line parity.** In one row, the horizontal line ends sum to twice the
  row's horizontal edges, so (corners + Ts with one horizontal arm) is even;
  likewise for columns. CP-SAT's linear relaxation already holds the equality
  through the edge variables; the parity itself it does not see.
- **Row-boundary counts.** The number of vertical edges between rows `r` and
  `r+1` is an integer the clues bound from both sides (each corner contributes
  one vertical end, each cross two, a straight zero or two, a T one or two).
  This is the quantity LMD solution codes ask for `[source: S3]`.
- **Border facts** come free from missing edge variables: a corner cell is
  empty or a corner piece, an edge cell is never a cross.
- **A used network has at least 4 cells** (the 2x2 ring), and by Euler's
  formula its bounded faces number `T/2 + cross + 1`. Not obviously useful to
  the solver; useful to a `verify` oracle.
- **Symmetry.** The model has no value symmetry once the root is canonical.
  Across puzzles, the board's rotations and reflections map solutions to
  solutions with the clue lines permuted, so hunt output dedupes under `D4`
  (square boards). `dedupe.D4` permutes cells without rotating a cell's value,
  so the key must be rotation-invariant: the grid of piece *types* works, and
  loses nothing for unique puzzles, because the full clue set is a function of
  the type grid — two networks with one type grid share every clue and
  neither is unique.

### 4.6 The generation loop this implies

1. **Sample a network**: the model with no clues, random seed, portfolio
   (`cpsat.solver(limit, reproducible=False, seed=…, randomize=True)`).
   Expect the dull-sample problem fillomino hit (`fillomino-cpsat.md`
   "Sampling diversity"): an unconstrained solve will likely return a minimal
   ring. Density and piece-mix targets, or random pinned cells as in
   `generate.py:140-173`, are needed. The network is "the smallest object that
   determines the puzzle" (`grid-finder-lessons.md:56-60`): every clue derives
   from it.
2. **Derive all `4*(R+C)` clues** from the network.
3. **Uniqueness**: ask for a network that satisfies the clues and differs from
   the sampled one on some edge. `INFEASIBLE` is unique; `UNKNOWN` is no
   verdict.
4. **Strip clues** (if Chris allows blanks, §6) with `minimizer.strip`.
5. **Verify** with an oracle that shares nothing with the model: flood fill,
   degree check, recount.

Whether a random network with its full clue set is usually unique is unknown
to me; nothing I read says, and it is a one-solve-per-sample measurement.

## 5. Prior art outside the repo

- **pzprjs (robx fork)** has a `ubahn` variety: editor, URL and file codec,
  and the answer checker quoted in §1. Added in one commit, "Add U-Bahn",
  Lennard Sprong, 2026-05-25 `[source: S5]`. It is a checker, not a solver.
  Whether puzz.link's deployed site serves it I did not check.
- **No solver or generator found.** Covered: a file-path match on
  `bahn|subway|metro` over the full (untruncated) git trees of
  `semiexp/cspuz_core` (180 puzzle `.rs` files), `semiexp/cspuz`,
  `T0nyX1ang/noqx` (189 solver `.py` files), `kevinychen/nikoli-puzzle-solver`
  (138 solver paths), `mstang107/noq` (73 solver files) and the `examples/`
  directory of `obijywk/grilops` (39 files, all read by name); GitHub code
  search for `bahn` scoped to each of those plus `semiexp/cspuz-solver2` and
  `sigh/Interactive-Sudoku-Solver` (no hits; GitHub code search is not
  guaranteed exhaustive); `gh search repos` for "ubahn puzzle" and "u-bahn
  puzzle solver" (no hits); and the game list on Simon Tatham's puzzle
  collection page, 40 games, none U-Bahn (its `net` and `tracks` are different
  rules) `[source: S19]`. **Not covered:** file contents under another name, a
  global GitHub code search (rate-limited before it ran), Penpa+'s source,
  private or unindexed code. So this is "none found in those places", not
  "none exists".
- **Human technique** is documented: the LMD beginner guide (start from full
  border lines, treat the empty count as a fifth clue, place the rare piece
  first) `[source: S2]`. Useful later if a human-solvability filter is wanted.

## 6. Open questions Chris must rule on

1. **Pure U-Bahn, or a U-Bahn layer over a sudoku?** The brief says "grid
   finder … in the same style as the existing sudoku finders". The model in §4
   is the pure puzzle; a hybrid adds the 81 digit variables and a coupling
   rule that does not exist yet.
2. **Where does a found puzzle go?** No SudokuMaker U-Bahn component exists
   and I did not establish that the app can hold a drawn network. Options are
   a `examples.jsonl` record only, a pzprjs/Penpa+ link, or a new example
   (a spec of its own).
   Ruled since: a Penpa+ link with the full clue set — the link format is
   in `docs/research/2026-10-10-u-bahn-penpa-link.md`.
3. **Clue policy.** Always all `4*(R+C)` numbers (the competition form, as far
   as the sources show), or strip to a minimal set (pzprjs permits blanks)?
4. **Board.** Sizes to hunt (6x6 is the only size I confirmed in the wild),
   square only or rectangular, holes or none.
5. **Quality bar.** Unique is checkable; "solvable by a human without trial
   and error" is what the published puzzles are prized for and needs either a
   human solver (as `finders/galaxy-copycat/human_solver.py` is for its rule)
   or Chris's eye. Density and piece-mix targets belong here too.
6. **Connectivity encoding.** Flow first, as recommended in §4.4, or a
   measured flow-versus-cuts comparison before committing?
7. **Naming.** `GLOSSARY.md` already defines **line** and **path** with other
   meanings (lines 50-75), and `CODING_STANDARDS.md:106` forbids synonyms.
   The finder needs its own words (network, edge, piece) entered in the
   glossary.
8. **Home.** `finders/ubahn/` on the hunt protocol is my assumption from
   `finders/AGENTS.md:27`; no new dependency is needed.

## 7. Not verified

- The inventor and first publication of U-Bahn.
- The janko.at rules page: the URL I tried
  (`https://www.janko.at/Raetsel/U-Bahn/index.htm`) returned the site's
  not-found page, so I do not know whether janko.at carries the genre.
- The clue order and layout in LMD's own images.
- A standard grid size, or the size range of published puzzles.
- wooferzfg's linked logic guide (a shortened link I did not follow).
- Any runtime, any uniqueness rate, any claim that a redundant constraint
  helps.
- Whether SudokuMaker can represent the puzzle.

## Sources

Repo files are cited inline as `path:line`. Outside sources:

- **S1** — "U-Bahn/de", Puzzlewiki, Logic Masters Deutschland; page last
  edited 21 January 2017. https://wiki.logic-masters.de/index.php?title=U-Bahn
- **S2** — "U-Bahn-Rätsel für Anfänger", Realshaggy, LMD Rätselportal,
  4 September 2009.
  https://logic-masters.de/Raetselportal/Raetsel/zeigen.php?id=00006L
- **S3** — "U-Bahn (1)", KNT, LMD Rätselportal, 15 April 2023.
  https://logic-masters.de/Raetselportal/Raetsel/zeigen.php?chlang=en&id=000DKS
- **S4** — "U-Bahn 3", Dandelo, LMD Rätselportal, 31 January 2021 (rule text
  identical to S1; the setter's comment of 22 September 2024 gives the 6x6
  size). https://logic-masters.de/Raetselportal/Raetsel/zeigen.php?id=0005BN
- **S5** — `src/variety/ubahn.js`, robx/pzprjs, branch `main`, commit
  `19cc9d83bb` "Add U-Bahn", Lennard Sprong, 2026-05-25.
  https://github.com/robx/pzprjs/blob/main/src/variety/ubahn.js — with
  `checkOneLoop`, `checkDeadendLine`, `checkLineExist` read in
  https://github.com/robx/pzprjs/blob/main/src/variety-common/Answer.js and
  `isLineStraight` / `isLineCurve` in
  https://github.com/robx/pzprjs/blob/main/src/puzzle/Piece.js
- **S6** — `src-ui/res/rules.en.yaml`, key `ubahn`, robx/pzprjs `main`.
  https://github.com/robx/pzprjs/blob/main/src-ui/res/rules.en.yaml
- **S7** — `test/script/ubahn.js`, robx/pzprjs `main`.
  https://github.com/robx/pzprjs/blob/main/test/script/ubahn.js
- **S8** — "U-Bahn", wooferzfg, undated.
  https://www.wooferzfg.me/puzzles/ubahn.html
- **S9** — "U-Bahn Lösetechnik", Logic Masters Forum thread started by
  Calavera, 14 April 2009 (the applet author's "alle 16 Möglichkeiten").
  https://forum.logic-masters.de/archive/index.php?thread-376.html=
- **S10** — "U-Bahn with Empty Cells", LMD Rätselportal, 28 June 2024 (setter
  name not captured).
  https://logic-masters.de/Raetselportal/Raetsel/zeigen.php?id=000IPE
- **S11** — "Classic Summation U-bahn", Playmaker6174, LMD Rätselportal,
  6 November 2025.
  https://logic-masters.de/Raetselportal/Raetsel/zeigen.php?id=000PZY
- **S12** — "U-Bahn mit Haltestellen", tuace, LMD Rätselportal, 28 March 2016.
  https://logic-masters.de/Raetselportal/Raetsel/zeigen.php?id=0002EA
- **S13** — "Subway Roundabout", LMD Rätselportal, 21 August 2024 (setter name
  not captured).
  https://logic-masters.de/Raetselportal/Raetsel/zeigen.php?id=000JGX
- **S14** — "Yin Yang U-Bahn [Secret Satan #1]", LMD Rätselportal (setter and
  date not captured).
  https://logic-masters.de/Raetselportal/Raetsel/zeigen.php?id=000LEZ
- **S15** — "U-Bahn (Embedded Latin Square)", Menderbug, Broken Sign Games,
  25 April 2025.
  https://brokensign.com/puzzle/2025/04/25/u-bahn-latin-square.html
- **S16** — "Puzzle #154 - U-Bahn", feadoor, 23 January 2025.
  https://feadoor.blogspot.com/2025/01/puzzle-154-u-bahn.html
- **S17** — Docstrings of `CpModel.add_circuit`, `add_multiple_circuit` and
  `add_allowed_assignments` in the installed `ortools 9.15.6755`
  (`ortools.sat.python.cp_model`), read with `inspect.getdoc` in the project
  environment.
- **S18** — "ortools.sat.python.cp_model", OR-Tools API reference (pdoc), no
  version shown on the page; the `add_circuit` and `add_multiple_circuit`
  text matches S17.
  https://or-tools.github.io/docs/pdoc/ortools/sat/python/cp_model.html
- **S19** — "Simon Tatham's Portable Puzzle Collection", Simon Tatham (game
  list read from the page's links).
  https://www.chiark.greenend.org.uk/~sgtatham/puzzles/
