"""The `hunt` CLI's render hook, in a subprocess (#490).

A finder that offers `render` gets one PNG per examples.jsonl line; a finder
that doesn't gets none. Black-box: only what a caller of the hunt CLI can
see -- files on disk and exit code, never a driver.py internal.

    uv run finders/hunt/test_render_hook.py
"""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
TOY_FINDER = HERE / "toy_finder.py"
TOY_RENDER_FINDER = HERE / "toy_render_finder.py"

ok = True


def check(name, cond):
    global ok
    status = "ok" if cond else "FAIL"
    if not cond:
        ok = False
    print(f"{status}: {name}")


with tempfile.TemporaryDirectory() as tmp:
    out = Path(tmp) / "hunt-out"
    result = subprocess.run(
        [sys.executable, str(TOY_RENDER_FINDER), "--out", str(out), "--seeds", "0:200"],
        capture_output=True,
        text=True,
    )
    check(f"exit code 0 (stderr: {result.stderr[-500:]})", result.returncode == 0)

    examples = [
        json.loads(line)
        for line in (out / "examples.jsonl").read_text().splitlines()
        if line
    ]
    check("at least one example was found over 200 seeds", len(examples) > 0)

    renders_dir = out / "renders"
    check(
        "a renders/ directory exists when the finder offers render",
        renders_dir.is_dir(),
    )

    png_files = sorted(renders_dir.glob("*.png")) if renders_dir.is_dir() else []
    check(
        "one PNG exists per examples.jsonl line",
        len(png_files) == len(examples),
    )

    progress = [
        json.loads(line)
        for line in (out / "progress.jsonl").read_text().splitlines()
        if line
    ]
    accepted_seeds = {e["seed"] for e in progress if e.get("outcome") == "example"}
    check(
        "each PNG is named after the seed it belongs to, not a running index",
        {p.stem for p in png_files} == {str(s) for s in accepted_seeds},
    )

with tempfile.TemporaryDirectory() as tmp:
    out = Path(tmp) / "hunt-out"
    result = subprocess.run(
        [sys.executable, str(TOY_FINDER), "--out", str(out), "--seeds", "0:200"],
        capture_output=True,
        text=True,
    )
    check(
        f"render-less finder still exits 0 (stderr: {result.stderr[-500:]})",
        result.returncode == 0,
    )
    check(
        "a finder with no render writes no renders/ directory",
        not (out / "renders").exists(),
    )

with tempfile.TemporaryDirectory() as tmp:
    # A finder whose render() raises must not take the whole hunt down with
    # it (#490 correctness review C1): the example itself is still real and
    # already durable in examples.jsonl by the time render() runs, so a
    # presentation-layer fault gets recorded on the seed's event, not
    # treated as a search failure.
    out = Path(tmp) / "hunt-out"
    raising_render_script = f"""
import sys
sys.path.insert(0, {str(HERE)!r})
from driver import run
from protocol import Verdict

class RaisingRenderFinder:
    symmetry = "IDENTITY"

    def propose(self, rng):
        return tuple(rng.randint(0, 1) for _ in range(4))

    def verify(self, candidate):
        return Verdict(ok=True)

    def record(self, candidate):
        return {{"grid": list(candidate)}}

    def key(self, candidate):
        return candidate

    def render(self, candidate):
        raise RuntimeError("boom")

sys.exit(run(RaisingRenderFinder(), sys.argv[1:]))
"""
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            raising_render_script,
            "--out",
            str(out),
            "--seeds",
            "0:5",
        ],
        capture_output=True,
        text=True,
    )
    check(
        f"a raising render() still exits 0 (stderr: {result.stderr[-500:]})",
        result.returncode == 0,
    )
    examples = [
        json.loads(line)
        for line in (out / "examples.jsonl").read_text().splitlines()
        if line
    ]
    progress = [
        json.loads(line)
        for line in (out / "progress.jsonl").read_text().splitlines()
        if line
    ]
    example_events = [e for e in progress if e.get("outcome") == "example"]
    check(
        "at least one example is still written despite render() raising",
        len(examples) > 0 and len(examples) == len(example_events),
    )
    check(
        "every example's event records the render failure instead of silently dropping it",
        all(e.get("render_error") for e in example_events),
    )

