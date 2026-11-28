# P10HJ — actual M1 curved Tet10 quadratic mechanical κ interpolation audit

Date 2026-11-24. Read-only scientific QA from pinned 13,978-node, 9,623-Tet10 P10GT M1. Original M1 evidence SHA256 `7bff029865bd69e12b8302a9f65b6159d61f58163300fdee81555954988a6ac3`. Mechanical-only C2 κ built from pinned P10HA 4D physics of M0/M1. No mesh generation, FEM or modification of original M1.

The independent reproducible script `scripts/p10hj_quadratic_tet10_curved_field_qa.py` computes standard ten-node Lagrange shape functions with Gmsh's official six Tet10 edge ordering. Its nodal 10×10 Kronecker condition is independently checked to <1e-13. It maps 11 strictly interior reference coordinates per element into actual curved geometry using all ten physical coordinates, then evaluates the original physical C2 field at those spatial positions. 105,853 / 105,853 samples fall within ice (none inside the pore). Comparator uses linear corner-node field at the *same reference positions*, not an unsupported claim about Gmsh spatial probing behavior.

| Absolute κ discrepancy from original C2 spatial field | Corner linear | Curved Tet10 quadratic |
|---|---:|---:|
| Sample count | 105,853 | 105,853 |
| Median | 0.000712918 | 0.000153512 |
| P95 | 0.0173560 | 0.00740723 |
| P99 | 0.0643768 | 0.0317525 |
| Maximum | 0.553797 | 0.570106 |
| Samples >0.05 | 1,424 | 572 |
| North polar samples >0.05 | 520 | 225 |
| South polar samples >0.05 | 446 | 248 |
| Nonpolar samples >0.05 | 458 | 99 |
| Near wall (d≤0.1 mm) p95 | 0.233264 | 0.204589 |
| Near wall (d≤0.1 mm) max | 0.553797 | 0.570106 |

Quadratic interpolant κ range across samples: **[-0.0261022, 0.853063]**; **2,311 / 105,853** sampled values are outside [0,1] (negative). This is a mathematical property of unconstrained quadratic interpolation, not an error in original bounded κ field. No clipping was applied to conceal the problem.

**Decision: NO-GO for M2 size field from a Tet10 nodal interpolation alone.** Quadratic interpolation improves typical accuracy but does not robustly resolve steep source field variations near the spherical wall, with both polar and nonpolar checks mandatory. Native Gmsh model-based `NodeData` / high-order PostView is documented, but not yet verified to provide a suitable adaptive-size field: do not conflate API availability with fidelity of the physical κ source.

**Next P10HK research design:** evaluate a mesh-independent direct continuous-κ query path usable by the Gmsh background size field, with bounded runtime and domain safeguards; or adaptive spatial sampling of the same continuous source with a *measured* error tolerance, especially at pore-wall/poles. Report true sampled size field, smoothness and D-025-compatible projected cell sizes before *any* 1D/2D/3D remeshing. Never generate FEM or M2 from this stage without successful independent source-field QA.

Official Gmsh 4.15.2 API reference: https://gmsh.info/doc/texinfo/#gmsh_002fview_002faddModelData and https://gmsh.info/doc/texinfo/#gmsh_002fview_002fsetInterpolationMatrices .
