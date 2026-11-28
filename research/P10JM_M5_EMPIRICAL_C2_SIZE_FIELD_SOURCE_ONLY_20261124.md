# P10JM — M5 C² metric-size field source-only empirical calibration after M4 (24.11.2026)

## Input and fixed assumptions

Real M4 FEM PASS P10JK; independent 1200-bin M3→M4 signed4D indicator P10JL β=.10 (90% mechanics/10% thermal), positive smoothed C² κ. Original accepted CAD sphere, 10 embedded seeds, same 3D geometry, no new mesh or FEM now. P10JL source SHA `0c5c475ff1986359d28fd0c4539353b9af5f221069f346008cac7be4ac149a61`, old P10IT source SHA `e31c0b72946391fa4b36572292657197ecb8f31b315403128d0d2c70fbfc3c06`, P10HA physical coordinate SHA `98bc99af9783e14f7800f08ecd04fc6bee8093d0490b359e3a024f4c6c4566a3`.

Fixed generic log-size damping `δ0=.1435943053641514` inherited from actual accepted M4, plus polar compact quintic taper and retained smooth local wall patch log-size maximum .10 near old bad wall direction [+.4179124587,+.7804360649,−.4650470143], angular chord width .45, radial width .50mm. No automatic mesh generation.

Formally proposed source field for future M5:
`h5/h4 = exp(-δ0 κ_M5(x) - δ_N W_N(x) - δ_S W_S(x) - .10 L_wall(x))`, with κ from P10JL, W_N/S compact C² pole taper and L_wall compact wall patch, all continuous across polar axis/periodic seam. δ_N and δ_S are calibrated **proxy**, not native truth.

## Empirical transfer method, explicit uncertainty

Previous **real** M4/M3 supported physical polar Veff729 from P10IZ: N .64811944865, S .66508663152, both D029 PASS [.50,.75]. Previous P10IY source-center cube-size proxy estimated N .5345210, S .6500, i.e. actual/proxy calibration factors N **1.21252**, S **1.02321**. This large north discrepancy demonstrates model uncertainty; no unqualified predictive guarantee is justified.

Using previous actual/proxy factor for each region, compute new source-center cubic size proxy with **M4 physical QP weights** (not old M3 weights), solve monotone per-pole log-size patch for calibrated transferred proxy target .65:

| Region | M3 polar QP | M4 polar QP | empirical correction | δ polar log-size | transferred ratio proxy | [.50,.75] scenario δ range |
|---|---:|---:|---:|---:|---:|---:|
| N | 137520 | 214236 | 1.21252376 | **.165575908380835** | .65 | [.11764281,.25345800] |
| S | 178272 | 270000 | 1.02321020 | **.138296708854402** | .65 | [.09036697,.22617263] |

Note correction to code: legacy P10IU `Field` defaults to `M3_QP`, which is valid for old M3→M4 only. For M4→M5 the P10JM driver **explicitly resets new-field weights to `M4_QP`** from P10JL's 1200-bin source before calibration (verified QP N214236/S270000); this is crucial for reproducibility. This calibration has only ONE observed native transition, so scenario bounds are **not statistical confidence intervals** and [.50,.75] cannot be claimed without actual M5.

## QA and scientific status

Source-only QA PASS. 396 sampled 3D points: `0.7340558130 ≤ h5/h4 ≤ 0.9999973880` (point samples, not global extremum). κ∈[0,1]. Cartesian seam max 1.943e−16, pole exact 0. New field changes the element size smoothly, preserving physically informed nonpolar adaptation from κ and added polar correction. No CAD, Tet10 or FEM generation.

Private artifacts: `P10JM_M5_SIZE_FIELD_QA.json` SHA `e7f10e30fcedc19ed151cd6381222f92297ee082bfa8f6262fed54b4040a3f17`, `P10JM_M5_SIZE_FIELD_SAMPLES.csv` SHA `f765ddd30a5dcb2c9011221e45ef1b8f0abd2c473ba6c1aadc28937af57eb6e4`. Do NOT publish raw M4 mesh or private bin/field CSV to GitHub.

**Current decision: M5_SOURCE_ONLY_SIZE_PROFILE_READY, M5_GEOMETRY_UNKNOWN, FEM=0**. Next P10JN prepare a **distinct one-shot guarded Windows M5 mesh-only** with pinned M4 and source hashes, same CAD/10 seeds, Gmsh4.15.2, 3D C² callback, all-phase visible P10JH heartbeat≤30s (including preflight and evidence packaging) and negative silent-child test. Native single mesh attempt, after evidence independent D031 all curved Tet10 and D029 actual near-polar N/S Veff ratios in [.50,.75], each Neff≥30. D030 neighbour q only diagnostic. Do not repeat consumed P10IY mesh or P10JF FEM markers. Only then decide first M5 physics.
