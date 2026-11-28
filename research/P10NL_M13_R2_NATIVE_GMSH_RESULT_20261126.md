# P10NL — native Gmsh quality of three-node diagnostic copy (2026-11-26)

Input result: `P10NL_M13_THREE_NODE_DIAGNOSTIC_GMSH_QUALITY_RESULT.json`, checked against pinned M13 R2 and diagnostic SHA256. This is a diagnostic mesh copy **not M13 R3**. No FEM, no Gmsh generation, no one-shot marker.

| Gmsh quality | Original M13 R2 | Three-node diagnostic | D031 threshold | Below threshold (before → after) |
|---|---:|---:|---:|---:|
| minSICN | 0.16294478890105799 | 0.19120540512114387 | >= 0.20 | 1 → 1 |
| minSJ | 0.28115937433961596 | 0.3174590262749687 | >= 0.40 | 1 → 1 |
| gamma | 0.24272495924632292 | 0.24272495924632292 | >= 0.15 | 0 → 0 |
| minDetJac | 1.6517904678607355e-13 | 1.6517904678607355e-13 | > 0 | 0 → 0 |

Both minSICN and minSJ violations remain confined to Tet10 tag `9478`; no other Tet10 falls below these thresholds. Improvement: minSICN +17.3449% and minSJ +12.9107%. Crucially, the optimized 729QP singular-value ratio of P10NK was only a source-side proxy; these measurements establish a positive but insufficient improvement for the actual Gmsh criterion.

The sample is consistent with a local curved-element degeneracy at the pore-facing tetrahedron, not with a mesh-wide quality degradation. However, a globally safe fix has **not** been established. D031 remains HOLD. M13 R2 remains the latest physical mesh candidate; the diagnostic copy is not an accepted successor.

## Next scientifically controlled experiment (proposed P10NM)

1. From the same pinned M13 R2, construct a limited family of *separate diagnostic* copies changing only the three off-pore corner nodes (8680, 8681, 9115) and their globally shared midside nodes; keep pore Tri6 fixed and preserve connectivity.
2. Start from the P10NL vector `(0.010,0.005,0.005) mm` and test a limited stepped neighborhood, while requiring positive 729QP detJ, affected-star individual curved volume ratio `[0.9,1.1]`, and bounded deterioration among adjacent Tet10. Any broader displacement requires separate justification.
3. On Windows Gmsh 4.15.2, obtain the *canonical* minSICN, minSJ, gamma and minDetJac for each SHA-pinned copy, recording the worst global Tet10 tags and counts violating thresholds. Choose only a non-dominated candidate that passes **all** D031 criteria. Do not infer minSJ pass from proxy ratios.
4. If no constrained candidate passes, report an honest local-coordinate optimization failure and revert to a conforming geometry-preserving CAD/remeshing strategy subject to the one-shot protocol. Do not run FEM or mark any trial M13 R3.

Original M13 R2 SHA256: `57403ba43fa299417d519046cebdf50fa4968b670c071a8b7882748b50f51e9c`.
Diagnostic copy SHA256: `fbc3f58a2d463936c80aa8ef04b89dad68ab45ed4b682b8d3807208ba6d65477`.