with tempfile.TemporaryDirectory() as tmp:
    # A render failure that clears up (a full disk that got space back, a
    # finder bug since fixed) must not leave examples.jsonl and renders/
    # permanently mismatched just because the seed's outcome was already
    # durable when it failed (#524 Codex pass 1): resume re-attempts a
    # missing PNG for any already-accepted example, for a stateless finder
    # -- see driver.py's `_repair_renders` for why a stateful finder is out
    # of scope here.
    out = Path(tmp) / "hunt-out"
    fail_env = dict(os.environ, TOY_RENDER_FAIL="1")
    result = subprocess.run(
        [sys.executable, str(TOY_RENDER_FINDER), "--out", str(out), "--seeds", "0:200"],
        capture_output=True,
        text=True,
        env=fail_env,
    )
    check(
        f"a fresh hunt with every render failing still exits 0 (stderr: "
        f"{result.stderr[-500:]})",
        result.returncode == 0,
    )
    examples_before = [
        json.loads(line)
        for line in (out / "examples.jsonl").read_text().splitlines()
        if line
    ]
    check("at least one example was found (render-fail run)", len(examples_before) > 0)
    check(
        "no PNG exists yet -- every render failed",
        not list((out / "renders").glob("*.png")),
    )

    resume_env = dict(os.environ)
    resume_env.pop("TOY_RENDER_FAIL", None)
    resume_result = subprocess.run(
        [sys.executable, str(TOY_RENDER_FINDER), "--out", str(out), "--seeds", "0:200"],
        capture_output=True,
        text=True,
        env=resume_env,
    )
    check(
        f"resume with rendering fixed exits 0 (stderr: {resume_result.stderr[-500:]})",
        resume_result.returncode == 0,
    )
    examples_after = [
        json.loads(line)
        for line in (out / "examples.jsonl").read_text().splitlines()
        if line
    ]
    check(
        "resume didn't rerun the search -- same examples, no duplicates",
        examples_after == examples_before,
    )
    progress_after = [
        json.loads(line)
        for line in (out / "progress.jsonl").read_text().splitlines()
        if line
    ]
    check(
        "no seed_done event fired twice for the same seed",
        len({e["seed"] for e in progress_after}) == len(progress_after),
    )
    accepted_seeds = {
        e["seed"] for e in progress_after if e.get("outcome") == "example"
    }
    png_stems_after = {p.stem for p in (out / "renders").glob("*.png")}
    check(
        "every previously-failed example now has its PNG, repaired by resume",
        png_stems_after == {str(s) for s in accepted_seeds},
    )

