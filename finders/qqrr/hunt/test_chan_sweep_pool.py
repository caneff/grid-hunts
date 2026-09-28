"""chan_sweep's worker pool configures each worker (#628, C2). A forkserver worker imports
chan_sweep fresh, so without the pool's initializer `solve` reads no globals and every task
dies with NameError. Seams: chan_sweep.pool running chan_sweep.solve, and the script's own
run. The main guard keeps a forkserver child, which re-imports this script, from running the
test again.

    uv run finders/qqrr/hunt/test_chan_sweep_pool.py
"""

import multiprocessing
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import chan_sweep

if __name__ == "__main__":
    # The start method a live run gets on Linux from Python 3.14; fork would hide the bug.
    multiprocessing.set_start_method("forkserver", force=True)
    argv = ["br", "1", "0.01", "/dev/null", "r5c1"]
    with chan_sweep.pool(1, argv) as p:
        line = p.apply(chan_sweep.solve, ((((1, 1), (1, 4)), 0, 1),))
    assert "pair r2c2=r2c5 slots 01 " in line, line
    # The script's own run goes through the same pool: one pair, its 12 slot patterns.
    with tempfile.TemporaryDirectory() as d:
        log = Path(d) / "chan.log"
        script = Path(__file__).resolve().parent / "chan_sweep.py"
        args = ["br", "1", "0.01", str(log), "r5c1", "pairs=r2c2=r2c5"]
        run = subprocess.run(
            [sys.executable, str(script), *args], capture_output=True, text=True
        )
        assert run.returncode == 0, run.stderr
        lines = log.read_text().splitlines()
        assert sum(" r2c2=r2c5 slots " in x for x in lines) == 12, lines
        assert lines[-1].startswith("done: "), lines
    print("ok")
