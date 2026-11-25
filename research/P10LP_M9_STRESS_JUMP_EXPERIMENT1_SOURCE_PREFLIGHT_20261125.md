# P10LP — experiment 1: stress-jump measurement feasibility on real M9

**2026-11-25. State:** source/geometry-only preflight PASS, actual stress jump **NOT YET MEASURED**, FEM0/Gmsh0. The consumed P10LM M9 one-shot must not be repeated.

## Scientific definition (do not conflate derivatives)

For each interior Tet10 face shared by elements `e+` and `e−`, choose *identical physical points* `x_fq` on the curved face and a consistent unit normal `n`.

- Actual traction jump: `j_t = ||(sigma_+ - sigma_-) n||` [Pa]. This is the primary weak-equilibrium-related indicator.
- Full stress jump: `j_sigma = ||sigma_+ - sigma_-||_F` [Pa]. This measures discontinuity of the reconstructed stress tensors.
- Geometric shape derivative stress jump: `j_dsigma = ||sigma'_geom,+ - sigma'_geom,−||_F` [Pa/m], an **additional** diagnostic, not a spatial derivative `grad sigma` and not the full state derivative.
- Normalized ratios require a declared reference stress and denominator floor; absolute values must always be retained.

The constitutive EDV history is held as independent QP states. Unlike polynomial displacement fields, physical stresses are only evaluated directly at the 27 volume quadrature points in the present code. A face value is therefore **not available directly** from those data, even during the physical run. Any volume-QP-to-face polynomial recovery must be explicitly labeled *reconstructed one-sided stress trace*, not an exact EDV field trace.

The recommended first numerical method is **two reconstruction orders**, P1 and P2, from the same 27 per-element volume-QP tensor samples. Fit each of six stress components (and optional six geometry-shape JVP components) via weighted least squares; evaluate each fitted polynomial on the shared curved Tri6 face at identical physical points. Report both P1 and P2 results and their difference as a reconstruction sensitivity diagnostic. Verify exact reproduction of constant/linear/quadratic synthetic tensor fields and rejection of degenerate solves before any new FEM.

At each step report only statistical reductions by radial shell, μ bin, and polar labels (count, weighted RMS, mean, max) plus the largest few face records. Keep all 36 steps, without 25k-face × 36-step raw output unless separately justified. One side of a face never enters a comparison at a different physical coordinate; avoid comparing nearest but unmatched volume QPs and calling the result a jump.

## Geometry preflight on exact accepted M9

Source `research/tools/p10lp_m9_interior_face_topology.py`, independent read-only parser of the original M9 Gmsh MSH 2.2, imported Tet10 internal edge mapping and quadratic face-centroid mapping. Mesh SHA `a40aca54636a752afe4d7babe9d03e741b2e988b9ad3dbb6f356728bff035a58` PASS; 19,236 nodes and 13,166 Tet10; 25,470 interior faces, 1,724 exterior faces, **zero non-manifold** faces.

**Important:** with exact curved Tri6 face centroids there are **zero interior face centroids** whose distance from the pore wall is in `[0,20 μm)`. The next radial bin `[20,50 μm)` contains **718** interior face centroids: 300 southmost μ bin, 382 northmost μ bin, 36 in the adjacent non-polar μ bins, none in central μ bins. `[50,100 μm)` contains 900 face centroids. Thus claiming a nonzero *face-centroid jump in the first 0–20 μm wall bin* would be geometrically unsupported. The existing P10LM first-shell stress-chain statistic is a **volume-QP bin statistic**, not a face-jump statistic.

For the first 0–20 μm region, either sample additional interior face quadrature points near the wall and report exact support counts, or analyze *within-element* radial stress variation / wall-adjacent one-sided traces as a **different** quantity. The recommended immediate comparison target for shared-face stress jumps is the supported `[20,50 μm)` shell, with separate face-point support diagnostics if extending toward the wall.

## Why a new physical run is needed

The supplied successful P10LM evidence contains P10DD binned aggregate 4D and the split `geometry/stress` CSV, but does **not** provide the 27-QP tensors `sigma`, `sigma'_geom`, or a per-step complete displacement/history field. Aggregating 355,482 volume QPs into 1,200 spatial bins is many-to-one and irreversible. No legitimate original M9 per-face stress jump can be reconstructed from the submitted ZIP.

The next **P10LQ** engineering gate is a new separately marked **M9** source-instrumented diagnostic: expose 27-QP stress and shape-JVP samples during the already-required mechanical step, perform validated P1/P2 face recovery and one-sided shared-face evaluation, output compact radial/polar/time aggregates and a negative QA. Preserve original `P10DD` and `P10LG` closures, mesh/source pins, 36×25s, and 4-thread bounded Windows one-shot. Require source-only and synthetic C++ recovery fixtures before delivery; **never** invoke or reuse the consumed P10LM/P10LC marker. Physical execution remains investigator-controlled under SOP D-028.

Machine-readable topological support: `research/P10LP_M9_FACE_SUPPORT_QA.json`. No stress-jump numerical measurement is claimed in P10LP.
