# P10NJ — M13 R2: conforming virtual radial displacement of the bad-Tet vertex star

2026-11-26. Source-only; exact M13 R2 mesh SHA `57403ba43fa299417d519046cebdf50fa4968b670c071a8b7882748b50f51e9c`. The independent tool `research/tools/p10nj_m13_r2_conforming_vertex_star_virtual_scan.py` identified the sole D031 failing Tet10 (tag 9478) and its off-pore fourth corner (global node tag **8680**). This common corner belongs to **28 Tet10**; there are 16 unique incident edge-midside nodes. A closure check verified that no element outside the 28-Tet10 star shares a modified node. All pore-surface nodes are fixed.

The trial moves node 8680 radially outward from the pore along the pore-face centroid direction, updating each of the 16 incident edge midnodes by half the same displacement. This is **globally shared-node conforming** across its incident edges and holds original quadratic Tri6 pore geometry unchanged. All 28 affected Tet10 were checked at 729 points each, but no `.msh` file was written, no Gmsh or FEM run occurred, and no marker was used. The trials are still **virtual** (canonical Gmsh quality not evaluated, detJ positivity between samples not proven).

| Radial outward δ (mm) | Worst min σ3/σ1 in 28 Tet10 | Ratio to baseline | Individual curved volume min ratio | Individual curved volume max ratio | Neighbors whose min ratio decreased |
|---|---:|---:|---:|---:|---:|
| 0 | 0.044827 | 1.000 | 1.000 | 1.000 | 0 |
| +0.005 | 0.048417 | 1.080 | 0.9656 | 1.0365 | 14 |
| **+0.010** | **0.051984** | **1.160** | **0.9313** | **1.0729** | **14** |
| +0.015 | 0.055530 | 1.239 | 0.8969 | 1.1094 | 15 |
| +0.020 | 0.059054 | 1.317 | 0.8625 | 1.1459 | 15 |
| +0.030 | 0.066034 | 1.473 | 0.7938 | 1.2188 | 16 |

For these positive trials all 729QP sampled detJ across the 28 Tet10 remained positive. The worst element in the star remained tag 9478, but its minimum singular-value ratio improved. **The sum of curved volumes over the entire star remained numerically invariant at 1.0** in every trial, as expected from a conforming interior-node perturbation with the star boundary fixed. Inward displacement δ = −0.010 to −0.030 mm worsens the minimum ratio and is not promising.

Scientific interpretation: a small outward shift around **+0.010 mm** may be a feasible starting design within modest local element-volume redistribution (individual ratios 0.931–1.073), without changing the pore or global effective shell adaptation. The simultaneous decrease in a geometrical ratio for 14 neighbors requires minimizing the **worst** quality (or multi-objective constraints), not maximizing quality of element 9478 in isolation. The `min σ3/σ1` quadrature proxy is **not** canonical Gmsh minSJ/minSICN, so this result is a hypothesis to be verified in future geometry-only tests, not M13 R3 acceptance.

Next scientifically controlled step: source-only constrained optimization of 2–4 interior nodes in the vicinity of node 8680, penalizing all decreases in local singular-value ratio and individual volume ratios outside e.g. [0.90,1.10]; preserve all shared edge midsides and spherical surface nodes. Only if that reveals a robust patch-wide improvement should a separately marked, one-shot **M13 R3 geometry-only** package be designed, with D029+D031 after generation before any FEM.

Full evidence: `p10nj_m13_vertex_star/P10NJ_M13_R2_CONFORMING_VERTEX_STAR_VIRTUAL_SCAN.json`. Source code is reproducible and SHA-pinned.
