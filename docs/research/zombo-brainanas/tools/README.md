# Zombo Brainanas hunt tooling

Working copies run from the git-ignored `scratch-zombo/` dir at the worktree
root (`hunt/` holds arm/sync scripts, `tpl/` holds shading templates). This
directory holds the sync/logging drivers; results sync into `../found/`.

- `arm.sh outdir first last [extra]` — one process per seed, 9 GB ulimit, stops on `hunt/STOP`
- `sync.sh` / `sync_loop.sh` — dedupe hits, render PNGs, commit + push every 30 min
- `memlog.sh` — RSS log per solver process

The one-off shading/pair/triple/pocket hunt scripts that once lived in
`finders/zombo-brainanas/tools/` (not `arm.sh`'s or `memlog.sh`'s own
target, `zb_bal.py`, which lives in the git-ignored `scratch-zombo/` and was
untouched) were deleted in #471: each hardcoded an absolute path into a
sibling `tang` checkout that no longer exists, so most could not run at all.
Their results are recorded in `BRAINANAS.md`, `DOTS.md`, `FORCED.md`,
`PAIRS.md`, `SWAP.md` and `UPPER_LEFT.md` in the directory above; the
scripts themselves are on file at
`git show 59335b1:finders/zombo-brainanas/tools/<name>.py`.
