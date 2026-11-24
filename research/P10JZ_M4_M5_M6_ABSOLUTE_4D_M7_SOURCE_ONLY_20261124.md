# P10JZ — M4→M5→M6 absolute signed-4D localization and provisional M7 source (2026-11-24)

## Scope and immutable data
SOURCE-ONLY. No new Gmsh, mesh or FEM execution. Same physical R / EDV_VAR / ξ0 / B6 5 mm, analytic adjoint, 36×25 s = 900 s. Signed physical 4D binning: 10 radial × 10 polar × 12 azimuth × 36 times; 1200 spatial cells, 43200 volume rows per mesh. Exact source CSV SHA-256: M4 `6c64dcb98f135cad24d8e8eb26b17d9cdfc92b38d385b6475f85a12b743595a2`, M5 `0241992ca09dcb4f04acbcfac96be910c07a99a3ad9d68868692cc49023b114b`, M6 `dd6e248d5410a18c9821d36e544028d7b64a028fddf1e125e234f24965a3bb1f`. Signed 4D components use the five volumetric columns, whose total agrees with global derivative; top Robin contribution is zero in these runs.

## Quantitative localization
Let `a_{kst}=Σ_comp(q_M5-q_M4)`, `b_{kst}=Σ_comp(q_M6-q_M5)`, spatial index k and time s. We evaluate `L1=Σ_(k,s)|a|` or `Σ|b|` **before** global signed summation.

| Category | M4→M5 absolute L1 [m⁻¹] | M5→M6 absolute L1 [m⁻¹] | ratio |
|---|---:|---:|---:|
| All cells | 2.136474002 | 1.929118586 | 0.902945 |
| Northern polar band (r bins 0..4, μ bin 9) | 0.840920569 | 0.767270904 | 0.912418 |
| Southern polar band (r bins 0..4, μ bin 0) | 0.434516706 | 0.289661000 | 0.666628 |
| Polar bands combined | 1.275437275 | 1.056931904 | 0.828682 |
| Remaining nonpolar cells | 0.861036727 | 0.872186682 | **1.012949** |
| Near-pore r bins 0..4 | 1.733403546 | 1.446114714 | 0.834263 |

Global signed derivative changes: −0.02395913896 and −0.001468203617 m⁻¹, respectively. Thus, **local convergence is NOT established**. Global cancellation factor for latest increment is 1313.93.

Time localization for M5→M6 L1: 0–225s 0.013567805; 225–450s 0.112848790; 450–675s 0.358791236; **675–900s 1.443910755 m⁻¹ (74.85% of total)**. The last time interval dominates, especially near the northern pole.

## C2 M7 adaptation source — provisional only
A future M7 source indicator was prepared using normalized componentwise absolute 4D deltas (mechanical 90%, thermal 10%, same convention as P10JL and P10JS). We propose a **diagnostic** robust score `s7=.30*s(M4,M5)+.70*s(M5,M6)`; the weights are **not** a calibrated mesh-size change and must be reviewed before mesh generation. A positive periodic/spherical-coordinate-free Wendland C2 map, inherited from the approved P10IU Field method, was evaluated at 1200 cells. Its interpolated center values lie in [0,1]. No claim of geometric 15–25% refinement or actual Tet10 quality is made yet.

Dörfler θ=0.5: previous increment 93 selected cells (68 polar), latest 115 cells (74 polar), mixed M7 115 cells (**83 polar: 48 northern and 35 southern**). Previous-vs-latest selection Jaccard **0.51825**; mixed-vs-latest **0.78295**. Latest vs previous time-cell signed increment agree on only **44.16% of overlap-weighted support**. This confirms substantial sign redistribution.

Total proposed mixed C2 source mass: polar 43.82% (north 29.74%, south 14.08%). Northern priority remains high, but do not ignore nonpolar growth.

## Decisions and hard gates
1. Retain **25 seconds** time step, source lock, exact R jpeak 4D physical bins, same-mesh direct/adjoint.
2. M7 **not generated and not FEM run**. No permission to infer convergence from near-zero global ΔM6−M5.
3. Next P10KA: source-only physical geometry h7/h6 calibration with guarded 15–25% smooth size adjustments; check D029 actual polar volume response and D031 quality. No hard mandatory uniformity; smoothness matters. Only then a distinct guarded mesh-only attempt.
4. For the next legitimate FEM, log CPU-time/wall utilization and timed serial/parallel phases; user observed ~20% CPU with 4 OpenMP threads.

## Artifacts
`P10JZ_M4_M5_M6_ABSOLUTE_LOCALIZATION_M7_SOURCE.png`: six-panel absolute 4D localization and proposed M7 score.
`P10JZ_M7_PROVISIONAL_C2_1200_BINS.csv`: per-cell signed/absolute old/new evidence and provisional C2.
`P10JZ_4D_LOCALIZATION_AND_M7_SOURCE_QA.json`: immutable hashes, numerical validation, regional and temporal diagnostics.
No one-shot markers or FEM outputs were modified.
