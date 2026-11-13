import fcntl
import os
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cli_checks import check, check_refusal, finish, read_jsonl, run_cli
from subprocess_env import pin_idle_load, success_env

pin_idle_load()

HERE = Path(__file__).resolve().parent
TOY_FINDER = HERE / "toy_finder.py"
TOY_RENDER_FINDER = HERE / "toy_render_finder.py"

# A render finder that builds its picture from `candidate_from_record` only
# (its record is not a candidate) and, on demand, stalls inside `render` so a
# test can kill the process mid-pass.
HOOK_FINDER = """\
import os
import sys
import time

sys.path.insert(0, {hunt!r})
from driver import run
from toy_render_finder import ToyRenderFinder


class HookFinder(ToyRenderFinder):
    def record(self, candidate):
        return {{"cells": list(candidate)}}

    def candidate_from_record(self, record):
        return tuple(record["cells"])

    def render(self, candidate):
        assert isinstance(candidate, tuple), "render got the raw record"
        if os.environ.get("TOY_RENDER_STALL") and time.time() > float(
            os.environ["TOY_RENDER_STALL"]
        ):
            time.sleep(60)
        return super().render(candidate)


sys.exit(run(HookFinder(), sys.argv[1:]))
"""


def example_seeds(out):
    return sorted(
        e["seed"]
        for e in read_jsonl(out / "progress.jsonl")
        if e["outcome"] == "example"
    )


def renders_state(out):
    d = out / "renders"
    return {p.name: p.read_bytes() for p in d.iterdir()} if d.is_dir() else None


with tempfile.TemporaryDirectory() as tmp:
    out = Path(tmp) / "hunt-out"
    r = run_cli(TOY_RENDER_FINDER, "--out", str(out), "--seeds", "0:200")
    check(f"hunt exits 0 ({r.stderr[-300:]})", r.returncode == 0)
    seeds = example_seeds(out)
    check("the hunt found examples", len(seeds) > 0)
    check("a hunt draws no pictures: no renders/", not (out / "renders").exists())

    r = run_cli(TOY_RENDER_FINDER, "--out", str(out), "--seeds", "0:200")
    check("a resume draws no pictures either", not (out / "renders").exists())

    r = run_cli(TOY_RENDER_FINDER, "render", str(out))
    check(f"render exits 0 ({r.stderr[-300:]})", r.returncode == 0)
    names = sorted(p.name for p in (out / "renders").iterdir())
    check(
        "renders/ holds one <seed>.png per example and nothing else",
        names == sorted(f"{s}.png" for s in seeds),
    )
    from PIL import Image

    decodes = True
    for p in (out / "renders").iterdir():
        with Image.open(p) as img:
            img.load()
            decodes = decodes and img.format == "PNG"
    check("every picture decodes as a PNG", decodes)
    first = renders_state(out)

    # A stale picture, a stale scratch directory a kill left: a re-run
    # replaces the set whole and sweeps the scratch.
    (out / "renders" / "9999.png").write_bytes(b"stale")
    (out / "renders.tmp").mkdir()
    (out / "renders.tmp" / "1.png").write_bytes(b"half")
    (out / "renders.old").mkdir()
    r = run_cli(TOY_RENDER_FINDER, "render", str(out))
    check("re-run exits 0", r.returncode == 0)
    check("re-run converges to the same full set", renders_state(out) == first)
    check(
        "re-run sweeps renders.tmp and renders.old",
        not (out / "renders.tmp").exists() and not (out / "renders.old").exists(),
    )

    # A failing draw refuses and leaves the previous set untouched.
    r = run_cli(TOY_RENDER_FINDER, "render", str(out), env={"TOY_RENDER_FAIL": "1"})
    check_refusal("a failing render refuses", r, "did not draw")
    check("it names the seed", f"seed {seeds[0]}" in r.stderr)
    check("the previous set is untouched", renders_state(out) == first)
    check("no scratch directory is left", not (out / "renders.tmp").exists())

    # A held lock refuses.
    lock = os.open(out / ".lock", os.O_RDWR)
    fcntl.flock(lock, fcntl.LOCK_EX)
    r = run_cli(TOY_RENDER_FINDER, "render", str(out))
    os.close(lock)
    check_refusal("a locked directory refuses", r, "is locked")
    check("and changes nothing", renders_state(out) == first)

with tempfile.TemporaryDirectory() as tmp:
    out = Path(tmp) / "plain"
    run_cli(TOY_FINDER, "--out", str(out), "--seeds", "0:50")
    r = run_cli(TOY_FINDER, "render", str(out))
    check_refusal("a finder with no render refuses", r, "the finder has no render")
    check("and draws nothing", not (out / "renders").exists())

with tempfile.TemporaryDirectory() as tmp:
    r = run_cli(TOY_RENDER_FINDER, "render", str(Path(tmp) / "empty"))
    check_refusal(
        "a directory with no examples.jsonl refuses", r, "not a hunt directory"
    )

with tempfile.TemporaryDirectory() as tmp:
    # candidate_from_record is the rebuild; a kill mid-pass leaves the
    # previous set (or none), and a re-run converges.
    script = Path(tmp) / "hook_finder.py"
    script.write_text(HOOK_FINDER.format(hunt=str(HERE)))
    out = Path(tmp) / "hunt-out"
    run_cli(script, "--out", str(out), "--seeds", "0:200")
    seeds = example_seeds(out)
    r = run_cli(script, "render", str(out))
    check(
        f"render via candidate_from_record exits 0 ({r.stderr[-300:]})",
        r.returncode == 0,
    )
    full = renders_state(out)
    check("one picture per example", sorted(full) == sorted(f"{s}.png" for s in seeds))

    def killed_render(out):
        """Start a render that stalls once it has drawn two pictures, kill it."""
        proc = subprocess.Popen(
            [sys.executable, str(script), "render", str(out)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            env=success_env({"TOY_RENDER_STALL": "1"}),
        )
        deadline = time.time() + 20
        scratch = out / "renders.tmp"
        while time.time() < deadline and proc.poll() is None:
            if scratch.is_dir() and len(list(scratch.glob("*.png"))) >= 2:
                break
            time.sleep(0.02)
        mid = proc.poll() is None
        proc.send_signal(signal.SIGKILL)
        proc.wait()
        return mid

    check("the stalled render was killed mid-pass", killed_render(out))
    check("a kill during render leaves the previous set", renders_state(out) == full)
    r = run_cli(script, "render", str(out))
    check(
        "a re-run after the kill converges",
        r.returncode == 0 and renders_state(out) == full,
    )

    fresh = Path(tmp) / "fresh"
    run_cli(script, "--out", str(fresh), "--seeds", "0:200")
    check("kill mid-pass with no earlier set", killed_render(fresh))
    check(
        "a kill during a first render leaves no renders/",
        not (fresh / "renders").exists(),
    )
    r = run_cli(script, "render", str(fresh))
    check(
        "and a re-run draws the full set",
        r.returncode == 0 and renders_state(fresh) == full,
    )

finish()
