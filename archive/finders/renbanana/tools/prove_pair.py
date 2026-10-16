"""Prove or refute: can any Renbanana grid hold two circled 2x2/2x3 rectangles?

Everything so far has been per-grid. 30,140 sampled grids came back INFEASIBLE
and 826 of the 3,308 pair geometries admit no digits at all, but a sample of
grids cannot say the pair is impossible -- only that we did not find one.

This asks the question once per geometry, over *all* grids and *all* shadings
at the same time. The pipeline has never done a joint search (renbanana_cpsat's
docstring says so outright: "never a joint shading+digit search"), because the
free version is enormous. Pinning a geometry is what makes it tractable: ten to
twelve cells are chocolate before the solver starts, their twenty-odd border
cells are banana, and the whisper inside both rectangles is fixed.

Only the 2,482 geometries a sudoku can carry are worth asking. The other 826
are already proved impossible at the digit level, and a superset of an
impossible constraint set is impossible.

What is exact here and what is lazy:

- Chocolate groups are rectangles: exact, via stage 1's lemma -- connected plus
  no 2x2 window holding exactly three of a colour means every group is a
  rectangle. So rule 3 alone carries it.
- Banana size cap: exact, structurally, on component labels.
- Whisper: exact -- two adjacent chocolate cells differ by 5 or more.
- Renban: a filter, and this is the expensive half. Per label, the member
  digits are distinct and span a run: max - min == size - 1. It cannot be lazy
  the way rule 4 is, because a component shape that is illegal with one set of
  digits is legal with another, so a shape-level cut would be unsound. Two
  disjoint banana components may still share a label (`banana_labels`), so a
  hit can break renban; `rv.check` re-checks every hit and `violations` says so.
- Banana non-rectangle: exact, up front -- one clause per rectangle placement
  forbidding it as a maximal banana group. A rectangular banana group is
  illegal whatever its digits. `solve` still cuts any rectangular group a
  solution shows, as a guard.

Everything above is exact or a relaxation, so an INFEASIBLE is a proof for that
geometry.

    uv run --with ortools finders/renbanana/tools/prove_pair.py \
        --procs 20 --seconds 120 --limit 50 --out docs/research/renbanana/pair-proof
"""

import argparse
import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from ortools.sat.python import cp_model as cp

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import canon
import renbanana_cpsat as rc
import renbanana_model as rm
import renbanana_verify as rv
from renbanana_model import ADJACENT, CELLS, IDX, MAX_BANANA, N


