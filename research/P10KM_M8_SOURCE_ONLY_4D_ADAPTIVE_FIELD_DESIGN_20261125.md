# P10KM — M8 adaptive mesh C2 source-only design (2026-11-25)

**PASS_SOURCE_ONLY_NO_GMSH_NO_MESH_NO_FEM.** A new M8 *size-field design* is prepared, not a new Gmsh mesh. No consumed M7 mesh/FEM attempt was repeated. Do not treat this source-only field as D031 geometry GO or D029 actual polar refinement GO.

## Independent source construction

Exact accepted M7 R2 mesh SHA256 `875c9177de24612d0078f7a792b4b7641a2e604973cb1353500710c87693bb3d`; input M7 evidence ZIP SHA256 `0bc50329078cba02f2a5ad55bfcee1d42ef4cf0475d44430598982c233ba5ec7`, pinned M6 CSV `dd6e248d5410a18c9821d36e544028d7b64a028fddf1e125e234f24965a3bb1f`. Regime remains R/EDV_VAR/xi0/B6 5mm **36×25 s**, analytic same-mesh adjoint.

For each of 1200 spherical bins (10 radial × 10 polar × 12 azimuth), compute full-time `L1=Σ_{t=1..36}|Δ(M7−M6)_{bin,t}|` and late-time `L1_late=Σ_{t=31..36}|Δ|`, both with per-bin full signed contributions. Set a nonnegative score `s = [0.4 L1/max(L1) + 0.6 L1_late/max(L1_late)] × p(μ)`, where `p=1+0.2 smoothstep5((|μ|−0.6)/0.3)` with clamping. This uses late-time evidence (60.8% of full L1 in last six steps), but does not force an azimuth singularity or a hard polar cut. The score is a **priority proxy, NOT an error estimator**.

Interpolate the positive scores with pre-existing pinned compact Wendland C2 Cartesian-direction/log-distance field (p10iu_continuous_m4.Field), normalize to `[0,1]` using quintic smoothstep. The additional **M8/M7 size multiplier** is `h=(1−0.20 κ)^(1/3)`; this means max **20% volume reduction**, i.e. **7.1682% characteristic length reduction** where κ=1. This follows the historical mesh rule; do not misstate it as 20% reduction in edge length. Maintain smooth [0,1] κ throughout the domain, zero effect outside C2 support. Apply this M8 multiplier *after* the complete accepted M7 R2 cumulative Gmsh size callback, including the distinct R2 polar C2 collar and retained CAD/10 embedded seeds/physical tags. Do not replace the M7 geometry and do not re-run its consumed one-shot.

## Independent source-only preflight

- Exactly 1200 source bins joined one-to-one to pinned source coordinate reference; source positive and bounded, all original 43,236 4D rows retained in input audit.
- 847 independent 3D test points: κ in `[1.67e-6,1]`, M8 incremental h-ratio sampled in `[0.92831777,0.99999989]`, positive everywhere, no step function.
- Periodic φ=−π/+π seam mismatch ≤ `6.11e−16`; exact polar-coordinate invariance mismatch `0`.
- Dominant bins are near-wall north and south polar sectors; azimuthal priorities vary smoothly through the Wendland interpolant.
- No 3D mesh created; Tet10 quality D031 curved 27/343/729QP, CAD closure, independent D029 effective-volume actual M8/M7 ratio, and one-shot Windows progress evidence remain the **next gates**.

Files in user artifact `P10KM_M8_SOURCE_ONLY_4D_ADAPTIVITY_DESIGN_20261125.zip`, Library `libfile_7e106d3f8eac8191bd3c79312d691e66`: `P10KM_M8_LATE_TIME_SIGNED4D_1200_BINS.csv`, `P10KM_M8_SOURCE_ONLY_DESIGN_QA.json`, `P10KM_M8_FIELD_SAMPLES.csv`, `P10KM_M8_SOURCE_PRIORITY_MAP.png`.

Source builder committed at [research/tools/p10km_m8_source_only_design.py](https://github.com/galildmur-dotcom/stage3d07_ice_pore/blob/research/p10bb-w5b2-20261118/research/tools/p10km_m8_source_only_design.py). This uses the exact older `p10iu_continuous_m4.Field`; packaging the standalone real M8 Windows one-shot must include all pinned source dependencies and exact accepted M7. Next P10KN should prepare distinct Windows mesh-only guarded package with ≤15s progress and separate M8 marker, without FEM. When a real M8 mesh arrives, apply independent D031 and D029 acceptance before any M8 FEM.
