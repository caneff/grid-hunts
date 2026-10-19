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
hunt protocol to start a new finder from, and the U-Bahn finder's engines and
flags. Read it before touching `finders/`.

Retiring a finder is `git mv` to `archive/finders/` plus its README; reviving one is a ticket that moves it back and makes its suites pass.

## End-to-end seam

- **Seam**: `just check`
- **Narrowed**: `bash tests/all.sh --changed origin/main` — lint, the runner's test, and the suites under each `finders/<name>/` folder the diff touches (plus the finder a changed data or code directory feeds: `finders/halver/`, the shared halver layer, feeds `halver_between`); shared code, a `docs/` file that is not `.md` and not mapped, or any path nothing names widens the run to every non-slow suite, and the last line ends `(widened: <path>)`; a diff of unmapped `.md` files runs lint and the runner's test; the rules and the data map are in the header of `tests/all.sh`
- **Blind to**: the slow halver/between hunt test (`just test-slow`), a
  hunt's own output, and how a found grid reads once it is built into a
  puzzle link

## Commands

- **Gate — run before each commit and before opening a PR:** `just check` —
  ruff on `finders/` and `tests/`, `uv lock --check`, every
  `finders/**/test_*.py` except the slow ones, and `tests/test_all_sh.py`
  (the runner's own test). It is the full seam: CI runs it nightly, on a cron
  line in `.github/workflows/ci.yml`, installing only uv. A pull request and a
  push to main run the narrowed gate, `bash tests/all.sh --changed
  origin/main` (a push uses the pushed range's base; a new branch or a
  force-push runs `just check` and says it widened). `--list --changed
  <base>` prints the selection; `tests/all.sh`'s header states the rules.
- Suites run one at a time. `GATE_JOBS=<n>` (or `bash tests/all.sh --jobs <n>`)
  runs n at once; CI sets 4 on its 4-vCPU runner, and a local run leaves it
  unset because the box is shared.
- CI gate wall clock, the `Gate (check)` step: **before** 15 min 15 s, one
  suite at a time (run 38341110336, push to main, 2026-10-13). **After:**
  6 min 22 s, 4 suites at once (run 38724587608, pull request, 2026-10-15,
  the same 64 test suites plus the runner's own test). Those are full-seam
  times; a narrowed run costs the selected suites only.
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
