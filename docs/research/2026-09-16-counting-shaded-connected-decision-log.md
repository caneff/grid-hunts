# Decision log: counting shaded, connected all-visible hunt (2026-09-16)

Every decision taken during the hunt, what it rested on, and what it cost.
Written because the same lessons keep being re-derived: **six of the errors
below were already covered by a written lesson in
`docs/agents/grid-finder-lessons.md` at the time they were made.** The gap is
not missing knowledge, it is that nothing forced a read before compute was
spent. The preflight section of that doc is the fix.

Format per entry: what was decided, the evidence it rested on, the outcome, and
whether a lesson already existed. "Caught by" records who noticed — several
were caught by Chris, not by me, which is the expensive kind.

---

## 1. Connectivity by lazy cuts

**Decided:** enforce orthogonal connectivity with lazy flood-fill cuts.
**Rested on:** a standing ruling from Chris to use lazy cuts (given for the
pinned-infeasibility question, carried over without rechecking that it applied).
**Outcome:** 2073 cuts in 120s, never returned a connected shape. Replaced with
single-commodity flow: connected shape in 77s.
**Lesson existed?** Partly — "cuts only pay when each cut kills a family rather
than one point" was already written. A component-layout cut kills one point.
**New lesson:** a ruling made for one question does not automatically transfer
to the next; re-ask whether its premise still holds.

## 2. Shape-only search for connected shapes

**Decided:** search shapes alone (`connected.py`), no grid variables.
**Rested on:** the written lesson "search the smallest object that determines
the puzzle", which was correct for the unconstrained hunt.
**Outcome:** returned connected shapes with admissible givens and **0 sudoku
solutions** — no grid completes them. The distinct-givens rule is necessary,
not sufficient.
**Lesson existed?** Yes, and it was the *other* lesson in the same file: "seed
local search from a joint feasibility model — a random shape is almost always
unsolvable." Two lessons pointed opposite ways and I followed the wrong one.
**New lesson:** when two written lessons conflict, the one about feasibility
wins; an unsolvable candidate is not a candidate.

## 3. Grid-first sampling (`gridfirst.py`)

**Decided:** fix a solved grid, then solve for the shaded cell set inside it.
**Rested on:** sound reasoning — admissibility becomes free and every hit is
solvable by construction, the grid being the witness.
**Outcome:** the idea is fine; the sampler was broken. `random_grid()` built
grids by relabelling, in-band row moves, band and stack swaps and transposition
of one `BASE` grid. Those are exactly the sudoku-preserving symmetries, so all
38,064 "random grids" were isomorphic — one equivalence class of 5.47 billion.
**Cost:** ~10 minutes of compute and a false conclusion (below).
**Lesson existed?** No.
**New lesson:** a sampler built from the puzzle's own symmetry group samples one
orbit, not the space. Validate a sampler by asking whether two outputs are
isomorphic, not whether they look different.

## 4. Concluding a size ceiling of 9 from that sampler

**Decided:** reported that connected all-visible sets max out around 9 cells and
that 98.7% of grids admit none.
**Rested on:** 38,064 samples — a large number that felt like evidence.
**Outcome:** artefact. The true ceiling is 26.
**Caught by:** Chris ("i think you are going about this the wrong way").
**New lesson:** sample size does not rescue a biased sampler. State what the
sampler covers before quoting a number from it.

## 5. Joint model with flow connectivity, maximizing shaded cell count

**Decided:** put digits, shaded cells, the all-visible link and connectivity in one
model and maximize.
**Outcome:** the best decision of the hunt. OPTIMAL at 26 shaded cells in 50s, and
the first shape it returned had 2 solutions — a near miss, which is what made
the band worth searching at all.

## 6. Pinning enumeration to the top of the size range

**Decided:** search only 26-cell shapes, because uniqueness wants more givens.
**Rested on:** intuition.
**Outcome:** wasted. 1 seed in 330s.
**Lesson existed?** **Yes, twice.** The written lesson "test a monotone
shortcut before betting on it" describes this exact hypothesis, and `dense.py`
had already falsified it in a 5-minute measurement: the densest shape, 35
shaded cells, had 8 solutions.
**Caught by:** the finder survey, after the compute was spent.