class JointPair:
    """Digits and shading together, with one pair of circled rectangles pinned."""

    def __init__(self, pair, pin_labels=True, renban=True):
        m = cp.CpModel()
        self.m = m
        self.pair = pair
        self.cuts = 0

        d = {p: m.new_int_var(1, 9, f"d{p}") for p in CELLS}
        self.d = d
        choc = {p: m.new_bool_var(f"c{p}") for p in CELLS}
        self.choc = choc

        rm.sudoku(m, d)
        rm.rectangle_lemma(m, choc)  # with connectivity, the whole rectangle rule

        # The pinned pair: chocolate inside, banana all round, so each is a
        # maximal group, and its own size on a cell the catalogue allows.
        for a, b, r0, c0 in pair:
            m.add_bool_and(rm.maximal_chocolate_lits(choc, a, b, r0, c0))
            # The catalogue's per-cell digit domains for this shape at this
            # box offset. Layer B -- the rectangle plus the boxes -- so a real
            # grid only narrows them and handing them over is sound. It is the
            # difference between the solver searching out the fillings and
            # reading the enumeration off disk.
            sup = rc.support_at(a, b, r0 % 3, c0 % 3)
            if sup is not None and len(sup) == a and len(sup[0]) == b:
                for i in range(a):
                    for j in range(b):
                        m.add_allowed_assignments(
                            [d[r0 + i, c0 + j]], [(v,) for v in sorted(sup[i][j])]
                        )
            sites = [
                (r0 + i, c0 + j) for i, j in rc.circle_cells_at(a, b, r0 % 3, c0 % 3)
            ]
            got = []
            for p in sites:
                v = m.new_bool_var(f"circ{p}")
                m.add(d[p] == a * b).only_enforce_if(v)
                got.append(v)
            m.add(sum(got) >= 1)

        rm.whisper(m, d, choc)

        # Rule 6 is the whole cost of this model: a label bool per cell pair,
        # a digit indicator per cell, and a product var per member per digit.
        # Dropping it leaves the digits free of renban, which the recycler then
        # settles exactly on fixed digits in a second or two -- generate
        # loosely, verify exactly.
        if renban:
            lab = rm.banana_labels(m, choc, pin=pin_labels)
            self.lab = lab

            # Renban per label: distinct digits spanning exactly their own count.
            # max - min == size - 1 with all members distinct is precisely "a set of
            # consecutive digits", which is the rule.
            eq = {
                (p, v): m.new_bool_var(f"e{p}_{v}") for p in CELLS for v in range(1, 10)
            }
            for p in CELLS:
                m.add_exactly_one([eq[p, v] for v in range(1, 10)])
                for v in range(1, 10):
                    m.add(d[p] == v).only_enforce_if(eq[p, v])
                    m.add(d[p] != v).only_enforce_if(eq[p, v].negated())
            for ell in range(len(CELLS)):
                members = [p for p in CELLS if IDX[p] >= ell]
                size = m.new_int_var(0, MAX_BANANA, f"n{ell}")
                m.add(size == sum(lab[p, ell] for p in members))
                lo = m.new_int_var(1, 9, f"lo{ell}")
                hi = m.new_int_var(1, 9, f"hi{ell}")
                for p in members:
                    m.add(d[p] >= lo).only_enforce_if(lab[p, ell])
                    m.add(d[p] <= hi).only_enforce_if(lab[p, ell])
                # Empty labels are free; a used one spans exactly its own size.
                used = m.new_bool_var(f"u{ell}")
                m.add(size >= 1).only_enforce_if(used)
                m.add(size == 0).only_enforce_if(used.negated())
                m.add(hi - lo == size - 1).only_enforce_if(used)
                for v in range(1, 10):
                    m.add(
                        sum(
                            self._both(m, lab[p, ell], eq[p, v], f"b{ell}_{v}_{IDX[p]}")
                            for p in members
                        )
                        <= 1
                    )
        # Rule 4 outright, up front: a cut per solution would cost a full
        # joint solve each.
        rm.forbid_banana_rectangles(m, choc)
        self._forbid_dead_chocolate()
        self._fives_are_lonely()

    def _forbid_dead_chocolate(self):
        """No maximal chocolate rectangle the catalogue says cannot be filled.

        A shape with no filling anywhere (2x8, 4x5, 7x7 and the rest) or none
        at this box offset (3x3 at (0,0), 4x4 at eight of nine) appears in no
        grid, so the solver should never be free to propose one.
        """
        self.dead = rm.forbid_dead_chocolate(
            self.m,
            self.choc,
            lambda a, b, r0, c0: (
                max(a, b) > 8 or not rc.fillings_at(a, b, r0 % 3, c0 % 3)
            ),
        )

    def _fives_are_lonely(self):
        """No chocolate cell with a chocolate neighbour holds a 5.

        A chocolate neighbour d of a 5 needs |5 - d| >= 5, so d <= 0 or d >= 10.
        Stage 1 can only assert that some legal placement of the nine 5s exists,
        having no digits; here the digits are present and the fact goes in
        directly, pair by pair.
        """
        for p, q in ADJACENT:
            self.m.add(self.d[p] != 5).only_enforce_if([self.choc[p], self.choc[q]])
            self.m.add(self.d[q] != 5).only_enforce_if([self.choc[p], self.choc[q]])

    @staticmethod
    def _both(m, x, y, name):
        z = m.new_bool_var(name)
        m.add_bool_or([x.negated(), y.negated(), z])
        m.add_implication(z, x)
        m.add_implication(z, y)
        return z

    def forbid_component(self, group):
        rm.forbid_banana_group(self.m, self.choc, group)
        self.cuts += 1

    def solve(self, seconds, workers, seed):
        deadline = time.monotonic() + seconds
        while True:
            left = deadline - time.monotonic()
            if left <= 0:
                return "unknown", None, None
            s = cp.CpSolver()
            s.parameters.max_time_in_seconds = left
            s.parameters.num_workers = workers
            s.parameters.random_seed = seed
            status = s.solve(self.m)
            if status == cp.INFEASIBLE:
                return "infeasible", None, None
            if status not in (cp.OPTIMAL, cp.FEASIBLE):
                return "unknown", None, None
            is_choc = {p: s.value(self.choc[p]) == 1 for p in CELLS}
            grid = {p: s.value(self.d[p]) for p in CELLS}
            bad = [g for g in rv.components(is_choc, False) if rv.is_rectangle(g)]
            if not bad:
                return "hit", grid, is_choc
            for g in bad:
                self.forbid_component(g)


def _key(pair):
    """A geometry as a hashable, however it arrived -- JSON gives lists."""
    return tuple(tuple(x) for x in pair)


