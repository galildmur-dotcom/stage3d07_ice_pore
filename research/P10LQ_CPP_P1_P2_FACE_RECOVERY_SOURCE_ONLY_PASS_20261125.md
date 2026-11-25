# P10LQ — source-only C++ face recovery for M9 stress jumps

**Date:** 2026-11-25. **State:** PASS C++ synthetic tests, no FEM/Gmsh, no actual physical stress jumps measured.

Following the preregistered P10LP real-M9 face-support audit, `research/diagnostics/p10lq_tet10_face_recovery.hpp` implements deterministic weighted least-squares reconstruction from all 27 Tet10 volume QPs to each of four *reference curved-face centroid* locations. P1 uses the four barycentric coordinates, P2 the same 10-node basis as production Tet10. The 10×10 Gram inversion uses partial-pivoting with a hard singularity gate. Precomputed linear weights permit applying exactly the same projection to all six components of stress and its geometric JVP, avoiding recomputation per physical state. The module also computes the physical Frobenius stress jump with shear-weight 2 and the traction jump against a shared normal.

Two independent native C++ fixtures PASS:

1. Standalone synthetic 27-QP Duffy sampling: affine stress exact P1 error `5.33e-15`; quadratic stress exact P2 error `6.22e-15`; P1/P2 comparison on quadratic fields is nontrivial (`0.067631`); deliberately rank-deficient samples are rejected; traction and Frobenius norms checked.
2. **Actual Stage3D07 production `volume_q(3)`** through the pinned source translation unit: P1/P2 constant reproduction within `3.33e-16` / `2.22e-16`, P2 known quadratic field at all four face centroids within `2.66e-15`.

These are *exact-polynomial reproduction tests*. A recovered trace of nonlinear EDV stress is not an exact constitutive value at a face: the material history is only stored at volume QPs. Hence real face-jump claims must report P1 and P2 separately and their disagreement, in addition to the primary traction jump and unscaled stress norm. The recovery method does **not** automatically enforce traction equilibrium and is not evidence of physical convergence or a continuum singularity.

P10LP geometric support constraint remains: zero interior curved-face centroids in the wall radial bin `[0,20 μm)`, 718 in `[20,50 μm)` (300 south pole, 382 north pole), then 900 in `[50,100 μm)`. For any first-shell claim, either add carefully defined face Gauss evaluation points and check nonzero support, or report the distinct wall-adjacent one-sided stress variation; do not use the original P10LM volume-QP values as face jumps.

**Next P10LR:** integrate the header into a **separate** guard-marked M9 diagnostic source: collect QP stress and geometric JVP only at the needed steps, recover each side of actual face pairs, aggregate by radial/polar bins, compare P1/P2, and retain original P10DD/P10LG closure. Validate compiled C++ data path on synthetic Tet10 pairs before preparing a new one-shot Windows ZIP. Do not consume/reuse old P10LM or P10LC markers.

QA: `research/P10LQ_FACE_RECOVERY_CPP_SOURCE_ONLY_QA.json`.
