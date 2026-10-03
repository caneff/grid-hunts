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


def read_jsonl(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


with tempfile.TemporaryDirectory() as tmp:
    out = Path(tmp) / "hunt-out"
    result = subprocess.run(
        [sys.executable, str(TOY_RENDER_FINDER), "--out", str(out), "--seeds", "0:200"],
        capture_output=True,
        text=True,
    )
    check(f"exit code 0 (stderr: {result.stderr[-500:]})", result.returncode == 0)

    examples = read_jsonl(out / "examples.jsonl")
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

    progress = read_jsonl(out / "progress.jsonl")
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
    examples = read_jsonl(out / "examples.jsonl")
    progress = read_jsonl(out / "progress.jsonl")
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
    # missing PNG for any already-accepted example. This block is the
    # stateless finder; the stateful blocks below cover the rest.
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
    examples_before = read_jsonl(out / "examples.jsonl")
    check("at least one example was found (render-fail run)", len(examples_before) > 0)
    check(
        "no PNG exists yet -- every render failed",
        not [p for p in (out / "renders").iterdir() if p.name.count(".") == 1],
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
    examples_after = read_jsonl(out / "examples.jsonl")
    check(
        "resume didn't rerun the search -- same examples, no duplicates",
        examples_after == examples_before,
    )
    progress_after = read_jsonl(out / "progress.jsonl")
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
    # A stateful finder's render-repair (#538): its `propose()` can have
    # side effects state.json owns, so repair never calls it -- it rebuilds
    # the candidate from the examples.jsonl record via the finder's
    # `candidate_from_record` and renders that.
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
        # TOY_NO_PROPOSE marks the resume run: every seed is already done,
        # so anything that reaches propose() is a render repair calling it.
        if os.environ.get("TOY_NO_PROPOSE"):
            raise RuntimeError("propose() called during resume")
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

    def candidate_from_record(self, record):
        # TOY_HOOK_RAISES simulates a record the hook cannot rebuild.
        if os.environ.get("TOY_HOOK_RAISES"):
            raise KeyError("grid")
        # TOY_HOOK_MUTATES simulates a hook that breaks the contract by
        # changing the finder's state.
        if os.environ.get("TOY_HOOK_MUTATES"):
            self.seeds_seen += 100
        return tuple(record["grid"])

    def render(self, candidate):
        if os.environ.get("TOY_RENDER_FAIL"):
            raise RuntimeError("simulated transient render failure")
        canvas = GridCanvas(2, 2, cell=10)
        for i, cell in enumerate(candidate):
            if cell:
                canvas.shade_cell(i // 2, i % 2, (0, 0, 0))
        return canvas.image

if os.environ.get("TOY_NO_HOOK"):
    StatefulRenderFinder.candidate_from_record = None
if os.environ.get("TOY_NO_SAVE"):
    StatefulRenderFinder.save_state = None
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
    resume_env = dict(os.environ, TOY_NO_PROPOSE="1")
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
    resumed_examples = read_jsonl(out / "examples.jsonl")
    check(
        "a stateful finder's failed renders are repaired from the recorded "
        "examples on resume",
        len(resumed_examples) > 0
        and len(list((out / "renders").glob("*.png"))) == len(resumed_examples),
    )
    check(
        "repair never called propose() (exit 0 under TOY_NO_PROPOSE) and left "
        "state.json's counter unchanged",
        json.loads((out / "state.json").read_text())["state"]["seeds_seen"] == 30,
    )
    # Each repaired picture is drawn from its own seed's record: a fresh
    # hunt with rendering working the whole way is the control (#538 review C3).
    control_out = Path(tmp) / "control"
    subprocess.run(
        [
            sys.executable,
            "-c",
            stateful_render_script,
            "--out",
            str(control_out),
            "--seeds",
            "0:30",
        ],
        capture_output=True,
        text=True,
        env=dict(os.environ),
    )
    control = {p.name: p.read_bytes() for p in (control_out / "renders").glob("*.png")}
    repaired = {p.name: p.read_bytes() for p in (out / "renders").glob("*.png")}
    check(
        "every repaired picture is byte-identical to the fresh hunt's picture "
        "for the same seed",
        len(control) > 1 and repaired == control,
    )

    # A record the hook cannot rebuild is a presentation-layer fault too: it
    # lands on the seed's event and never stops the resume (#538 review C1).
    raise_out = Path(tmp) / "hook-raises"
    run_argv = [sys.executable, "-c", stateful_render_script]
    seeds_argv = ["--out", str(raise_out), "--seeds", "0:30"]
    subprocess.run(
        run_argv + seeds_argv,
        capture_output=True,
        text=True,
        env=dict(os.environ, TOY_RENDER_FAIL="1"),
    )
    raise_result = subprocess.run(
        run_argv + seeds_argv,
        capture_output=True,
        text=True,
        env=dict(os.environ, TOY_HOOK_RAISES="1"),
    )
    raise_events = read_jsonl(raise_out / "progress.jsonl")
    check(
        f"a raising candidate_from_record doesn't stop the resume (stderr: "
        f"{raise_result.stderr[-300:]})",
        raise_result.returncode == 0 and len(raise_events) == 30,
    )
    check(
        "the hook's failure is recorded on each example's event as render_error",
        all(
            "KeyError" in e.get("render_error", "")
            for e in raise_events
            if e.get("outcome") == "example"
        ),
    )

    # A stateful finder with no candidate_from_record is left alone: nothing
    # is rebuilt, and its failed renders keep their original render_error
    # (#538 review C2).
    nohook_out = Path(tmp) / "no-hook"
    nohook_argv = ["--out", str(nohook_out), "--seeds", "0:30"]
    subprocess.run(
        run_argv + nohook_argv,
        capture_output=True,
        text=True,
        env=dict(os.environ, TOY_RENDER_FAIL="1"),
    )
    nohook_result = subprocess.run(
        run_argv + nohook_argv,
        capture_output=True,
        text=True,
        env=dict(os.environ, TOY_NO_HOOK="1", TOY_NO_PROPOSE="1"),
    )
    nohook_events = read_jsonl(nohook_out / "progress.jsonl")
    check(
        "a stateful finder with no candidate_from_record resumes with exit 0 "
        "and no picture",
        nohook_result.returncode == 0
        and not list((nohook_out / "renders").glob("*.png")),
    )
    check(
        "its events keep the original render failure, untouched by repair",
        all(
            e.get("render_error", "").startswith("RuntimeError")
            for e in nohook_events
            if e.get("outcome") == "example"
        ),
    )

    check(
        "the hook-less finder's resume says on stderr that it left renders "
        "unrepaired (#627 S6)",
        "unrepaired" in nohook_result.stderr,
    )

    # The warning fires only when a picture is actually missing: the same
    # refused finder resuming with every render intact stays quiet.
    quiet_out = Path(tmp) / "no-hook-intact"
    quiet_argv = ["--out", str(quiet_out), "--seeds", "0:30"]
    quiet_first = subprocess.run(run_argv + quiet_argv, capture_output=True, text=True)
    quiet_result = subprocess.run(
        run_argv + quiet_argv,
        capture_output=True,
        text=True,
        env=dict(os.environ, TOY_NO_HOOK="1", TOY_NO_PROPOSE="1"),
    )
    check(
        "a refused finder with every render intact resumes without the "
        "unrepaired warning",
        quiet_first.returncode == 0
        and quiet_result.returncode == 0
        and list((quiet_out / "renders").glob("*.png"))
        and "unrepaired" not in quiet_result.stderr,
    )

    # A stateful finder with `load_state` and a hook but no `save_state`
    # fails closed too: repair cannot snapshot its state, so the hook is
    # never called and the failed renders keep their original render_error
    # (#538, #627 controller-1). Only the resume drops `save_state`: the
    # first run must leave a state.json for the resume to load, or the
    # resume reruns every seed and renders them afresh. TOY_HOOK_RAISES would
    # overwrite that error with a KeyError if the hook were called.
    nosave_out = Path(tmp) / "no-save"
    nosave_argv = ["--out", str(nosave_out), "--seeds", "0:30"]
    nosave_first = subprocess.run(
        run_argv + nosave_argv,
        capture_output=True,
        text=True,
        env=dict(os.environ, TOY_RENDER_FAIL="1"),
    )
    nosave_result = subprocess.run(
        run_argv + nosave_argv,
        capture_output=True,
        text=True,
        env=dict(os.environ, TOY_NO_SAVE="1", TOY_HOOK_RAISES="1"),
    )
    nosave_events = read_jsonl(nosave_out / "progress.jsonl")
    check(
        "the no-save first run exits 0 and found examples to repair",
        nosave_first.returncode == 0
        and any(e.get("outcome") == "example" for e in nosave_events),
    )
    check(
        f"a stateful finder with no save_state resumes with exit 0 and no "
        f"picture (stderr: {nosave_result.stderr[-300:]})",
        nosave_result.returncode == 0
        and not list((nosave_out / "renders").glob("*.png")),
    )
    check(
        "its events keep the original render failure: candidate_from_record "
        "was never called",
        all(
            e.get("render_error", "").startswith("RuntimeError")
            for e in nosave_events
            if e.get("outcome") == "example"
        ),
    )

    # A hook that mutates finder state must not reach state.json: repair
    # snapshots the state before the call and restores it after (Codex gate
    # 2). A kill is simulated by truncating progress.jsonl, so the resume
    # both repairs renders and reruns seeds; the persisted state must equal
    # the one a resume with a well-behaved hook writes.
    def resumed_state(name, resume_extra_env):
        run_out = Path(tmp) / name
        run_args = ["--out", str(run_out), "--seeds", "0:30"]
        subprocess.run(
            run_argv + run_args,
            capture_output=True,
            text=True,
            env=dict(os.environ, TOY_RENDER_FAIL="1"),
        )
        lines = (run_out / "progress.jsonl").read_text().splitlines(keepends=True)
        (run_out / "progress.jsonl").write_text("".join(lines[:10]))
        resumed = subprocess.run(
            run_argv + run_args,
            capture_output=True,
            text=True,
            env=dict(os.environ, **resume_extra_env),
        )
        return resumed, json.loads((run_out / "state.json").read_text())

    clean, clean_state = resumed_state("state-clean", {})
    mutating, mutating_state = resumed_state(
        "state-mutating", {"TOY_HOOK_MUTATES": "1"}
    )
    check(
        f"both state-mutation resumes exit 0 (stderr: {mutating.stderr[-300:]})",
        clean.returncode == 0 and mutating.returncode == 0,
    )
    check(
        "a hook that mutates finder state never reaches state.json",
        clean_state["state"]["seeds_seen"] > 30 and mutating_state == clean_state,
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
        "renders/ being a directory doesn't stop full cleanup after the "
        "mismatch, and leaves only .lock behind (#519, see driver.py's "
        "_cleanup_partial_output)",
        out.exists() and {p.name for p in out.iterdir()} == {".lock"},
    )

with tempfile.TemporaryDirectory() as tmp:
    # A save that fails after writing part of the file (#537): renders/<seed>.png
    # must only ever exist complete, and resume must end with valid PNGs. A
    # truncated PNG already at the destination is
    # not "done" either: repair re-renders it.
    from PIL import Image

    out = Path(tmp) / "hunt-out"
    partial_script = f"""
import os
import sys
sys.path.insert(0, {str(HERE)!r})
from dedupe import D4
from driver import run
from protocol import Verdict
from render import GridCanvas

class PartialImage:
    def __init__(self, image):
        self.image = image

    def save(self, path):
        # A disk-full save: write the head of the file, then fail.
        import io
        buf = io.BytesIO()
        self.image.save(buf, format="PNG")
        with open(path, "wb") as f:
            f.write(buf.getvalue()[:20])
        raise OSError("simulated disk full mid-write")

class PartialRenderFinder:
    symmetry = D4

    def propose(self, rng):
        return tuple(rng.randint(0, 1) for _ in range(4))

    def verify(self, candidate):
        return Verdict(ok=True)

    def record(self, candidate):
        return {{"grid": list(candidate)}}

    def key(self, candidate):
        return candidate

    def render(self, candidate):
        canvas = GridCanvas(2, 2, cell=10)
        for i, cell in enumerate(candidate):
            if cell:
                canvas.shade_cell(i // 2, i % 2, (0, 0, 0))
        if os.environ.get("TOY_PARTIAL_SAVE"):
            return PartialImage(canvas.image)
        return canvas.image

sys.exit(run(PartialRenderFinder(), sys.argv[1:]))
"""
    argv = [sys.executable, "-c", partial_script, "--out", str(out), "--seeds", "0:30"]
    first = subprocess.run(
        argv,
        capture_output=True,
        text=True,
        env=dict(os.environ, TOY_PARTIAL_SAVE="1"),
    )
    check(
        f"a hunt whose renders fail mid-write still exits 0 (stderr: "
        f"{first.stderr[-500:]})",
        first.returncode == 0,
    )

    def decodes(path):
        try:
            with Image.open(path) as img:
                img.load()
            return True
        except Exception:
            return False

    check(
        "a failed mid-write save leaves no file at renders/<seed>.png",
        not [p for p in (out / "renders").iterdir() if p.name.count(".") == 1],
    )
    check(
        "a failed mid-write save leaves no temp file behind",
        not list((out / "renders").iterdir()),
    )
    env_ok = {k: v for k, v in os.environ.items() if k != "TOY_PARTIAL_SAVE"}
    resume = subprocess.run(argv, capture_output=True, text=True, env=env_ok)
    check(f"resume exits 0 (stderr: {resume.stderr[-500:]})", resume.returncode == 0)
    pngs = sorted((out / "renders").glob("*.png"))
    n_examples = len((out / "examples.jsonl").read_text().splitlines())
    check(
        "resume after a mid-write failure ends with a valid PNG per example",
        n_examples > 0 and len(pngs) == n_examples and all(decodes(p) for p in pngs),
    )

    # A kill mid-save leaves a driver temp file; resume sweeps it. A file
    # that only looks like one is not the driver's and stays.
    stale = out / "renders" / "7.tmp-99999.png"
    stale.write_bytes(b"partial")
    foreign = out / "renders" / "notes.tmp-x.png"
    foreign.write_bytes(b"mine")
    subprocess.run(argv, capture_output=True, text=True, env=env_ok)
    check("resume sweeps a stale driver temp file", not stale.exists())
    check("resume leaves a non-driver *.tmp-*.png alone", foreign.exists())
    foreign.unlink()

    # Tail-truncated: still decodes, but has no IEND.
    victim = pngs[-1]
    victim.write_bytes(victim.read_bytes()[:-12])
    subprocess.run(argv, capture_output=True, text=True, env=env_ok)
    check(
        "resume re-renders a PNG whose IEND tail is cut off",
        decodes(victim)
        and victim.stat().st_size > 0
        and victim.read_bytes().endswith(b"IEND\xaeB`\x82"),
    )

    victim = pngs[0]
    victim.write_bytes(victim.read_bytes()[:20])
    resume2 = subprocess.run(argv, capture_output=True, text=True, env=env_ok)
    check(
        f"second resume exits 0 (stderr: {resume2.stderr[-500:]})",
        resume2.returncode == 0,
    )
    check(
        "resume re-renders a truncated PNG already at the destination",
        decodes(victim),
    )

sys.exit(0 if ok else 1)
