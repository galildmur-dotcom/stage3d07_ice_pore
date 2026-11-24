# P10HU — independently verified real P10HT candidate against pinned original M1

Date 2026-11-24. User provided `P10HT_M2_UNVERIFIED_CANDIDATE_EVIDENCE.zip` SHA256 `92079e8c1dd7bcf99b34ce973c1a9960c189b4fd5a9e17981a46a90b03dc7883`. Candidate MSH SHA256 `53de9d5c5ad28c677f21f5b660acd75e497b8a27b3dd93173e4f2de678937d58`; compare **original pinned M1 evidence** SHA256 `7bff029865bd69e12b8302a9f65b6159d61f58163300fdee81555954988a6ac3`, MSH SHA256 `47460969be26c2bd0a15e0b1425806fa350aa09aa2b4ac9f80605b433fc65ca7`. Independent reproducible program `scripts/p10hu_independent_m1_m2_curved_qp_adjudicate.py` re-parsed raw source, actual CAD physical Tri6 groups 2–9 and Tet10 connectivity. **No FEM, no mesh generation, no new physical history.**

P10HT native result: Gmsh 4.15.2 25,095 callback queries; 9 cavity-only ghost samples up to 0.0669841 mm inward; zero actual mesh nodes in air, center ghost probes 0; single native 3D 1.307 s; 14,071 nodes, 9,693 Tet10. M1 has 13,978 nodes, 9,623 Tet10.

| Independent property | M1 pinned | Candidate P10HT |
|---|---:|---:|
| 3D Tet10 | 9,623 | 9,693 |
| QP729 curved ice volume m³ | .00017999581340742544 | .00017999581344651052 |
| QP729 relative CAD volume closure | 1.22e−8 | 1.24e−8 |
| Min detJ, 27QP | 2.28685e−11 | 2.62267e−11 |
| Min detJ, 343QP | 1.96200e−11 | 2.34310e−11 |
| Min detJ, 729QP | 1.92252e−11 | 2.30927e−11 |
| Mean total Tet10 volume ratio candidate/M1 | — | **0.9927783** |

All sampled detJ positive. Across 18 signed radial/polar/hemisphere partitions the maximum absolute disagreement of 343/729 effective-volume *ratios* is 0.0065191. Hence numerical integration and curvature are not the source of observed volume redistribution.

| Actual spatial comparison (QP729 or curved Tet10) | Candidate/M1 |
|---|---:|
| North polar, distance 0.1–0.5 mm, QP effective volume | **0.9211** |
| South polar, distance 0.1–0.5 mm, QP effective volume | **1.0359** |
| North polar, distance 0–0.1 mm, QP effective volume | **1.0159** |
| South polar, distance 0–0.1 mm, QP effective volume | **1.0086** |
| Northern taper 0–0.1 mm (0.6<abs μ<0.8) | **0.8329** |
| North wall-adjacent d≤0.5 mm, median Tet10 volume | **0.9350** |
| South wall-adjacent d≤0.5 mm, median Tet10 volume | **0.9918** |
| Nonpolar wall-adjacent d≤0.5 mm, median Tet10 volume | **0.9736** |

The original C2 κ is concentrated on the pore surface, thus **no element centroid** reaches κ≥0.8. Classifying Tet10 by *actual nodal* max κ≥0.8 yields 37 M1 vs 40 candidate wall-adjacent elements; **unmatched group median candidate/M1 curved volume 1.2043**. This is not a pointwise matched-volume comparison and must not be over-interpreted, but it shows that nominal 17% characteristic-volume reduction does **not** reliably translate into 15–25% actual reduction near all extreme κ wall nodes.

## Scientific verdict

**Geometric/curved-QP GO, quantitative D-025 local 15–25% effect NOT demonstrated.** User explicitly accepts *small* local size differences and redistribution for an ~20% adaptation iteration; therefore a small global +0.7% Tet10 change is not an automatic rejection. However the sign and spatial coverage of densification still require evidence. The candidate may be useful as a *geometry-only adaptive study* but is **not yet accepted as production M2 for FEM**. In particular southern near-polar QP volumes increased by 3.6% while northern ones decreased by 7.9%; do not claim uniform critical-zone densification.

Next step P10HV: one bounded, predeclared original-CAD 3D **α sensitivity sweep** with α∈{0.15,0.20,0.25} around existing α=.17 (no FEM) and otherwise byte-identical source/geometric settings, then independent QP343/729 comparison of actual resulting volume distributions. The prepared ZIP `research/proposals/P10HV_ALPHA_3D_SCAN_20261124/P10HV_R1_THREE_ALPHA_3D_CANDIDATES_WINDOWS_20261124.zip` has SHA256 `b498e2f48b87dc65f74b04ad91351c2f46013ec75734f6acab24843ab39aee5f` (214,716 bytes, CRC verified, source Python syntax checked). This identifies whether modest change of α alters local behavior or whether the mesh algorithm's finite-size response dominates. Keep polar/north/south and smoothness checks. No automatic user permission request for prepared Windows programs.
