# P10JR — real M5 FEM independent 43,236-row signed4D audit (2026-11-24)

## Native one-shot provenance and result

User delivered private `P10JP_M5_FIRST_FULL4D_EVIDENCE.zip`; archive CRC PASS (manifest, native log, signed4D, closure, analytic adjoint and components). Native manifest `P10JP_M5_REAL_FULL4D_PASS`, exit0, no STOP, wall **1045.268760s** (17m25s), max polled private bytes **2,312,318,976** (~2.15GiB), hard cap8GiB; marker `G:\ildar\Stage3D07\LOCAL_RUNS\P10JP_M5_ONE_SHOT_MARKERS\M5_R_DT25_STEPS36_91b26a9a5dcc054e.json` **CONSUMED — NEVER REPEAT**. Exact M5 mesh SHA `91b26a9a5dcc054e9ebddebc68d3e90df93956c0d7e048266d7766c0931413dd`, 15780 nodes, 10826 Tet10, 386 pore Tri6, min27QP detJ positive1.8192e−12; previously independent D031/D029 geometry/adaptation GO. Model **R/EDV_VAR/ξ0/B6 5mm, 36×25s/900s, 4 threads**, fresh forward + analytic same-M5 adjoint, **central_fd_evaluations=0**, 108 mechanical adjoint solves; max mechanical equilibrium residual2.102e−8, thermal4.9225e−11, checkpoint bitwise1.

## Independent 4D evidence QA

Re-ran pinned independent `P10GY_temporal_series.independent_time_audit` on raw returned CSV **without new FEM/Gmsh**: 43,236 signed4D rows (1200 physical volume bins×36 = 43,200, Robin36), time bounds 36×25s, all 5 component sums and 6th thermal Robin consistent, global derivative `D_R j_peak(M5)=+2.364120991403208 m⁻¹`, independent closure PASS. Component totals m⁻¹: mech explicit −10.714618279521789, mech equilibrium +9.057007210793897, mech history +3.9506008369369985, thermal mass +0.0020843404349842774, thermal diffusion +0.06904688275911731, Robin 0.0. Private signed CSV SHA `0241992ca09dcb4f04acbcfac96be910c07a99a3ad9d68868692cc49023b114b`.

New independent source-only M2/M3/M4/M5 physical common-bin comparison implemented in `p10jq_independent_m5_signed4d_audit.py`; verified row identity and region bounds, positivity of prior M2–M4 QP was addressed in previous P10JK; validates 1200×36 per mesh and signed4D sums equal global independently computed derivatives within 2e−9. JSON QA SHA `80dee5cfab3a05dfb4e390bdc2be4e55f95d0607d71f26c0e1ec615653150f8c`, remains private/local.

## Spatial derivative sequence (all steps are dt25)

| Mesh | D_R jpeak m⁻¹ | next-minus-previous m⁻¹ |
|---|---:|---:|
| M2 | +2.5598510250834945 | — |
| M3 | +2.4732148709178685 | −0.08663615416561332 |
| M4 | +2.388080130362648 | −0.08513474055522013 |
| M5 | **+2.364120991403208** | **−0.023959138959437354** |

Absolute consecutive ratio |ΔM5−M4| / |ΔM4−M3| **0.28142611116430155** (global absolute increment decreases 71.86%, ~3.55×); prior |ΔM4−M3| / |ΔM3−M2| ~0.982669895. Relative M4→M5 global ~−1.003%. **Improved global consistency, NOT proof of spatial convergence** owing strong cancellation.

| 4D diagnostics | M2→M3 | M3→M4 | M4→M5 |
|---|---:|---:|---:|
| Σ abs per bin/time **signed total** m⁻¹ | 4.9588498165 | 2.6693487290 | **2.1364740017** |
| ratio to preceding stage | — | .5383 | **.8003727570** |
| cancellation factor L1/abs(global signed) | 57.24 | 31.35 | **89.17** |
| polar N signed Δ | +.72314691 | +.09220086 | **+.11970349** |
| polar S signed Δ | +.52512093 | +.16718035 | **+.14141935** |
| polar N+S signed Δ | +1.24826784 | +.25938121 | **+.26112284** |
| outside polar signed Δ | −1.33490399 | −.34451595 | **−.28508198** |
| polar L1 signed4D Δ | 2.8357778526 | 1.6792578827 | **1.2754372752** |

The global Δ shrinks quickly but polar signed Δ does **not** shrink between M3→M4 and M4→M5 (north actually rises). Polar L1 drops ~24%, full L1 only ~20%; cancellation factor rises to89.17. Global derivative alone is unsafe as an error estimator. Need continued adaptive M6 work with nonpolar signed differences and β0.1 score, preserving D029/D031 and nonpolar influence; do not prematurely claim convergence or assign asymptotic order.

## Native log and missing heartbeat

Native log confirms 36-step solver and analytic adjoint successfully completed, final `P10W_ANALYTIC_ADJOINT_OK` wall1044.215s. The supplied **archive does not include the outer live console stdout**, so this evidence cannot identify why `P10JP_FEM_HEARTBEAT` was absent from user's screen. Earlier confirmed P10JQ instrumentation defect remains: heartbeat in same thread as WindowsJob/PSAPI/output enumeration. Do not claim it is fixed just because the FEM passed. Future guarded FEM must pass an independent Windows native silent child >60s heartbeat regression, with watchdog independent of blocking checks.

## Next scientific stage

**P10JS SOURCE-ONLY**: from real accepted M4→M5 signed4D update error map κ(M6) (same physical bins, β=.10), quantify polar/nonpolar score and spatial localization, then C² size field source-only and preregister D029 targets; only later distinct guarded M6 mesh-only Windows one-shot. No new FEM until next candidate M6 passes D031 geometry and D029 adaptation; user independently runs Windows jobs. Preserve 25s, all-phase true heartbeat, one-shot guards. Source and raw private files must not be committed to public GitHub.