with tempfile.TemporaryDirectory() as tmp:
    # A stateful finder's render-repair is out of scope (see driver.py's
    # `_repair_renders` docstring): its `propose()` can have side effects
    # state.json owns, so a missing PNG for it stays missing rather than
    # risk corrupting state by calling `propose()` a second time.
    out = Path(tmp) / "hunt-out"
    stateful_render_script = f"""
import os
import sys
sys.path.insert(0, {str(HERE)!r})
from dedupe import D4
from driver import run
from protocol import Verdict
from render import GridCanvas

class StatefulRenderFinder:
    symmetry = D4

    def __init__(self):
        self.seeds_seen = 0

    def propose(self, rng):
        self.seeds_seen += 1
        return tuple(rng.randint(0, 1) for _ in range(4))

    def verify(self, candidate):
        return Verdict(ok=True)

    def record(self, candidate):
        return {{"grid": list(candidate)}}

    def key(self, candidate):
        return candidate

    def save_state(self):
        return {{"seeds_seen": self.seeds_seen}}

    def load_state(self, state):
        self.seeds_seen = state["seeds_seen"]

    def render(self, candidate):
        if os.environ.get("TOY_RENDER_FAIL"):
            raise RuntimeError("simulated transient render failure")
        return GridCanvas(2, 2, cell=10).image

sys.exit(run(StatefulRenderFinder(), sys.argv[1:]))
"""
    fail_env = dict(os.environ, TOY_RENDER_FAIL="1")
    subprocess.run(
        [
            sys.executable,
            "-c",
            stateful_render_script,
            "--out",
            str(out),
            "--seeds",
            "0:30",
        ],
        capture_output=True,
        text=True,
        env=fail_env,
    )
    resume_env = dict(os.environ)
    resume_env.pop("TOY_RENDER_FAIL", None)
    resume_result = subprocess.run(
        [
            sys.executable,
            "-c",
            stateful_render_script,
            "--out",
            str(out),
            "--seeds",
            "0:30",
        ],
        capture_output=True,
        text=True,
        env=resume_env,
    )
    check(
        f"a stateful finder's resume still exits 0 (stderr: "
        f"{resume_result.stderr[-500:]})",
        resume_result.returncode == 0,
    )
    check(
        "a stateful finder's already-failed renders stay unrepaired (documented scope limit)",
        not list((out / "renders").glob("*.png")),
    )
    check(
        "state.json's counter wasn't double-incremented by a render-repair attempt",
        json.loads((out / "state.json").read_text())["state"]["seeds_seen"] == 30,
    )

with tempfile.TemporaryDirectory() as tmp:
    # A render-providing finder that accepts (and renders) an example on
    # one seed, then hits a SymmetryMismatch (#509/#511) on a later one,
    # must still clean up fully: `_cleanup_partial_output` iterates
    # OUTPUT_FILES and renders/ is the one entry there that's a directory,
    # not a file -- `path.unlink()` raises `IsADirectoryError` on it if not
    # special-cased, once a render has actually been written. Caught by
    # rebasing this PR onto #488/#509 landing on main, not by the original
    # render-hook review. Seed 0's candidate has a key() the length the
    # symmetry group expects (4), so it's accepted and rendered; seed 1's
    # has a different length, which is what canonical_key rejects.
    out = Path(tmp) / "hunt-out"
    render_symmetry_mismatch_script = f"""
import sys
sys.path.insert(0, {str(HERE)!r})
from driver import run
from protocol import Verdict
from render import GridCanvas

class RenderMismatchedLengthFinder:
    symmetry = [(0, 1, 2, 3), (1, 3, 0, 2), (2, 0, 3, 1), (3, 2, 1, 0)]

    def __init__(self):
        self.calls = 0

    def propose(self, rng):
        # Seeds run 0, 1, 2, ... in order within one process (a fresh hunt
        # never reorders them), so this counter is exactly the seed number
        # -- just a marker `key()` below reads to alternate deterministically.
        marker = self.calls
        self.calls += 1
        return marker

    def verify(self, candidate):
        return Verdict(ok=True)

    def record(self, candidate):
        return {{"marker": candidate}}

    def key(self, candidate):
        return (0, 1, 2, 3) if candidate % 2 == 0 else (0, 1, 2, 3, 4)

    def render(self, candidate):
        return GridCanvas(3, 3, cell=10).image

sys.exit(run(RenderMismatchedLengthFinder(), sys.argv[1:]))
"""
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            render_symmetry_mismatch_script,
            "--out",
            str(out),
            "--seeds",
            "0:5",
        ],
        capture_output=True,
        text=True,
    )
    check(
        f"a render-providing finder hitting a symmetry mismatch exits 2 "
        f"(stderr: {result.stderr[-500:]})",
        result.returncode == 2,
    )
    check(
        "renders/ being a directory doesn't stop full cleanup after the mismatch",
        not out.exists(),
    )

sys.exit(0 if ok else 1)
