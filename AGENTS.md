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

## Finder rules

`finders/AGENTS.md` holds the rules and the guide to each finder: the
renbanana catalogue rule, the hunt protocol to start a new finder from, and
the U-Bahn finder's engines and flags. Read it before touching `finders/`.

## End-to-end seam

- **Seam**: `just check`
- **Blind to**: the slow renbanana tests (`just test-slow`), a hunt's own
  output, and how a found grid reads once it is built into a puzzle link

## Commands

- **Gate — run before each commit and before opening a PR:** `just check` —
  ruff on `finders/`, `uv lock --check`, and every `finders/**/test_*.py`
  except the slow ones. CI runs it on every pull request and on pushes to
  main, installing only uv.
- Lint + auto-fix: `just fmt`
- Tests alone: `just test` — slow tests, by hand: `just test-slow`
- Most tests are standalone scripts run by name (`uv run <file>`).
  `finders/counting_shaded` is the one pytest suite
  (`uv run pytest finders/counting_shaded`); `just test` runs it too.
- Python runs in the one project environment (`pyproject.toml`, `uv.lock`):
  `uv run <file>`. `sudoku-kit` (the CP-SAT helpers, the SudokuMaker link
  codec and the five-status uniqueness check) is pinned there by tag; nothing
  reads a sibling checkout under `~/src`.

## Pointers

- Finder rules and the guide to each finder → `finders/AGENTS.md`
- Coding + testing standards → `CODING_STANDARDS.md`
- Before writing the next finder → `docs/agents/grid-finder-lessons.md`
- Terms → `GLOSSARY.md`
- Notes, hunt outputs and precomputed catalogues → `docs/research/`

## Agent skills

### Issue tracker

Issues live in this repo's GitHub Issues, via the `gh` CLI. See `docs/agents/issue-tracker.md`.

### Triage labels

Default six canonical triage roles, each label string equal to its name. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: one `GLOSSARY.md` at the repo root. See `docs/agents/domain.md`.
