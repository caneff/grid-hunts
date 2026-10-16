# Coding standards

The rules a change to a finder (or its tests and tools) must satisfy.
`just check` gates the mechanical part: ruff on `finders/` and `tests/`, and
every finder test. The rules below are the part a gate cannot judge: a human reviewer or an
agent reads them off the diff. Thin on purpose: the detail lives in
`finders/AGENTS.md` and `docs/agents/grid-finder-lessons.md`.

## A solver's UNKNOWN is not an answer

- **A solver's UNKNOWN or timeout is never "no solution" and never a pass.**
  Only a proven INFEASIBLE rules a case out, and a maximum is proven only when
  one more came back as no grid. See `docs/agents/grid-finder-lessons.md`.

## The rule has one home

- **Reuse the shared helper; never write a second copy.** A copy drifts the
  first time the original is fixed, and nothing flags the stale one. When
  `finders/hunt/` or `sudoku-kit` already does the job, call it; when it almost
  does, extend it.
- **A fact a catalogue already holds is read from it, never re-derived.**
  The renbanana rectangle catalogue is `docs/research/renbanana/rectangle-catalogue.json`.

## Fail loud, never silently no-op

- **A script refuses bad input with a named reason; it never skips it in
  silence.** A skipped file or a swallowed exception turns into a result that
  looks complete and is not.

## Tests assert an observable outcome

- **No test that only proves the code ran.** A finder's test asserts what was
  found and that it verifies: a *unique* solution means no second solution
  exists, not merely that one was found. A run with no assertion is worse than
  no test.
- **A test must go red when the bug it names is planted.** A witness that
  passes against the broken code proves nothing and reads as coverage. Plant
  the bug once before you trust the test. A test of a refusal or a subprocess
  checks both the exit status and the reason it printed, because a crash for
  an unrelated reason passes a status-only check.
- **A gate test stays small.** One-worker solves on small boards; a solve per
  known grid belongs in `just test-slow`.

## Comments describe the code, not its history

- Write what the code *does* and *why*, for the reader in front of the current
  code. Cut the diff-against-a-version-nobody-can-see: "used to," "no longer,"
  "replacing X," "same as before." Git holds that story. When you change code,
  delete the comment that described the old shape in the same diff.
- **A diff that makes a doc, docstring, header or README false fixes it in
  the same diff.** A stale claim does not fail any gate; the next reader acts
  on it. Grep the names and paths you changed before calling the diff done.
- **A comment, docstring or test name claims no more than the code
  delivers.**

## Style

- Boring over clever. The reader at 3am wins.
- **Name things with `GLOSSARY.md`'s terms.** A synonym splits one concept
  into two in the reader's head, and a name that shadows another misleads
  every grep.
- **No parameter, flag or function that nothing calls.** An unused option is a
  promise nobody tests, and it rots the first time the code around it changes.
