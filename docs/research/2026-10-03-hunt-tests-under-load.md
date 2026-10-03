# Hunt tests under load, and the race-probe flake (#669)

## The `--out` race probe flake

`test_toy_hunt.py` once exited `[0, 0]` from "racing on a fresh --out: exactly
one wins" at load ~6. That is a test race, not a double win in the driver.
`driver.run` takes the `.lock` flock before it reads anything in `--out`. A
second launch that starts after the first has finished and released the lock
finds `run.json`, takes the resume path with the same argv, and exits 0 on a
finished hunt. Two plain simultaneous launches can therefore legitimately both
exit 0. The probe now starts a slow hunt (`toy_slow_finder.py`, 0:400), waits
for its `progress.jsonl` (written only after the lock is held), and asserts the
second launch exits 2 with "an active hunt (locked)".

## Forcing the real load above 24

The load gate reads `os.getloadavg()` unless `HUNT_FAKE_LOAD1` is set. To run
the hunt suite as on a busy box without loading it, put a `sitecustomize.py` on
`PYTHONPATH` that patches the call; subprocesses inherit it:

    mkdir -p .scratch/load
    printf 'import os\nos.getloadavg = lambda: (30.0, 30.0, 30.0)\n' > .scratch/load/sitecustomize.py
    for f in finders/hunt/test_*.py finders/qqrr/hunt/test_*.py; do
      PYTHONPATH=$PWD/.scratch/load uv run $f || echo "FAIL $f"
    done

Before the fix, `test_hunt_resume`, `test_hunt_verify`, `test_render_hook` and
`test_toy_hunt` failed this way, and some `exit 2` refusals in `test_toy_hunt`
passed on the load gate's exit 2 rather than the refusal they claimed.
`subprocess_env.pin_idle_load()` now pins each of those files.