## 7. Enumeration instead of local search

**Decided:** enumerate the feasible set by solve-then-forbid.
**Rested on:** a belief that the connected feasible set was "tiny and isolated".
**Outcome:** wrong on both counts. The belief came from a broken measurement
(entry 8). Enumeration by one-point forbidding is the same whack-a-mole that
sank the lazy cuts.
**Lesson existed?** Yes — local search plus a bounded counter is what produced
all 234 previous examples, and both renbanana and zombo_brainanas had recorded
that random objective weights, not forbid-clauses, are what keep candidates
apart. Switching to random weights gave a 4x seed rate and real size diversity.
**Caught by:** Chris ("look at what our other finders have been successful
doing").

## 8. The neighbourhood-density measurement

**Decided:** measure whether local search can move, by counting feasible
single- and pair-toggle neighbours of a connected seed against disconnected
examples as a baseline.
**Outcome first pass:** baseline read 0/81 for every disconnected example,
apparently proving the connected region was uniquely sparse. **Broken:**
`givens()` hard-codes the connectivity check, so it rejects every neighbour of
a disconnected shape by construction.
**Outcome second pass:** connected 26-seed 1/81 single, 6/400 pair; disconnected
found examples 0-1/81 single, 3-10/400 pair. The connected region is **as
sparse as the one local search already conquered.** Local search was viable all
along.
**New lesson:** when a filter is applied globally inside a helper, a "control
with the constraint off" must make the helper switchable. A control that cannot
turn the thing off is not a control.

## 9. Claiming "no unique example below 25 shaded cells"

**Decided:** inferred a lower bound from the size distribution of the 234
verified examples (none below 25).
**Outcome:** false. `charvest.py` and `harvest.py` both default
`--min-shaded 26`, and `seed_shape` enforces `sum(g) >= min_shaded`. Every seed
that built the catalogue started at 26+. The absence was the floor I set.
**Caught by:** Chris ("you cant say that only 25 or 26 exists if you haven't
done more exhaustive smaller searches").
**New lesson:** a corpus inherits its generator's parameters. Never read a
distribution bound off a corpus without re-reading the flags that produced it.

## 10. The broken control

**Decided:** validate the 26 ceiling by re-running the maximize with
connectivity removed, expecting a higher number.
**Outcome:** printed "no connectivity: max=26", which I nearly read as
confirmation. `joint.build()` added flow connectivity internally regardless of
the flag I passed, so the control re-measured the constrained model.
**New lesson:** a control must be shown to change the model. If the control and
the treatment agree, first check the control did anything at all.

## 11. Calling 26 "proven"

**Decided:** reported the ceiling as proven on one model's OPTIMAL status.
**Outcome:** overstated. OPTIMAL proves a fact about the model, not about the
puzzle, and two encoding bugs had already shipped that same session.
**Caught by:** Chris ("so i still don't believe the 26 ceiling").
**Resolution:** rebuilt the question sharing nothing with the original —
one-hot booleans instead of integers under `add_all_different`, the link
enforced on the (shaded cell, digit) pair instead of an equality against a sum,
rooted spanning-tree connectivity instead of flow, with the tree encoding
verified 200/200 against flood fill. **`--exactly 27` returned INFEASIBLE in
579s.** Two independent proofs; the ceiling stands.
**New lesson:** OPTIMAL is a claim about the model. A ceiling that will bound
future search deserves a second encoding before it is called proven.

## 12. Misreading UNKNOWN as exhaustion

**Decided:** the harvester printed "seed supply exhausted" on any non-SAT
status.
**Outcome:** CP-SAT `UNKNOWN` is a timeout. Only `INFEASIBLE` proves a size
band empty. Fixed to distinguish them.
**New lesson:** never let a solver timeout print as a proof. This is the same
discipline `minimal.py` and `zombo_brainanas_cpsat.py` already apply when they
treat a timeout as "keep the clue".

## 13. Searching shaded cell counts below 17

**Decided:** launched four size bands, 6-11, 12-16, 17-21, 22-26.
**Outcome:** half the compute was spent where uniqueness is impossible — but
the reason needs stating carefully. The 17-givens minimum (McGuire, Tugemann &
Civario, 2012) holds for a board carrying digit givens **and nothing else**. A
board with any other clue type can be unique with far fewer, which is the usual
case in this repo. It applies here only because all-visible counting shaded reduces to
exactly that: the shaded cell rule is redundant once every shaded cell is visible, so the
board is a plain sudoku whose givens are the shaded cell digits.
**New lesson:** look up the base puzzle's known bounds before choosing a search
range, and check whether the variant's extra clue types void them. Borrowing
the bound without proving the reduction would have been the same error in the
opposite direction — ruling out a band that a constrained puzzle could reach.

## 14. Reasoning about why visibility matters

**Decided:** argued that all-visible makes the shaded cell rule redundant (correct),
and therefore that all-visible is the hardest variant and hidden shaded cells would
be easier to find examples for (wrong).
**Outcome:** backwards. A shaded cell marker only becomes a given digit if the shaded cell
status of its whole 3x3 is known, so under the original hidden-shaded rule a
visible shaded cell is a marker whose value the solver cannot compute — not a given
at all. All-visible is the *maximally* clued variant.
**Caught by:** Chris.
**New lesson:** separate the mechanism from the conclusion and check each. The
mechanism here was right and the conclusion drawn from it was inverted; stating
them as one claim hid that.

## 15. Naming a size window from sampled data, twice

**Decided:** reported the viable band as 25-26, then as 18-21.
**Rested on:** the first came from the 234-example catalogue (entry 9). The
second came from the corpus maximum of distinct digits per size -- 7 at 22, 6
at 23, 6 at 24 -- off twelve configurations at those sizes.
**Outcome:** both wrong. Asking the solver directly, one size at a time, took
seconds per size: 17 through 21 all have witnesses, 22 through 26 are all
INFEASIBLE. 17 is in and 22 is out, and neither guess had it.
**Caught by:** Chris, twice ("did you rule out 22-24?", then "fix your
reasoning").
**New lesson, and the important one in this file:** **when a solver can answer
the question directly, never report the answer from sampled data.** This is
distinct from the biased-generator lessons above -- the generator was fine, the
sample was simply not the question. A sample maximum is a fact about the sample.
The oracle was available and cheap the entire time.

## 16. An INFEASIBLE message that omitted its own constraints

**Decided:** printed "no connected all-visible configuration exists with 25-25
shaded cells" when the run also had `--all-digits` posted.
**Outcome:** flatly contradicts the four 25-cell configurations already in the
corpus. The result was right; the sentence was false.
**New lesson:** an INFEASIBLE is a claim about the model *as posted*. Print
every restriction in play, or the log will contradict the rest of the evidence
and nobody will know which to believe.

## 17. Misdiagnosing the solve budget

**Decided:** argued that the pinned runs were wasting their 300s budget proving
optimality, and recommended cutting it.
**Rested on:** all three sizes returning at exactly 300s, which does look like
budget exhaustion.
**Outcome:** backwards. A 20s budget found nothing in 240s of trying, and
`stop_after_first_solution` found nothing in 180s, while the 300s runs produced
steadily. These were **search-bound**: finding the first feasible configuration
takes nearly the whole budget at those sizes. Cutting it would have killed the
top-band corpus.
**Saved by:** running the probe instead of acting on the argument.
**New lesson:** "returns at exactly the budget" is consistent with both a wasted
proof and a search that only just finishes. The two are distinguished by a
probe, not by reasoning.

---

## What actually worked

- The joint model: digits and shape together, every candidate solvable by
  construction.
- Random objective weights for seed diversity, over solve-then-forbid.
- Flow (and tree) connectivity over lazy cuts.
- Every encoding checked against an independent implementation: flow vs flood
  fill 300/300, tree vs flood fill 200/200, C filter vs Python 20,000 shapes.
- Verifying the census with code that shares nothing with the model: 39
  configurations, 0 rejected.

## Scoreboard

- Ceiling: 26 connected all-visible shaded cells, two independent proofs.
- Floor for uniqueness: 17, by theorem.
- Connected configurations found (uniqueness aside): 39 and counting, sizes
  8-22, all verified.
- Connected *unique* examples: none yet.
