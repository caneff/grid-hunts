"""`summary DIR`, `links DIR` and the finish hook of the shared driver (#121).

Black-box on `toy_summary_finder.py`: the seed span, outcome counts and hits
`summary DIR` prints are checked against progress.jsonl, the link files
`links DIR` writes against the verified hits, and the finish hook's mark
against a completed hunt and a SIGKILLed one.

    uv run finders/hunt/test_summary_links.py
"""

import fcntl
import os
import signal
import subprocess
import sys
import tempfile
import time
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import short_link
import toy_summary_finder
from cli_checks import check, check_refusal, finish, read_jsonl, run_cli
from subprocess_env import pin_idle_load, success_env

pin_idle_load()

HERE = Path(__file__).resolve().parent
TOY = HERE / "toy_summary_finder.py"
PLAIN = HERE / "toy_finder.py"
EMPTY = {"TOY_EMPTY": "timeout:2,infeasible:4"}

with tempfile.TemporaryDirectory() as tmp, short_link.fake_mint() as fake:
    out = Path(tmp) / "hunt"
    hunt = run_cli(TOY, "--out", out, "--seeds", "0:12", env=EMPTY)
    check(f"the hunt completes (stderr: {hunt.stderr[-200:]})", hunt.returncode == 0)

    events = read_jsonl(out / "progress.jsonl")
    outcome = Counter(e["outcome"] for e in events)
    check("the scripted empties ran", outcome["empty"] == 2)

    # summary: span, counts, hits
    result = run_cli(TOY, "summary", out)
    check(f"summary exits 0 (stderr: {result.stderr[-200:]})", result.returncode == 0)
    text = result.stdout
    check("summary names the seed span", "12 seeds (0..11)" in text)
    check(
        "summary counts found, empty, timed out, duplicate and rejected",
        f"found {outcome['example']}, empty 1, timed out 1, "
        f"duplicate {outcome['duplicate']}, rejected {outcome['rejected']}" in text,
    )
    examples = read_jsonl(out / "examples.jsonl")
    check("the hunt has hits to report", len(examples) >= 2)
    for record in examples:
        check(
            f"summary lists the hit {record['grid']} in the finder's wording",
            f"hit, {sum(record['grid'])} shaded: {record['grid']}" in text,
        )
    check("summary lists exactly the hits", text.count("hit, ") == len(examples))

    # links: one file per verified hit, minted from the finder's document
    stale = out / "links" / "stale.txt"
    stale.parent.mkdir()
    stale.write_text("old\n")
    result = run_cli(TOY, "links", out)
    check(f"links exits 0 (stderr: {result.stderr[-200:]})", result.returncode == 0)
    seeds = [e["seed"] for e in events if e["outcome"] == "example"]
    files = sorted(p.name for p in (out / "links").iterdir())
    check(
        f"links writes one file per hit and drops a stale one ({files})",
        files == sorted(f"{s}.txt" for s in seeds),
    )
    for seed, record in zip(seeds, examples, strict=True):
        link = (out / "links" / f"{seed}.txt").read_text().strip()
        check(
            f"seed {seed}'s link holds the toy's document",
            short_link.fake_doc(fake, link)
            == toy_summary_finder.link_doc(record["grid"]),
        )

    check(
        "links says how many it wrote",
        result.stdout.strip() == f"wrote {len(seeds)} links to {out / 'links'}",
    )

    # a finder that words its own summary replaces the driver's lines whole
    result = run_cli(TOY, "summary", out, env={"TOY_OWN_SUMMARY": "1"})
    check(
        f"a summary_lines hook words summary DIR ({result.stdout!r})",
        result.returncode == 0 and result.stdout == "own wording for hunt\n",
    )

    # a held lock refuses, and links/ stays as it was
    before = sorted(p.name for p in (out / "links").iterdir())
    lock = os.open(out / ".lock", os.O_RDWR)
    fcntl.flock(lock, fcntl.LOCK_EX)
    result = run_cli(TOY, "links", out)
    os.close(lock)
    check_refusal("links on a locked directory", result, "is locked")
    check(
        "a refused links changes nothing",
        sorted(p.name for p in (out / "links").iterdir()) == before,
    )

    # a --no-verify hunt has no verified hit: links writes none until `verify`
    raw = Path(tmp) / "raw"
    run_cli(TOY, "--out", raw, "--seeds", "0:12", "--no-verify")
    result = run_cli(TOY, "links", raw)
    check(
        "links on an unverified hunt writes no link",
        result.returncode == 0 and not list((raw / "links").iterdir()),
    )
    run_cli(TOY, "verify", raw)
    result = run_cli(TOY, "links", raw)
    check(
        "after verify, links writes the hits",
        result.returncode == 0 and len(list((raw / "links").iterdir())) >= 1,
    )

    # a finder with link_text: its own wording is written, nothing is minted,
    # and a refusal names the seed and leaves links/ as it was
    own = Path(tmp) / "own"
    run_cli(TOY, "--out", own, "--seeds", "0:12", env={**EMPTY, "TOY_LINK_TEXT": "1"})
    result = run_cli(TOY, "links", own, env={"TOY_LINK_TEXT": "1"})
    own_hits = read_jsonl(own / "examples.jsonl")
    check(
        f"link_text links exits 0 (stderr: {result.stderr[-200:]})",
        result.returncode == 0,
    )
    check(
        "links writes the finder's own text for each hit, no minted link",
        all(
            (own / "links" / f"{e['seed']}.txt").read_text()
            == "own-link:" + "".join(map(str, r["grid"])) + "\n"
            for e, r in zip(
                [
                    e
                    for e in read_jsonl(own / "progress.jsonl")
                    if e["outcome"] == "example"
                ],
                own_hits,
                strict=True,
            )
        ),
    )
    full = Path(tmp) / "full"
    full.mkdir()
    (full / "run.json").write_text((own / "run.json").read_text())
    (full / "examples.jsonl").write_text(
        '{"grid": [1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1]}\n'
    )
    (full / "progress.jsonl").write_text('{"seed": 5, "outcome": "example"}\n')
    check_refusal(
        "a link_text refusal names the seed",
        run_cli(TOY, "links", full, env={"TOY_LINK_TEXT": "1"}),
        "seed 5: every cell shaded",
    )

    # refusals
    check_refusal(
        "summary on a directory with no hunt",
        run_cli(TOY, "summary", tmp),
        "no run.json",
    )
    result = run_cli(PLAIN, "links", out)
    check_refusal("a finder without link_document", result, "link_document")
    plain = Path(tmp) / "plain"
    run_cli(PLAIN, "--out", plain, "--seeds", "0:4")
    result = run_cli(PLAIN, "summary", plain)
    check(
        "a finder without describe_hit still summarises",
        result.returncode == 0 and "4 seeds (0..3)" in result.stdout,
    )

    # finish hook: marks a completed hunt, not a killed one
    check("a completed hunt is marked", (out / "finished.txt").exists())
    check(
        "a plain finder without the hook is unmarked",
        not (plain / "finished.txt").exists(),
    )
    killed = Path(tmp) / "killed"
    proc = subprocess.Popen(
        [sys.executable, str(TOY), "--out", str(killed), "--seeds", "0:6"],
        env=success_env({"TOY_STALL_CALL": "3"}),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    deadline = time.time() + 30
    while time.time() < deadline and (
        not (killed / "progress.jsonl").exists()
        or len(read_jsonl(killed / "progress.jsonl")) < 2
    ):
        time.sleep(0.05)
    proc.send_signal(signal.SIGKILL)
    proc.wait()
    check(
        "the killed hunt got seeds in", len(read_jsonl(killed / "progress.jsonl")) >= 2
    )
    check("a killed hunt is not marked", not (killed / "finished.txt").exists())
    resumed = run_cli(TOY, "--out", killed, "--seeds", "0:6")
    check("the resume completes", resumed.returncode == 0)
    check("the resumed, completed hunt is marked", (killed / "finished.txt").exists())

finish()
