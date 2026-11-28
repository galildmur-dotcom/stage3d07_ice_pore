# P10KA — M7 incremental C² size field calibrated to 20% local volume reduction (2026-11-24)

## Outcome
**PASS_SOURCE_ONLY** (no Gmsh, no M7 mesh, no FEM). Uses accepted M6 as immutable base, P10JZ 1200-cell provisional C² adaptation map, physical signed4D (M4,M5,M6), `Δt=25 s × 36`. The user-approved notion of 15–25% **element volume** reduction is NOT a 15–25% element edge reduction. Nominal 20% maximum volume reduction corresponds to **7.17% local linear size decrease**.

Incremental field on original CAD:

`h7(x)/h6(x) = exp( log(0.80) κ_M7(x) / 3 ) = 0.80^(κ_M7(x)/3)`, with `0≤κ_M7≤1`, where κ is a smooth nonnegative C² field based on P10JZ mixed M4→M5, M5→M6 signed 4D absolute errors.

The local cube proxy is `(h7/h6)^3=0.80^κ`. This is a **source-only proxy**, not an actual regional Tet10 Veff(M7)/Veff(M6) measurement.

## Scenario and continuity guards
For 15%, 20%, 25% local volume reductions, the minimum linear size factors are approximately 0.94727, 0.92832, 0.90856, respectively; elsewhere the factor continuously returns to 1. No point is assigned an incremental factor below the corresponding bound. Existing accepted M6 field and the original CAD are unchanged.

Continuous-field sample coverage: 12 distances from pore wall × 11 polar directions × 6 azimuths = 792 physical points; includes poles, azimuthal seam, near-wall and far-field. Azimuthal seam discrepancy at Δt-independent size ratio 1.1×10⁻¹⁶, pole identity 0. Max difference between adjacent 1200-cell source-center size factors 0.07148, 95th percentile 0.00360. These are **not** adjacent-element quality metrics.

The strongest incremental source refinement remains at the northern pore pole, some activity at the southern pole, tapering smoothly away from the wall. This is consistent with P10JZ: M5→M6 L1 error of north 0.76727, south 0.28966 m⁻¹; 74.85% of latest L1 difference lies in 675–900 s. However nonpolar L1 increased 1.3%, so it cannot be ignored.

## Gates and next work
- **D031 true curved Tet10 quality unknown**. Must be calculated after distinct guarded Gmsh M7 candidate with multi-QP (27/343/729) tests, Jacobian sign, minSJ/SICN/gamma, CAD closure, mesh transition.
- **D029 actual regional Veff(M7)/Veff(M6) unknown**. Must compare independently on supported polar and nonpolar regions and report actual ratios separately from source proxy; do not infer success from `0.80^κ`.
- **No M7 FEM**: do not run until distinct mesh GO and scientific go/no-go. Never replay consumed M6 FEM marker.
- Future native launch programs should show independent progress heartbeat every 15–30s and per-process CPU/wall profiling (user's M6 four-thread CPU≈20% issue).
- The next task P10KB is a *separate guarded M7 mesh-only program* against exact accepted M6, not a rerun of old M6. Do not alter dt=25s.

## Reproducibility
Input source P10JZ 1200-bin CSV SHA256 `851fd56d8df84b5e6dd9990ac6b5edf56227a39598e7b634a6448b76ef3f4454`.
P10HA physical centers SHA256 `98bc99af9783e14f7800f08ecd04fc6bee8093d0490b359e3a024f4c6c4566a3`.
Artifacts: `P10KA_M7_C2_SIZE_FIELD.png`, `P10KA_M7_C2_SIZE_FIELD_SAMPLES.csv` (792 rows), `P10KA_M7_C2_SIZE_PREFLIGHT_QA.json`.
