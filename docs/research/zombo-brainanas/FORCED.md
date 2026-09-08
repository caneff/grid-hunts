# Forced shading

r8c8 is infected in every valid Zombo Brainanas grid. Nothing else is forced.

Proof. Box 9's patient zero is its 9, the largest digit, so it infects every
orthogonal neighbour. Its infected group is a rectangle, so it covers the
bounding box of the 9 and its neighbours. 9 at the center: it is r8c8. 9 on a
box edge: r8c8 is a neighbour. 9 in a corner: the two in-box neighbours form an
L with it whose bounding rectangle contains r8c8.

Solver check (tools/forced.py, model at efe3ac2): for each of the 81 cells,
"can it be uninfected" and "can it be infected" were solved with a 60 s limit.
161 of 162 cases found a witness grid; only "r8c8 uninfected" is INFEASIBLE,
proven in presolve. No case timed out. Box 8's center is not forced because an
8 spares a neighbouring 9 (r8c5 infected in 38 of 77 found grids).

Use: the component seeds r8c8 infected before any propagation; the generator
may fix it to shrink the model.
