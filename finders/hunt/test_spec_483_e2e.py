"""WHAT A GREEN RUN DOES NOT COVER: any real finder's search (toy rule,
sub-second solve, no kill mid-solve under job-run; see
docs/research/2026-09-28-qqrr-tie-kill-resume.md), and the live app (solve
time, how a link renders in sudokumaker.app)."""

import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from cli_checks import check, check_refusal, finish, read_jsonl, run_cli
from dedupe import D4, canonical_key
from driver import run
from ortools.sat.python import cp_model
from protocol import Verdict
from render import GridCanvas
from subprocess_env import success_env
from sudoku_kit.uniqueness import check_uniqueness

SIDE = 4
SEEDS = 40
AS_FINDER = "--as-finder"


class SpecToyFinder:
    symmetry = D4

    def __init__(self):
        self.seeds_seen = 0

    def propose(self, rng):
        time.sleep(0.02)  # so a kill lands mid-hunt without a timing race
        self.seeds_seen += 1
        return tuple(rng.randint(0, 1) for _ in range(SIDE * SIDE))

    def verify(self, candidate):
        m = cp_model.CpModel()
        cells = [m.NewIntVar(0, 1, f"x{i}") for i in range(len(candidate))]
        for var, value in zip(cells, candidate, strict=True):
            m.Add(var == value)
        parity = m.NewIntVar(0, 1, "parity")
        m.Add(sum(cells) == 2 * m.NewIntVar(0, len(cells), "half") + parity)
        result = check_uniqueness(m, [*cells, parity])
        if not result.unique:
            return Verdict(ok=False, reason=f"model {result.status}")
        if result.first[-1] != 0:
            return Verdict(ok=False, reason="odd shaded-cell count")
        return Verdict(ok=True)

    def record(self, candidate):
        rows = [list(candidate[r * SIDE : (r + 1) * SIDE]) for r in range(SIDE)]
        return {
            "grid": list(candidate),
            "rows": rows,
            "workers": self.workers,
            "seeds_seen_at_find": self.seeds_seen,
        }

    def key(self, candidate):
        return candidate

    def candidate_from_record(self, record):
        return tuple(record["grid"])

    def render(self, candidate):
        canvas = GridCanvas(SIDE, SIDE, cell=20, margin=4)
        for i, cell in enumerate(candidate):
            if cell:
                canvas.shade_cell(i // SIDE, i % SIDE, (0, 0, 0))
        return canvas.image

    def save_state(self):
        return {"seeds_seen": self.seeds_seen}

    def load_state(self, state):
        self.seeds_seen = state["seeds_seen"]


def cli(out, *extra, env=None):
    return run_cli(__file__, AS_FINDER, "--out", out, *extra, env=env)


def seed_done(out):
    return [
        e["seed"]
        for e in read_jsonl(out / "progress.jsonl", missing_ok=True)
        if e.get("event") == "seed_done"
    ]


def kill_partway(out, *extra, min_done=5):
    proc = subprocess.Popen(
        [sys.executable, __file__, AS_FINDER, "--out", str(out), *extra],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=success_env(),
    )
    deadline = time.time() + 20
    while time.time() < deadline and proc.poll() is None:
        if len(seed_done(out)) >= min_done:
            break
        time.sleep(0.005)
    proc.kill()
    proc.wait(timeout=10)


def main():
    seeds = f"--seeds=0:{SEEDS}"
    with tempfile.TemporaryDirectory() as tmp:
        ref = Path(tmp) / "ref"
        r = cli(ref, seeds, "--workers", "1")
        check(
            f"uninterrupted reference hunt exits 0 ({r.stderr[-300:]})",
            r.returncode == 0,
        )
        ref_keys = {
            canonical_key(tuple(e["grid"]), D4)
            for e in read_jsonl(ref / "examples.jsonl")
        }
        check("the reference hunt found examples", len(ref_keys) > 0)

        out = Path(tmp) / "hunt"
        kill_partway(out, seeds, "--workers", "1")
        done_before = seed_done(out)
        check("the kill left a partial hunt", 0 < len(done_before) < SEEDS)
        check(
            "run.json holds argv, git sha and start time",
            set(json.loads((out / "run.json").read_text()))
            >= {"argv", "git_sha", "start_time"},
        )

        r = cli(out, seeds, "--workers", "1")
        check(f"resume exits 0 ({r.stderr[-300:]})", r.returncode == 0)
        check(
            "every seed done exactly once", sorted(seed_done(out)) == list(range(SEEDS))
        )

        examples = read_jsonl(out / "examples.jsonl")
        keys = [canonical_key(tuple(e["grid"]), D4) for e in examples]
        check("no symmetric duplicate in examples.jsonl", len(keys) == len(set(keys)))
        check("resume finds what an uninterrupted hunt finds", set(keys) == ref_keys)
        check(
            "every example passed the CP-SAT verifier (even count)",
            all(sum(e["grid"]) % 2 == 0 for e in examples),
        )
        summary = json.loads((out / "summary.json").read_text())
        check(
            "summary.json counts match the lines",
            summary == json.loads((ref / "summary.json").read_text()),
        )
        state = json.loads((out / "state.json").read_text())
        check(
            "state.json was reloaded across the kill, not restarted",
            state["state"]["seeds_seen"] == SEEDS,
        )
        check(
            "the hunt and its resume drew no pictures", not (out / "renders").exists()
        )
        r = subprocess.run(
            [sys.executable, __file__, AS_FINDER, "render", str(out)],
            capture_output=True,
            text=True,
            env=success_env(),
        )
        check(f"hunt render exits 0 ({r.stderr[-300:]})", r.returncode == 0)
        pngs = sorted(p.stem for p in (out / "renders").glob("*.png"))
        check("one PNG per example", len(pngs) == len(examples) and len(pngs) > 0)

        # Refusals.
        r = cli(out, f"--seeds=0:{SEEDS - 1}", "--workers", "1")
        check_refusal("a different argv refuses", r, "argv differs")
        check(
            "the refused resume left the seeds alone",
            sorted(seed_done(out)) == list(range(SEEDS)),
        )
        gated = Path(tmp) / "gated"
        r = cli(gated, "--seeds=0:3", env={"HUNT_FAKE_LOAD1": "25"})
        check_refusal("load above 24 refuses", r, "is above 24")
        check("and runs no seed", not (gated / "progress.jsonl").exists())
        r = cli(gated, "--seeds=0:3", "--force-load", env={"HUNT_FAKE_LOAD1": "25"})
        check("--force-load proceeds", r.returncode == 0 and len(seed_done(gated)) == 3)
        check(
            "--workers defaults to 3",
            {e["workers"] for e in read_jsonl(gated / "examples.jsonl")} == {3},
        )

        # Verification: inline drops rejects; --no-verify defers to `hunt verify`.
        deferred = Path(tmp) / "deferred"
        r = cli(deferred, seeds, "--no-verify", "--workers", "1")
        check(f"--no-verify exits 0 ({r.stderr[-300:]})", r.returncode == 0)
        raw = read_jsonl(deferred / "examples.jsonl")
        check(
            "--no-verify lets a rejected candidate through",
            any(sum(e["grid"]) % 2 for e in raw),
        )
        r = subprocess.run(
            [sys.executable, __file__, AS_FINDER, "verify", str(deferred)],
            capture_output=True,
            text=True,
            env=success_env(),
        )
        check(f"hunt verify exits 0 ({r.stderr[-300:]})", r.returncode == 0)
        stamp, *verdicts = read_jsonl(deferred / "verified.jsonl")
        check(
            "verified.jsonl stamps its example count and marks each verdict",
            stamp == {"verified_examples": len(raw)}
            and [v["ok"] for v in verdicts] == [sum(e["grid"]) % 2 == 0 for e in raw],
        )

    finish()


if __name__ == "__main__":
    if AS_FINDER in sys.argv:
        argv = [a for a in sys.argv[1:] if a != AS_FINDER]
        sys.exit(run(SpecToyFinder(), argv))
    sys.exit(main())
