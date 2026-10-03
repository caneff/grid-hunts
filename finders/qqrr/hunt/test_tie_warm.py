"""The tie finder's warm start (#643): each solve is hinted from the nearest known
grid, read from hunt output directories given as `--warm-from`.

Seams: TieFinder.warm_hits (the order and the forbidden filter), chan_big.build
(the hint the model carries), and the CLI's run.json (which grid it warm-started from).
One CP-SAT worker, a 1 s cap; a few seconds in all.

    uv run finders/qqrr/hunt/test_tie_warm.py
"""

import json
import random
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[2] / "finders" / "hunt"))
import hunt_common as hc

# isort: split
import chan_big
import tie_finder
from subprocess_env import success_env

# Found by chan_big.py in the 34-36 hunt (docs/research/2026-09-22-qqrr-tie-r5c1.md).
G_SAME = "436781529/978265134/125394876/217839465/354176982/689452713/763948251/591627348/842513697"  # passes q34
G_CORNER = "654781392/987234516/123956847/218679453/539842761/476513928/745168239/391427685/862395174"  # passes q34
G_WINDOW = "465781329/987432651/123965874/218574936/354196782/679328415/591847263/732659148/846213597"  # no 34-36 cell
G_FAR = "563781429/987425136/124396875/218537964/745169283/396842517/439278651/652913748/871654392"  # passes q34
SEED = hc.HUNTS["r1c5"][2]

ok = True


def check(name, cond):
    global ok
    if not cond:
        ok = False
    print(f"{'ok' if cond else 'FAIL'}: {name}")


def rec(grid, ten, corner, hunt="r1c5"):
    return {"grid": grid, "hunt": hunt, "ten": ten, "corner": corner, "q34": True}


def source(root, name, records):
    d = Path(root) / name
    d.mkdir()
    (d / "examples.jsonl").write_text("".join(json.dumps(r) + "\n" for r in records))
    return str(d)


