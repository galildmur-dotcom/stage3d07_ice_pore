# P10LG — two-term mechanical explicit diagnostic (source-only)

**Date:** 2026-11-25. **State:** prepared and syntax-checked; **no FEM or Gmsh run**. The M9 physical one-shot remains consumed and must not be reused.

## Scientific question

The P10LF audit identified the `mech_explicit` increment but did not determine whether the near-wall effect comes predominantly from motion of the observation volume or from the stress-chain rule. P10LG instruments the existing P10DD 4D partition without modifying the normal signed P10DD output.

For each bin `b` in a particular time step, with QPs `q`, the split is

\[
 E_{b,\mathrm{geom}}=\frac{w}{V}\left(\sum_{q\in b} \dot v_q\,s_q-\bar s\sum_{q\in b}\dot v_q\right),\qquad
 E_{b,\mathrm{stress}}=\frac{w}{V}\sum_{q\in b}v_q\,(\lambda_{\sigma,q}:\dot\sigma_q).
\]

Here `s_q=src.value`, `bar s=Σ(v_q s_q)/V`, and `w` is the same PeakMoment weight as the original P10DD implementation. The original `dpoint` is a stress-chain term for PeakMoment, whose direct-strain term is zero. At each cell the original `mech_explicit` must equal `E_geom+E_stress` to tolerance `1e-10` in the existing `expect_close` convention.

## Deliverables

- `research/tools/p10lg_build_two_term_explicit_diagnostic.py`: reproducible, SHA-pinned builder; refuses to overwrite an existing diagnostic package. The original P10LC source is read-only.
- `research/diagnostics/P10LG_stage3d10dd_two_term_partition.hpp`: instrumented header for audit/review, not a replacement for the original solver.
- `p10lg_source_only/P10LG_SOURCE_ONLY_QA.json`: preparation manifest and compiler check.
- New optional CSV sidecar `P10LG_EXPLICIT_GEOMETRY_STRESS_4D.csv` with 1,200 spatial bins per step, 36 steps, 43,200 rows for each mesh run; columns identify bin/time and both signed terms plus original sum.

## Verification and boundaries

1. Exact original P10DD source SHA-256 pin: `bbcb824a9fa25d7c66be54091c19c56b2a7ced40d2801071250f0b57ed4df55d`.
2. Source-only syntax PASS: `g++ -std=c++20 -fopenmp -O0 -fsyntax-only` on `stage3d10fn_any_mesh_full4d.cpp` including original `src`, `tests` and work directory paths, defining `STAGE3D06_ROOT_DIR`. No execution.
3. Three programmed gates: per-cell closure at computation, per-cell closure at CSV emission, all-steps two-term closure against original explicit; existing P10DD-vs-P10V closure retained.
4. The usual `P10DD_SIGNED_R_THETA_PHI_T.csv` remains unchanged in its column definitions and expressions.
5. **No newly measured geometry/stress numbers** are claimed. Neither a new FEM run nor a validated replay of physical state data was available or authorized. The previously observed M8→M9 signed increment `+0.19602467 m⁻¹` cannot yet be assigned to either term.

**Next scientific gate (P10LH):** validate a source-only synthetic quadrature fixture that produces nonzero values in each term and checks closure, then decide whether a genuinely new, separately marked physical run or a provably complete saved-state replay is warranted. Never reuse the consumed M9 one-shot marker.
