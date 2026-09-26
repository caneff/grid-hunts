# qqrr hunt scripts

Drivers for the 7-digit tie hunt and the 34–36 hunt (map #591). Flags, results
and the runs that produced them: `docs/research/2026-09-22-qqrr-tie-r5c1.md`.
`$HUNT_LOGS` (default `.scratch/place`) is where `chan_big.py`, `scheduler4.sh`,
`sync_presets.py` and `check_3436.py` find the `big-*.log` files; `pair_sweep.py`,
`chan_sweep.py` and `measure.py` take their log path as an argument. The
worker, pool and load numbers are the ones the hunts ran with; check `uptime`
and the box rules in `AGENTS.md` before launching, and run one hunt at a time.

- `pair_sweep.py` — one solve per seeing pair, resumable.
  `pair_sweep.py <corner> <procs> <per-pair timeout> <log> [<hunt> [<workers> [retry]]]`
- `chan_sweep.py` — the digit-channelled pair sweep.
  `chan_sweep.py <corner> <procs> <per-task timeout> <log> <hunt> [<workers>] [pairs=r7c2=r7c5,...] [from=<pair_sweep log>]`
- `chan_big.py` — the big channelled finder; flags `warm`, `forbid-known`, `criteria=q34`.
  `chan_big.py <hunt r5c1|r1c5> <ten rXcY> <corner> <workers> <timeout> <log> [count] [flags...]`
- `scheduler4.sh` — 4 pools × 6 workers of `chan_big.py` under a load cap of 22.
  `HUNT_LOGS=<dir> scheduler4.sh`
- `sync_presets.py` — adds hits from `big-*-q34.log` to the explorer's presets.
  `sync_presets.py [<explorer.html>]`
- `check_3436.py` — oracle check of the 34–36 criterion over found grids.
  `check_3436.py`
- `hunt_common.py` — what the scripts share: the hunt table, `$HUNT_LOGS`, the q34
  criterion, the HIT-block log lines and their parser. `import hunt_common` comes
  first in a script and puts `finders/qqrr` and the repo root on `sys.path`.
- `measure.py` — solver-settings timing on timed-out channelled tasks (calls `chan_sweep.configure`).
  `measure.py <log>`
