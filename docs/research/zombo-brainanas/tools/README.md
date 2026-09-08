# Zombo Brainanas hunt tooling

Working copies run from the git-ignored `scratch-zombo/` dir at the worktree
root (`hunt/` holds arm/sync scripts, `tpl/` holds shading templates). This
directory is the durable copy of those scripts; results sync into `../found/`.

- `arm.sh outdir first last [extra]` — one process per seed, 9 GB ulimit, stops on `hunt/STOP`
- `sync.sh` / `sync_loop.sh` — dedupe hits, render PNGs, commit + push every 30 min
- `template.py mk|run` + `tpl/*.txt` — fix an opener's shading, solve for the rest
- `pairs.py shard nshards [round_s] [total_s]` — every box-9 circle pair as open circles
- `b9cover.py` — build-once cover loop over box-9 pairs
- `build_lineup.py` + `lineup_template.html` — the lineup artifact page
- `memlog.sh`, `sanity.py` — RSS log per solver process, quick model check
- `forced.py shard nshards` — per cell, can it be infected / uninfected (FORCED.md)
- `kinds.py shard nshards` — per pair, which shading combos (II/IU/UI/UU) are feasible
- `pairopt.py shard nshards [limit] [stall]` — per pair kind (no r8c8), maximize circles → hunt/pairopt/
- `pairone5.py shard nshards [limit] [stall]` — one open box-9 circle per case (cell × I/U, no r8c8), ≥5 brainanas, maximize circles + chocolate (`ZB_WORKERS` env) → hunt/pairone5/
- `pair99.py shard nshards [limit] [stall]` — r9c7 + r9c9 circles (IU / UI), maximize circles + chocolate → hunt/pair99/
- `pair99free.py` — as `pair99.py` with no avoid set → hunt/pair99free/
- `pair99var.py shard nshards [nseeds] [limit] [stall]` — variety around r9c7 + r9c9: seeds ≥12 shading cells apart, chocolate weight alternating 1/3 and 1/6 circle → hunt/pair99var/
- `pair99g4.py` — as `pair99var.py` with ≥4 uninfected groups → hunt/pair99g4/
- `pair99g4near.py 0 1 [nseeds]` — neighbours of pair99g4 UI_w3_s0 (`MIN_DIST` env, default 6) → hunt/pair99g4near/
- `pair99digits.py 0 1 [nseeds]` — digit variants of pair99g4 UI_w3_s0, shading fixed → hunt/pair99digits/
- `pair99g4nearIU.py 0 1 [nseeds]` — neighbours of the pair99g4 IU grids → hunt/pair99g4nearIU/
- `pair99fills.py [cap]` — every digit fill of the four UI four-pocket shadings → hunt/pair99fills/
- `pinx.py shard(0=IU,1=UI) [limit]` — which third circle outside box 9 pins the r9c7/r9c9 shading → hunt/pinx/<kind>.log
- `plant.py variant seed [ceil|r7c8I_r9c7U]` — plant the 4 and 5 next to box 1, maximize box-1 chocolate (UPPER_LEFT.md)
- `groups.py K [limit] [workers]` — can a grid have K brainanas? exact component count, 20 s at K=5
- `kinds5.py shard nshards` — per box-9 pair kind, can the grid have 5 brainanas? (all infeasible, BRAINANAS.md)
- `tri68w.py` — circles r6c8 + r9c7 + r9c9 with a forced white dot on r7c5–r7c6 (both uninfected, consecutive); infeasible for both kinds.
- `tri68sweep.py` — same circles, one forced white-dot edge per run; sweep of rows 6–9 cols 4–6 (results in `probes/tri68w/sweep.txt`).
- `tri3.py` — circles r9c7 + r8c9 + r6c8, kind = shading of (r9c7, r8c9), circles + chocolate maximized.
- `tri3w66.py` — as tri3 with a white dot on some edge of r6c6 (solver picks the edge).
- `tri3wdot.py` — as tri3 with a forced white dot on one named edge (e.g. `UI r6c5 r7c5`).
- `kill9.py` — circles r9c7 r8c9 r6c8, r9c7 given 9, one forced white-dot edge (or `none`), shading free: KILLED means the dot makes r9c7 = 9 impossible.
- `pocket4.py` — circles r9c7 r8c9 r6c8, one forced white dot, shading free, at least four pockets: 4POCKET or NO4.
- `pair99b8d1.py` — r9c7 + r9c9 UI, at least two circles in box 8, a black dot on some edge inside box 1, optional pocket floor.
- `pair99b68.py` — r9c7 + r9c9, black dot inside box 1 or 2, a circle in box 6 off row 6 and one in box 8 off column 6, pocket floor.
- `pair99ring.py` — r9c7 + r9c9 UI with the opener kropki: a white or black dot on a domino touching r5c6–r5c9 or r6c5, the cells outside the 7-cell green block that r9c7 = 9 would force; pocket floor.
- `minuniq.py` — greedy irreducible clue set (circles, white dots, black dots unless `NO_BLACK=1`; no givens, positive dots only) that makes a found fill the unique solution; dots are stripped first with every circle kept, then circles. Keeps r9c7, r9c9 and the opener dot. Output in `unique/`.
- `render_unique.py` — two-panel PNG of a `unique/*.json` clue set: puzzle as presented, and the solution with shading.
- `x9hunt.py` — circle r9c7 (uninfected) + one other box-9 circle X (infected), r9c9 != 9, pocket floor, circles + chocolate maximized.
- `x9kill.py` — for one x9 grid, tests each white dot near box 9 alone with r9c7 given 9: KILLS = the dot makes r9c7 = 9 impossible (results in `probes/x9/killers.txt`).