def work(job):
    """One geometry, one seed.

    The seed is the whole point of a second pass. CP-SAT's search is
    randomised, and the 600-second test showed a geometry that resists one
    search resists it all the way down -- so an unknown is re-attacked with a
    different seed rather than a longer clock. A job that omits the seed gets
    0, which is what every run before this one used.
    """
    pair, seconds, pin_labels, seed, renban = (*job, True)[:5] if len(job) < 5 else job
    pair = [tuple(x) for x in pair]
    model = JointPair(pair, pin_labels=pin_labels, renban=renban)
    t0 = time.monotonic()
    verdict, grid, is_choc = model.solve(seconds, 1, seed)
    row = {
        "pair": pair,
        "verdict": verdict,
        "seed": seed,
        "renban": renban,
        "seconds": round(time.monotonic() - t0, 1),
        "cuts": model.cuts,
    }
    if grid is not None:
        row["grid"] = ["".join(str(grid[r, c]) for c in range(N)) for r in range(N)]
        row["shading"] = [
            "".join("C" if is_choc[r, c] else "b" for c in range(N)) for r in range(N)
        ]
        row["violations"] = rv.check(grid, is_choc)[:5]
    return row


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--procs", type=int, default=20)
    ap.add_argument("--seconds", type=float, default=120.0)
    ap.add_argument("--limit", type=int, default=0, help="0 means every geometry")
    ap.add_argument(
        "--no-pin-labels",
        action="store_true",
        help="drop the owner-cell label clause. It does not close the "
        "shared-label hole either way; this is here to measure which model "
        "harvests more verified grids per hour.",
    )
    ap.add_argument(
        "--seed",
        type=int,
        default=0,
        help="CP-SAT random seed. A second pass over the leftovers uses a "
        "different one; the same one repeats the same search exactly.",
    )
    ap.add_argument(
        "--only-unknown-from",
        type=Path,
        default=None,
        help="a proof.jsonl from an earlier pass. Only geometries it left "
        "unknown are attempted, so a re-seeded pass never re-proves a "
        "settled one.",
    )
    ap.add_argument(
        "--drop-renban",
        action="store_true",
        help="leave rule 6 out of the joint model and let recycle_hits settle "
        "it on the fixed digits afterwards -- generate loosely, verify "
        "exactly. Dropping a rule is a relaxation, so an INFEASIBLE verdict "
        "is still a proof; only a hit becomes weaker.",
    )
    ap.add_argument(
        "--canonical",
        action="store_true",
        help="one geometry per dihedral orbit. Legality is invariant under "
        "the group, so the seven others in an orbit have a legal grid exactly "
        "when the representative does -- 2,482 geometries become 320.",
    )
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)

    # Only the geometries a sudoku can carry: the rest are already proved.
    feasible = [
        r["pair"]
        for r in (
            json.loads(line)
            for line in (Path("docs/research/renbanana/circled-pairs-all/pairs.jsonl"))
            .read_text()
            .splitlines()
            if line.strip()
        )
        if r["grid"] is not None
    ]
    if a.only_unknown_from:
        prior = [
            json.loads(line)
            for line in a.only_unknown_from.read_text().splitlines()
            if line.strip()
        ]
        settled = {
            _key(r["pair"]) for r in prior if r["verdict"] in ("infeasible", "hit")
        }
        before = len(feasible)
        feasible = [p for p in feasible if _key(p) not in settled]
        print(
            f"{before - len(feasible)} geometries already settled by "
            f"{a.only_unknown_from}; {len(feasible)} left",
            flush=True,
        )
    if a.canonical:
        by_orbit = {}
        for p in feasible:
            by_orbit.setdefault(canon.geometry_key([tuple(x) for x in p]), p)
        print(
            f"{len(feasible)} geometries collapse to {len(by_orbit)} orbits",
            flush=True,
        )
        feasible = list(by_orbit.values())
    if a.limit:
        feasible = feasible[: a.limit]
    print(f"{len(feasible)} geometries a sudoku can carry; proving each", flush=True)

    log = a.out / "proof.jsonl"
    tally = {}
    began = time.monotonic()
    with ProcessPoolExecutor(max_workers=a.procs) as pool:
        for done, row in enumerate(
            pool.map(
                work,
                [
                    (p, a.seconds, not a.no_pin_labels, a.seed, not a.drop_renban)
                    for p in feasible
                ],
                chunksize=1,
            ),
            1,
        ):
            tally[row["verdict"]] = tally.get(row["verdict"], 0) + 1
            with log.open("a") as f:
                f.write(json.dumps(row) + "\n")
            if row["verdict"] == "hit":
                print(f"HIT: {row['pair']} violations={row['violations']}", flush=True)
            if done % 10 == 0:
                print(
                    f"  {done}/{len(feasible)} in {time.monotonic() - began:.0f}s: {tally}",
                    flush=True,
                )
    (a.out / "stats.json").write_text(json.dumps(tally, indent=1) + "\n")
    print(
        f"\n{len(feasible)} geometries, {time.monotonic() - began:.0f}s: {tally}",
        flush=True,
    )


if __name__ == "__main__":
    main()
