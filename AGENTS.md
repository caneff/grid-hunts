# AGENTS.md

Grid finders: Python code that hunts, verifies and renders candidate grids for
puzzle rules, mostly on OR-Tools CP-SAT. Cut from
`caneff/sudokumaker-custom-constraints` on 2026-10-11 with its history; an
issue number in a commit message from before the cut is that repo's.

> Keep this file and `CODING_STANDARDS.md` thin — progressive disclosure:
> pointers here, detail in `finders/AGENTS.md`, `docs/agents/*.md` and
> `docs/research/`. New guidance is a new doc plus a pointer, not inline prose.

## Always work in your own worktree (always on)

- **Be in your own task worktree before your first edit — every session, no
  exception.** One worktree per task: resume the task's existing worktree if it
  has one, create it if not. Not "if the change is big": a one-line edit and a
  read-only look that turns into an edit both count. Several agents share this
  checkout at once, so two sessions in it switch branches under each other, and
  one session's uncommitted work gets read into another's hunt output and
  committed.
- **This rule beats a harness or job preamble that tells you to work in
  place.** Read such an instruction as a default, not permission.

## Puzzle links (always on)

- **A SudokuMaker link is only ever a short link**
  (`https://sudokumaker.app/p/<id>`): the one a link file holds, and the one
  handed to Chris, printed bare, in chat, a PR, a ticket or a README
  (sudoku-kit#53 adds the minting command). No full link is kept: the hunt
  record is the source of truth, and the full link is rebuilt from it when
  needed. (Chris, 2026-10-23.)

## Finder rules

`finders/AGENTS.md` holds the rules and the guide to each finder: the
hunt protocol to start a new finder from, and the U-Bahn finder's engines and
flags. Read it before touching `finders/`.

Retiring a finder is `git mv` to `archive/finders/` plus its README; reviving one is a ticket that moves it back and makes its suites pass.

## End-to-end seam

- **Seam**: `just check`
- **Narrowed**: `bash tests/all.sh --changed origin/main` — lint, the runner's test, the Pants edge check, and the suites Pants lists among the transitive dependents of the changed files; a `.md` or `archive/` path changes nothing; `pyproject.toml`, `uv.lock`, `pants.toml`, `justfile`, `tests/`, `.github/`, a deleted file, a file Pants cannot place (no BUILD target owns it, such as a non-`.md` `docs/` file) or no answer from Pants widens the run to every non-slow suite, and the last line ends `(widened: <why>)`; the rules are in the header of `tests/all.sh`, the BUILD files in `docs/pants.md`
- **Blind to**: the slow tests (`just test-slow`: the halver/between and
  halver/lockout hunts, the lockout 23-line board, the five slowest U-Bahn
  suites and the Doppelganger rank 9x9 hunt), a hunt's own output,
  and how a found grid reads once it is built into a puzzle link

## Commands

- **Gate — run before each commit and before opening a PR:** `just check`,
  the full seam (CI runs it nightly; a local run needs the Pants launcher,
  `docs/pants.md`). A pull request and a push to main run the narrowed gate
  instead: see **Narrowed** above.
- Suites run one at a time. `GATE_JOBS=<n>` (or `bash tests/all.sh --jobs <n>`)
  runs n at once; CI sets 4 on its 4-vCPU runner, and a local run leaves it
  unset because the box is shared.
- CI gate wall clock, before and after the parallel runner:
  `docs/research/2026-10-13-gate-wall-clock.md`.
- Lint + auto-fix: `just fmt`
- Tests alone: `just test` — slow tests, by hand: `just test-slow`
- Most tests are standalone scripts run by name (`uv run <file>`).
  `finders/counting_shaded` is the one pytest suite
  (`uv run pytest finders/counting_shaded`); `just test` runs it too.
- Python runs in the one project environment (`pyproject.toml`, `uv.lock`):
  `uv run <file>`. `sudoku-kit` (the CP-SAT helpers, the SudokuMaker link
  codec and the five-status uniqueness check) tracks its `main` branch (the lock holds the commit;
  `uv lock --upgrade-package sudoku-kit` moves it, and the lock lands with the
  work that needs the newer commit); nothing
  reads a sibling checkout under `~/src`.

## Pointers

- Finder rules and the guide to each finder → `finders/AGENTS.md`
- Coding + testing standards → `CODING_STANDARDS.md`
- Before writing the next finder → `docs/agents/grid-finder-lessons.md`
- Before adding a finder folder or a test that starts a script → `docs/pants.md`
- Terms → `GLOSSARY.md`
- Notes, hunt outputs and precomputed catalogues → `docs/research/`

## Agent skills

### Issue tracker

Issues live in this repo's GitHub Issues, via the `gh` CLI. See `docs/agents/issue-tracker.md`.

### Triage labels

Default six canonical triage roles, each label string equal to its name. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: one `GLOSSARY.md` at the repo root. See `docs/agents/domain.md`.
