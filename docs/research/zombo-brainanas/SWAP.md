# Why the role swap is infeasible

Swap = uninfected groups must be rectangles, infected groups must not be.
CP-SAT proves it infeasible in presolve. Ablation (2026-09-07, tools not kept;
the build source was patched in-memory with flags):

| relaxed rule | swap |
|---|---|
| none | INFEASIBLE |
| one patient zero per row (columns only) | feasible |
| one patient zero per column (rows only) | INFEASIBLE |
| drop any single row's rule, or rows 1-3 | INFEASIBLE |
| uninfected groups are rectangles | feasible |
| infected groups are not rectangles | INFEASIBLE |

So the conflict is exactly: row rule + "uninfected groups are rectangles".
The banana side and the column rule play no part.

Mechanism (digit height lemma). An infected cell is a patient zero or has an
infected neighbour with a larger digit. The only infected 9 is box 9's, rows
7-9. So an infected 8 is in rows 6-9, an infected 7 in rows 5-9, ..., an
infected digit d is in rows >= d-2. Turned round: row r can only hold infected
digits <= r+2. Row 1 holds at most three infected cells (its 1, 2, 3), row 2 at
most four, row 3 at most five.

With the row rule, rows 1-3 hold exactly the patient zeros 1, 2, 3, one per
row, so row 1 has an infected cell and at least six uninfected ones. Under the
swap those six lie in rectangles whose entire bottom edges and side columns
are infected, but the rows beneath are nearly as starved of infection, and the
only supply in the top band is three patient zeros that infect almost nothing
(a 1 infects nothing, a 2 only a 1). Without the row rule the 1, 2, 3 can all
sit in row 3 and rows 1-2 become one uninfected 2x9 rectangle, which is why
"columns only" is feasible. A full hand proof of the contradiction is still
open; the solver's presolve is the proof of record.
