"""Spec #115 at the `just check` seam: a killed toy hunt's `summary DIR` and
`links DIR` answer like its resume would, `render DIR` draws each example's own
picture, and a locked directory refuses.

WHAT A GREEN RUN DOES NOT COVER: any real finder's search, hooks or record
(toy rule, parity verifier, offline fake mint; the real finders migrate in
#116 and #117), the SIGKILL landing inside a log write (the torn last line is
injected by hand into a copy), a hunt long enough for load or timing to
matter, and how a minted link renders in sudokumaker.app.

    uv run finders/hunt/test_spec_115_e2e.py
"""

import fcntl
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from cli_checks import check, check_refusal, finish, read_jsonl, run_cli
from dedupe import D4
from driver import run
from protocol import Verdict
from render import GridCanvas
from short_link import fake_mint
from subprocess_env import success_env

SIDE = 4
SEEDS = 40
AS_FINDER = "--as-finder"


class E2EFinder:
    symmetry = D4

    def propose(self, rng):
        time.sleep(0.02)  # so a kill lands mid-hunt without a timing race
        return tuple(rng.randint(0, 1) for _ in range(SIDE * SIDE))

    def verify(self, candidate):
        ok = sum(candidate) % 2 == 0
        return Verdict(ok=ok, reason="" if ok else "odd shaded-cell count")

    def record(self, candidate):
        return {"cells": list(candidate)}

    def key(self, candidate):
        return candidate

    def candidate_from_record(self, record):
        return tuple(record["cells"])

    def link_document(self, candidate):
        return {
            "formatVersion": "1.6.0",
            "puzzle": {
                "name": "",
                "author": "",
                "type": "custom",
                "width": SIDE,
                "height": SIDE,
                "minDigit": 1,
                "maxDigit": 2,
                "cells": [{"value": 1 + c} for c in candidate],
                "constraints": [],
            },
        }

    def describe_hit(self, record):
        return f"hit {record['cells']}"

    def render(self, candidate):
        canvas = GridCanvas(SIDE, SIDE, cell=20, margin=4)
        for i, cell in enumerate(candidate):
            if cell:
                canvas.shade_cell(i // SIDE, i % SIDE, (0, 0, 0))
        return canvas.image


def cli(*args, env=None):
    return run_cli(__file__, AS_FINDER, *args, env=env)


def seed_done(out):
    return [
        e["seed"]
        for e in read_jsonl(out / "progress.jsonl", missing_ok=True)
        if e.get("event") == "seed_done"
    ]


def kill_partway(out, min_done=5):
    proc = subprocess.Popen(
        [
            sys.executable,
            __file__,
            AS_FINDER,
            "--out",
            str(out),
            f"--seeds=0:{SEEDS}",
            "--workers",
            "1",
        ],
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


def links(out):
    d = out / "links"
    return {p.name: p.read_text() for p in d.iterdir()} if d.is_dir() else None


def main():
    hunt_args = (f"--seeds=0:{SEEDS}", "--workers", "1")
    with fake_mint(), tempfile.TemporaryDirectory() as tmp:
        ref = Path(tmp) / "ref"
        r = cli("--out", str(ref), *hunt_args)
        check(f"reference hunt exits 0 ({r.stderr[-300:]})", r.returncode == 0)
        ref_summary = cli("summary", str(ref))
        check("reference summary exits 0", ref_summary.returncode == 0)
        check("reference links exit 0", cli("links", str(ref)).returncode == 0)
        ref_links = links(ref)
        check("the reference hunt has verified hits", bool(ref_links))

        out = Path(tmp) / "hunt"
        kill_partway(out)
        check("the kill left a partial hunt", 0 < len(seed_done(out)) < SEEDS)

        # A kill can cut the last log line short; summary and links read
        # through it as the driver's own resume does.
        torn = Path(tmp) / "torn"
        shutil.copytree(out, torn)
        for name in ("progress.jsonl", "examples.jsonl"):
            with (torn / name).open("ab") as f:
                f.write(b'{"seed": 9')
        for label, d in (("killed", out), ("torn-tail", torn)):
            r = cli("summary", str(d))
            check(
                f"summary of a {label} hunt exits 0 ({r.stderr[-200:]})",
                r.returncode == 0 and "seeds" in r.stdout,
            )
            r = cli("links", str(d))
            check(
                f"links of a {label} hunt exits 0 ({r.stderr[-200:]})",
                r.returncode == 0,
            )
        check(
            "a torn tail changes neither summary nor links",
            cli("summary", str(torn)).stdout == cli("summary", str(out)).stdout
            and links(torn) == links(out),
        )
        killed_links = links(out)
        check(
            "the killed hunt's links are a subset of the reference's",
            killed_links.items() <= ref_links.items(),
        )

        r = cli("--out", str(out), *hunt_args)
        check(f"resume exits 0 ({r.stderr[-300:]})", r.returncode == 0)
        r = cli("summary", str(out))
        check(
            "the resumed summary equals the uninterrupted one",
            r.returncode == 0 and r.stdout == ref_summary.stdout,
        )
        check("resumed links exit 0", cli("links", str(out)).returncode == 0)
        check("the resumed links equal the uninterrupted ones", links(out) == ref_links)

        # render DIR draws each example's own picture.
        from PIL import Image

        r = cli("render", str(out))
        check(f"render exits 0 ({r.stderr[-300:]})", r.returncode == 0)
        examples = read_jsonl(out / "examples.jsonl")
        seeds = sorted(
            e["seed"]
            for e in read_jsonl(out / "progress.jsonl")
            if e.get("outcome") == "example"
        )
        check(
            "renders/ holds one picture per example",
            sorted(p.name for p in (out / "renders").iterdir())
            == sorted(f"{s}.png" for s in seeds)
            and len(seeds) == len(examples) > 1,
        )
        finder = E2EFinder()
        own = True
        for seed, record in zip(seeds, examples, strict=True):
            want = finder.render(finder.candidate_from_record(record))
            with Image.open(out / "renders" / f"{seed}.png") as img:
                own = (
                    own
                    and img.convert("RGB").tobytes() == want.convert("RGB").tobytes()
                )
        check("each picture is its own example's drawing", own)
        check(
            "the examples are not all the same picture",
            len({tuple(e["cells"]) for e in examples}) > 1,
        )

        # A locked directory refuses every post-pass and changes nothing.
        before = links(out)
        lock = os.open(out / ".lock", os.O_RDWR)
        fcntl.flock(lock, fcntl.LOCK_EX)
        try:
            for command in ("render", "links"):
                r = cli(command, str(out))
                check_refusal(f"a locked directory refuses {command}", r, "is locked")
        finally:
            os.close(lock)
        check("and links/ is untouched", links(out) == before)

    finish()


if __name__ == "__main__":
    if AS_FINDER in sys.argv:
        argv = [a for a in sys.argv[1:] if a != AS_FINDER]
        sys.exit(run(E2EFinder(), argv))
    sys.exit(main())
