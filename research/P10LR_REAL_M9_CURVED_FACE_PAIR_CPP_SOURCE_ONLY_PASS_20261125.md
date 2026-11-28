# P10LR — paired recovered stress traces on actual curved M9 Tet10 faces

**Date:** 2026-11-25. **Outcome:** PASS real accepted M9 geometry, synthetic per-QP stress tensors. No FEM or Gmsh. Consumed P10LC/P10LM native markers untouched.

## Implemented

The new `research/diagnostics/p10lr_tet10_face_jump.hpp` joins each shared face using three common global *vertex* IDs, strictly rejects non-manifold topology, and evaluates the **quadratic Tet10 physical face centroid** on both elements independently. Its normal is the normalized cross product of two exact tangents of the curved quadratic face map at its centroid (not a planar three-vertex normal). The two centroids must coincide to 1e-10 m or the diagnostic stops.

At the same physical face centroid, P10LQ P1/P2 weighted volume-QP recovery gives both one-sided tensors. It computes three independent nonnegative metrics: full Voigt/Frobenius stress jump, traction jump against the shared curved-face normal, and the geometric-JVP tensor jump. Results accumulate per fixed 10×10×12 spatial bin with count, sums, squared sums, maxima; mixed B6 boundary faces are excluded by requiring **both adjacent elements** in the mask.

## Real M9 topology + synthetic tensor test

Compiles the actual pinned Stage3D07 translation-unit environment and reads the exact accepted M9 (`19,236` nodes, `13,166` Tet10; mesh SHA `a40aca54636a752afe4d7babe9d03e741b2e988b9ad3dbb6f356728bff035a58`). The selftest `research/tools/p10lr_real_m9_synthetic_face_pair_selftest.cpp` reports:

| Test | Measured result |
| --- | ---: |
| Shared interior face pairs | 25,470 |
| Maximum centroid discrepancy between element sides | `1.44097e-17 m` |
| Largest false stress jump for globally constant 6-component tensors | `5.49757e-15` |
| Deliberate local stress-tensor discontinuity | `1000` detected exactly |
| Deliberate local geometry-JVP discontinuity | `500` detected exactly |
| Both P1 and P2, curved-normal traction, singular recovery guard | PASS |

These values are synthetic stress units in this source-only fixture, **not measured physical M9 ice stresses**. The source-only test verifies the actual face adjacency/topology, correct physical-point pairing and tensor algebra, using all interior faces, not the physical B6 mask.

## Limits and next P10LS

The P10LR module currently accepts per-step arrays `sigma[qp]` and `geom_dsigma[qp]`; neither is present in the old P10LM evidence ZIP. The next distinct source step must connect these arrays to the actual `p10dd::mechanical_step` while it already loops over the 27 mechanical Gauss points, and call P10LR from `reverse_scan` after constructing `p10c::Step`. Record both P1 and P2 face-jump aggregates at all 36 time steps with clear mask coverage, radial/μ support counts, original signed P10DD/P10LG closure, independently checked CSV. This needs source-pin update and a **new independently marked physical M9 one-shot**, not a rerun of consumed P10LM.

The P10LP support constraint still applies: zero interior **face centroids** in 0–20 μm, first nonempty centroid shell 20–50 μm. No face-jump observation in the unsupported bin may be inferred from the P10LM volume-QP explicit stress-chain totals.

Machine-readable QA: `research/P10LR_REAL_M9_FACE_PAIR_SOURCE_ONLY_QA.json`.