with tempfile.TemporaryDirectory() as tmp:
    a = source(
        tmp,
        "a",
        [
            rec(G_FAR, "r6c6", "bl"),
            rec(G_WINDOW, "r7c7", "bl"),
            rec(G_CORNER, "r1c1", "tr"),
            rec(G_SAME, "r7c7", "tr"),
            rec(SEED, "r7c7", "tr", hunt="r5c1"),
        ],
    )
    # a second directory is read too
    b = source(tmp, "b", [rec(G_FAR, "r6c6", "bl")])

    f = tie_finder.TieFinder("r1c5", "r7c7", "tr", 1, True, [a, b])
    got = [h[2] for h in f.warm_hits()]
    check("a grid of another hunt is never a hint", SEED not in got)
    check("the same window and corner comes first", got[0] == G_SAME)
    check(
        "the grid that fails the criterion comes after every passing one",
        got[-1] == G_WINDOW,
    )
    check(
        "then nearer before farther among those that pass",
        got == [G_SAME, G_CORNER, G_FAR, G_FAR, G_WINDOW],
    )

    f.found.append(G_SAME.replace("/", ""))
    got = [h[2] for h in f.warm_hits()]
    check("a grid the run forbids is never the hint", G_SAME not in got)
    check("the next nearest takes its place", got[0] == G_CORNER)

    # propose hands the model the hits, never a forbidden one (a stub build stops the solve)
    class Built(Exception):
        pass

    def proposed_hits(finder):
        def stub(hunt, ten, corner, flags, hits=None):
            raise Built(flags, hits)

        real, chan_big.build = chan_big.build, stub
        try:
            finder.propose(random.Random(0))
        except Built as e:
            return e.args
        finally:
            chan_big.build = real

    g = tie_finder.TieFinder("r1c5", "r7c7", "tr", 1, True, [a])
    flags, hits = proposed_hits(g)
    check("propose asks build to warm-start", "warm" in flags)
    check("propose passes the nearest grid first", hits[0][2] == G_SAME)
    g.found.append(G_SAME.replace("/", ""))
    flags, hits = proposed_hits(g)
    check(
        "after a find, propose passes no grid the run forbids",
        G_SAME not in [h[2] for h in hits],
    )
    flags, hits = proposed_hits(tie_finder.TieFinder("r1c5", "r7c7", "tr", 1, True))
    check(
        "without --warm-from, propose asks for no warm start",
        "warm" not in flags and hits is None,
    )

    q, warm_from, _ = chan_big.build(
        "r1c5",
        "r7c7",
        "tr",
        {"tables", "hint", "warm", "criteria=q34"},
        hits=f.warm_hits(),
    )
    check("build's warm_from is the first hit it was given", warm_from[2] == G_CORNER)
    hinted = dict(
        zip(
            q.m.Proto().solution_hint.vars,
            q.m.Proto().solution_hint.values,
            strict=True,
        )
    )
    want = {
        q.x[r][c].Index(): int(d)
        for r, row in enumerate(G_CORNER.split("/"))
        for c, d in enumerate(row)
    }
    check(
        "the model's hint is that grid",
        all(hinted.get(i) == d for i, d in want.items()),
    )

    q, warm_from, _ = chan_big.build("r1c5", "r7c7", "tr", {"tables", "hint"})
    check("without warm hits build reports no warm start", warm_from is None)
    seed_hint = dict(
        zip(
            q.m.Proto().solution_hint.vars,
            q.m.Proto().solution_hint.values,
            strict=True,
        )
    )
    check(
        "... and the hint is the hunt's seed grid",
        all(
            seed_hint.get(q.x[r][c].Index()) == int(d)
            for r, row in enumerate(SEED.split("/"))
            for c, d in enumerate(row)
        ),
    )

    f = tie_finder.TieFinder("r1c5", "r7c7", "tr", 1, True, [a])
    cand = tie_finder.Candidate(
        tuple(int(d) for d in G_SAME if d != "/"), "r1c5", "r7c7", "tr", True, G_CORNER
    )
    saved = f.record(cand)
    check(
        "an example records the grid its solve was hinted with",
        saved["warm"] == G_CORNER,
    )
    check("... and reads it back", f.candidate_from_record(saved).warm == G_CORNER)
    check(
        "config names the sources and the starting grid",
        {k: v for k, v in f.config["warm_from"].items() if k != "order"}
        == {"dirs": [a], "grid": G_SAME, "ten": "r7c7", "corner": "tr"},
    )
    check(
        "without a source the config has no warm_from key",
        "warm_from" not in tie_finder.TieFinder("r1c5", "r7c7", "tr", 1, True).config,
    )

    def cli(*args):
        return subprocess.run(
            [sys.executable, str(HERE / "tie_finder.py"), *args],
            capture_output=True,
            text=True,
            env=success_env(),
        )

    base = [
        "--seeds=0:1",
        "--workers",
        "1",
        "--hunt",
        "r1c5",
        "--ten",
        "r7c7",
        "--corner",
        "tr",
        "--timeout",
        "1",
        "--q34",
    ]
    out = Path(tmp) / "hunt"
    r = cli("--out", str(out), *base, "--warm-from", a, b)
    check("a warm hunt exits 0", r.returncode == 0)
    cfg = json.loads((out / "run.json").read_text())["config"]
    check(
        "run.json records the grid it warm-started from",
        cfg["warm_from"]["grid"] == G_SAME,
    )

    out2 = Path(tmp) / "plain"
    cli("--out", str(out2), *base)
    check(
        "without --warm-from, run.json has no warm_from",
        "warm_from" not in json.loads((out2 / "run.json").read_text())["config"],
    )

    empty = source(tmp, "empty", [rec(G_SAME, "r7c7", "tr", hunt="r5c1")])
    r = cli("--out", str(Path(tmp) / "none"), *base, "--warm-from", empty)
    check("a source with no grid for this hunt refuses (exit 2)", r.returncode == 2)
    check("... saying it holds no r1c5 grid", "holds no r1c5 grid" in r.stderr)
    r = cli(
        "--out",
        str(Path(tmp) / "gone"),
        *base,
        "--warm-from",
        str(Path(tmp) / "missing"),
    )
    check("a source that is not a hunt directory refuses (exit 2)", r.returncode == 2)
    check("... saying it has no examples.jsonl", "has no examples.jsonl" in r.stderr)

sys.exit(0 if ok else 1)
