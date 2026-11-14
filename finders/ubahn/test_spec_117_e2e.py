"""Spec #117 at the `just check` seam, on the 4x4 board, through the commands
Chris runs: a killed `climb --out DIR` resumes past a torn last log line
(story 1), `--help` names `--exactly N:KIND:rK` and says it counts blanks
(story 2), `brute.py` and `hybrid_finder.py` refuse an off-board `--circles`
in the same words with exit 2, and `render DIR` and `links DIR` run on a hunt
directory the climb wrote.

WHAT A GREEN RUN DOES NOT COVER (AGENTS.md's Blind to): the slow tests
(`just test-slow`: the five slowest U-Bahn suites among them), a hunt's own
output (the 7x7 climb of record is made by hand), and how a found grid reads
once it is built into a puzzle link (the link is written, not opened).
The kill is a hand-cut log line, not a SIGKILL landing inside a write.

    uv run finders/ubahn/test_spec_117_e2e.py
"""

import shutil
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "hunt"))
from cli_checks import check, check_refusal, finish, read_jsonl, run_cli
from short_link import fake_mint

FINDER = HERE / "hybrid_finder.py"
BRUTE = HERE / "brute.py"
BOARD = ["--rows", "4", "--cols", "4", "--timeout", "20"]


def steps(out):
    """The climb's steps, the run log's heading left out, the time cleared."""
    return [{**s, "seconds": None} for s in read_jsonl(out / "climb.jsonl")[1:]]


def main():
    with fake_mint(), tempfile.TemporaryDirectory() as tmp:
        ref = Path(tmp) / "ref"
        r = run_cli(FINDER, "climb", *BOARD, "--out", ref)
        check(f"a reference climb exits 0 ({r.stderr[-300:]})", r.returncode == 0)
        ref_steps = steps(ref)
        check("the climb logged more than one step", len(ref_steps) > 1)

        # Story 1: a kill cuts the last log line short; the rerun drops it
        # and goes on, ending where the uninterrupted climb ended.
        torn = Path(tmp) / "torn"
        shutil.copytree(ref, torn)
        lines = (ref / "climb.jsonl").read_text().splitlines(keepends=True)
        (torn / "climb.jsonl").write_text("".join(lines[:2]) + '{"at_least": 3, "sta')
        shutil.rmtree(torn / ref_steps[1]["dir"])
        r = run_cli(FINDER, "climb", *BOARD, "--out", torn)
        check(
            f"climb after a log cut short mid-line exits 0 ({r.stderr[-300:]})",
            r.returncode == 0,
        )
        check(
            "and finishes with the uninterrupted climb's steps and its maximum",
            steps(torn) == ref_steps and "maximum" in r.stdout,
        )

        # Story 2: --help names the flag and says it counts blanks.
        r = run_cli(FINDER, "--help")
        flag = r.stdout.split("--exactly N:KIND:rK", 1)
        check(
            "--help names --exactly N:KIND:rK and its blank kind",
            r.returncode == 0 and len(flag) == 2 and "blank" in flag[1][:200],
        )

        # An off-board circle is refused alike, exit 2, by brute and finder.
        bad = "r9c9"
        said = {}
        for name, r in (
            ("brute.py", run_cli(BRUTE, 4, 4, "--circles", bad)),
            (
                "hybrid_finder.py",
                run_cli(FINDER, "classify", *BOARD, "--circles", bad),
            ),
        ):
            check_refusal(f"{name} refuses an off-board circle", r, "r9c9 is off the")
            said[name] = r.stderr.strip().splitlines()[-1].split("--circles", 1)[-1]
        check(
            f"in the same words ({said})",
            said["brute.py"] == said["hybrid_finder.py"] and "r9c9" in said["brute.py"],
        )

        # render DIR and links DIR run on a hunt directory the climb wrote.
        hunt = ref / ref_steps[0]["dir"]
        r = run_cli(FINDER, "render", hunt)
        check(f"render exits 0 ({r.stderr[-300:]})", r.returncode == 0)
        check(
            "and draws the example",
            (hunt / "renders" / "0.png").stat().st_size > 0,
        )
        r = run_cli(FINDER, "links", hunt)
        check(f"links exits 0 ({r.stderr[-300:]})", r.returncode == 0)
        check(
            "and writes the example's link",
            (hunt / "links" / "0.txt").read_text().strip() != "",
        )

    finish()


if __name__ == "__main__":
    main()
