# P10JK — real P10JF M4 full4D PASS; independent M2→M3→M4 signed 4D spatial audit (24.11.2026)

## Native provenance and independent physics validity

Researcher supplied private `P10JF_M4_FIRST_FULL4D_EVIDENCE.zip`; CRC all 7 entries PASS. Contains `P10JF_MANIFEST.json`, native log, 5 compact signed-4D CSVs. Native protocol `P10JF_FIRST_REAL_M4_FULL4D_V1`: `P10JF_M4_REAL_FULL4D_PASS`, native exit0, wall1095.3127s (18m15s), peak polled private2,220,810,240 bytes≈2.068GiB, private job cap8GiB, stop_reason empty, FEM_attempts=1; **P10JF one-shot marker consumed; NEVER repeat**. Source P10GY R2 exact 101 SHA, manifest SHA `dc3f1b8d3fef2c7c0982b319225c3046c10567a7d4630649df34ae1f222214fc`, native EXE SHA `2ccbf5b68f51ce8cdfcdd7f1680785452ffe02486179f4c7c8905748afde19f7`. Exact accepted M4 SHA `a9fff03ca56b92c1d250e834bd116afee3cb0af1e846b848ef8215fb245e755c`, 15141 nodes/10399 Tet10. Same M4 direct+analytic adjoint, R/EDV_VAR/ξ0/B6 5mm/900s/36×25s/4 threads, fresh forward history SHA recorded. P10IZ prior independent D031/D029 M4 GO remains valid.

Independent reconstruction `P10GY_temporal_series.independent_time_audit` on user-returned M3 and M4 CSVs: both PASS, each 43236 rows, 36 steps, 1200 physical volume bins + Robin, 6 signed components, mechanical/thermal QP closure, 4D row/step/global closure. P10JK separate 1200-bin 43200 signed-space-time comparison verified exact identical physical bin bounds and nonzero QP support in all M2/M3/M4 bins. No new FEM or Gmsh generation in independent analysis.

## Primary jpeak shape derivative, all values m⁻¹

| mesh | D_R jpeak | change from previous | relative change |
|---|---:|---:|---:|
| M1 dt25 | 2.628806049 (prior P10IL pinned) | – | – |
| M2 dt25 | 2.559851025083483 | −0.068955024 | −2.623% |
| M3 dt25 | 2.473214870917869 | −0.086636154165614 | −3.3844% |
| M4 dt25 | 2.388080130362648 | **−0.085134740555220** | **−3.4422%** |

`|Δ(M4-M3)|/|Δ(M3-M2)|=0.98266989544`: global differences **do not decay meaningfully**. NO global spatial convergence certification. Do not use Richardson extrapolation on this non-asymptotic sequence.

## Independent physical 4D polar analysis

Supported fixed physical bins d≤0.5mm, |μ|≥0.8, 60 N and 60 S each; identical 36 time steps and physical bounds across meshes. Signed polar contribution to D_R jpeak (m⁻¹):

| Region | M3 | M4 | Δ M4−M3 | M2→M3 signed Δ |
|---|---:|---:|---:|---:|
| N | −1.8495579001504685 | −1.757357036212226 | +0.092200863938242 | +0.723146911588244 |
| S | −1.3219210352014144 | −1.154740688846814 | +0.167180346354597 | +0.525120925486002 |
| N+S | −3.171478935351883 | −2.912097725059040 | +0.259381210292839 | +1.248267837074246 |

Both polar signed magnitudes decrease, but the net global change is **negative**, because outside-polar Δ≈−0.344515950848059. Exact polar 4D temporal-bin L1 `Σ_bins,steps |Δtotal|` M2→M3 2.8357778526, M3→M4 1.6792578827 (**−40.78%**). Whole-volume L1 M2→M3 4.9588498165 → M3→M4 2.6693487290 (**−46.17%**); polar share of M3→M4 L1 ≈62.91%. Global cancellation factor M3→M4 = 31.3544 (spacetime L1 divided by signed global Δ), smaller than M2→M3 57.24 but still large. The stronger absolute local decay relative to persistent signed global Δ is a nontrivial compensation effect, not proof of local pointwise convergence.

M3→M4 six signed-component global changes (m⁻¹): mech_explicit +0.3592588311, mech_equilibrium −0.0731633144, mech_history −0.3718310598, thermal_mass +0.0001736686, thermal_diffusion +0.0004271339, thermal_robin 0. Combined −0.08513474056.

P10JK source-only QA files locally: `P10JK_M3_M4_SIGNED4D_QA.json` and `P10JK_M3_M4_1200_SIGNED_BINS.csv`. Input archives and private raw 4D bins are NOT published in public GitHub.

## Decision and next scientific stage

**M4_REAL_FEM_PASS, independent signed4D PASS, but SPATIAL_CONVERGENCE_NOT_ESTABLISHED.** First compute source-only P10JL physical 4D error/κ hypothesis for next mesh M5 using M3→M4 spatial signed-component differences (mechanical 90%, thermal 10% as previously approved β=.10) and benchmark against M2→M3. Do not repeat M4 FEM or M4 Gmsh. Respect original CAD/10 seeds, smooth C² graded adaptation, pre-registered D029 actual N/S Veff target 25–50% and D031 all-curved-Tet10 quality gate, D030 neighbour q diagnostics only. No default automatic new Gmsh/FEM until a distinct safe source-validated package has been prepared. Future Windows tools must implement P10JH all-phase actual visible ≤30s heartbeat with regression tests of silent native child.

This report records one real new physical mesh step and sets up further convergence research; paper claims must distinguish verified local L1 decay from unverified global convergence.
