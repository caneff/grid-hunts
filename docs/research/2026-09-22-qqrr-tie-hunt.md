# QQRR: no opener completion holds a 7-digit tie between interior cells that see each other

**Question (map #591, ticket #601, ruled at #594):** does any completion of the
opener hold two interior cells that see each other (row, column or box) whose
cell numbers are equal and exactly 7 digits long, built from different
window-rank lists (the one-digit rank in a different slot, e.g.
`1|23|45|67 = 12|3|45|67`)?

**Answer: no, at either surviving corner.** Every run below ended in a CP-SAT
infeasibility proof over the full space under its fixings, not a timeout.

**Model.** `model.add_seeing_tie` (#601) on the opener model: one pair literal
per unordered pair of interior cells that see each other (344 pairs), each
enforcing equal numbers, three of four window ranks two digits wide on both
sides, and the one-digit rank in a different slot; at least one pair true.
Run through `finders/qqrr/qqrr_cpsat.py --tie --count 2 --workers 8
--timeout 1800`. The first two rows ran at `f7a85a5`, check 2 at `8755429`;
the constraint posted is the same at both (`8755429` changed reporting and
tests, and made `sees` read the box size from n, which is 3 at 9x9).

| run | fixings | tr | br |
|---|---|---|---|
| the ticket's run | opener clues + 13 entered digits + marks 9, 8, 1 (`--hypotheses`) | infeasible, 33.8 s | infeasible, 60.3 s |
| check 1 (Chris, beyond the stop rule) | as above, leading-digit bound removed | infeasible, 203.6 s | infeasible, 292.6 s |
| check 2 (Chris, beyond the stop rule) | opener clues only; digits and marks as hints | infeasible, 106.1 s | infeasible, 163.9 s |

Opener clues in every run: QR 10 at the window with top-left r6c6, QQRR 33 at
r1c5, QR band 51..56 at r2c5's window, QR band 58+ at r4c4's window, and
QQRR 5 pinned at the named corner.

**The two checks go past the ticket.** The ticket's stop rule ("if both corners
are infeasible, stop") was met by the first row. Chris then asked how far the
result could be trusted and ruled both checks:

- *Check 1* removes the leading-digit bound (the window-rank band posted from
  each window's top-left digit, and the clued windows' digit pre-prune), the one
  pruning rule in the model whose soundness rests on a separate argument
  (map #321, #324). Run from a scratch copy of `model.py` and `checker.py`
  with only those lines deleted. Same verdict, 5 to 6x slower: the bound is not what
  makes the tie infeasible.
- *Check 2* drops the entered digits and the uncircled marks, which Chris had
  called forced. Same verdict at both corners: the tie is ruled out by the
  opener's clues and the corner pin alone.

**Not a vacuous proof.** 7-digit interior numbers are common in opener
completions: the 14 completions preset in
`docs/research/2026-09-22-qqrr-explorer.html` carry 14 to 16 each, never two
equal. The infeasibility comes from the equality, not from 7-digit numbers
being impossible. On a grid with no clues, the same constraint finds a tie in
about 20 s (`grids.TIE_WITNESS`: r4c6 `2|25|12|46` = r5c4 `22|51|24|6` =
2251246, same box); that grid is a test fixture, not an opener completion.

**What the verdict rests on.** The model's window ranks, cell numbers and cell
ranks agree with the independent oracle (`oracle.py`) on every fixed grid the
tests pin and on every grid a run has returned; that is agreement on the grids
seen, not a proof of the encoding. The tie constraint's parts are each
witnessed by a test that goes red when the part is removed.

**Open for Chris:** the ticket's flag for a tie "touching the r1c5 cage" was
read as a tied cell sharing a 2x2 window with the cage cell (r2c4, r2c5,
r2c6). No tie was found, so the flag never fired.

No grid was found, so the explorer gains no preset.
