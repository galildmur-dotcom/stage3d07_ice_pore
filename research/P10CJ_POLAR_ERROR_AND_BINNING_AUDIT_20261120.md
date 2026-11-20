# Stage3D07 / P10CJ — независимый анализ полярных межсеточных различий после P10CI R1

Дата: 2026-11-20. Область: `D_R jpeak`, механическая составляющая, `EDV_VAR`, срез `t=900 s`, диагностический слой **только 20–100 мкм от поверхности поры**, десять полос равной ширины по `μ=cos θ`. Весь домен B6, φ-зависимость и тепловая компонента здесь **не** анализировались как пространственные поля. Статус: **READ-ONLY SCIENTIFIC AUDIT; FEM=0; M1=.msh NOT CREATED**.

## 1. Вход и независимая проверка

- Пользовательский оригинал: `P10CI_EVIDENCE.zip`, SHA-256 `8ff592f3d7696975e41b76946df6d438a378e816e04d56e532f0549bf2366e96`; CRC ZIP `5/5 PASS`.
- P10CI R1 `P10CI_RESULT.txt`: `RESULT=P10CI_MESH_ONLY_GEOMETRY_OK_NO_FEM`, `PHYSICAL_FEM_RUNS=0`, `SOURCE_MESH_WRITES=0`, `GMSH_REMESH=0`, `MESHER_CALLS=0`, `MESHES_PINNED_SHA_PASS=3/3`, 600 rows in 20–100 мкм, 30 rows in 0–20 мкм, 12 summary rows. Independent reconciliation with P10CH: **600/600 exact (radial, polar) joins**.
- P10CI 5 input text SHA-256: main 600-cell CSV `db22675c116b1d151e86c73726cc4e2aeba21bcb4c41c099ee4e5d2e4d3e9f61`; wall 0–20 CSV `5cf06f11a9221cfee20e725cadf0d25b858475f67b897fd7246a41f5e745777d`; group 12 CSV `265daba52a12515c18a19640be92ff8a6db35c24332fe9603cec1a92f6b74950`; mesh count CSV `4c6da8910f96eacd75179c0415197cd0c5b47fafca77b07e212561aea844b788`; result TXT `c535b7bc6794e23f199420b8d7d53be84bf652484e076e0d3a48233ef3db7f7d`.
- Independently pinned original P10BB QP CSV SHA-256: `H4W4B2` `219b237e42305f1e4db3089f6501bdd59034dc664f9eee83c5bdc0888e15d447`, `H4W4B20` `3803ed656045384727109952c9331c4e073e4cec9f718a3a7770ecf3a28bd1be`, `H4W5B2` `8ad499250082e919942e8ea105ed0b21463cfd5083085af3f004ee293294c11c`; P10BE H2 dt50−25 CSV `e16a580d4935580b6b5228ce3f10edd80e67534b2306ef73c8b9fb77df0ffc7e`. P10CH 200-cell indicator SHA-256 `84b738960d712ba11eca880a86f98782905dc6dcc6cd3c72c70e4c97c42406c3`.

## 2. Реальная геометрия трёх сеток, без повторного расчёта

| Параметр | H4W4B2 | H4W4B20 | H4W5B2 |
|---|---:|---:|---:|
| Nodes | 367823 | 449522 | 393998 |
| Tet10 | 261091 | 323052 | 275549 |
| Tet10 corner-centroids 20–100 мкм | 29288 | 29577 | 35331 |
| Tet10 corner-centroids 0–20 мкм | 18518 | 18525 | 26465 |

P10CI quality uses **only four straight-corner vertices of each curved Tet10** (not the quadratic map at Gauss QP). In 20–100 мкм: no negative straight-corner tetrahedra, no quality `q<0.1`; every coarse Tet10 intersects at least one 3–5 мкм P10CH radial sub-bin boundary by its four corners (600/600 aggregated cells have crossing fraction 100%). This is geometric bin support mismatch, **not** a diagnosed QP derivative bug. Actual curved Tet10 Jacobian positivity still NOT CHECKED.

Weighted H4W4B2 5th-percentile corner shape quality: polar bands μ=0/9 `q05=0.54832`, middle μ=1…8 `q05=0.55720`. 90th-percentile corner azimuth span: `18.42°` polar vs `5.50°` middle; near poles azimuth as coordinate is poorly conditioned, but a wide φ span in a polar cone does not by itself mean physical geometric distortion. Percent of corner-centroid tets crossing a polar-band boundary is **lower** at poles `8.95%` vs middle `27.17%`; φ-sector occupancy covers 12/12 sectors in 198/200 H4W4B2 cells. There is no evidence from these proxies of catastrophic polar tet quality.

Spearman across 200 bins of `|Δ_bulk|` and φ-span is 0.674 (H4W4B2), 0.680 (H4W4B20), 0.684 (H4W5B2). After within-polar-band rank adjustment it becomes −0.052, −0.053, −0.010 respectively. Correlation is mostly **confounded by polar location**; it does not prove φ span drives mismatch. Corner-quality `q05` globally correlates near zero with `|Δ_bulk|`.

## 3. Физический сигнал, абсолютное и относительное несовпадение

The baseline H4W4B2 **absolute signed-cell mechanical contribution sum** in the two polar μ bands is `0.7097417603 m−1` vs `0.0909037421 m−1` in the eight middle bands: **88.6462% absolute mechanical signal** belongs to poles. This is a sum of absolute cell contributions, not the absolute global derivative or signed component. P10CH two-pole share of *spatial* `Σ|Δ|` is 87.00575% (H4W4B20 bulk), 87.79656% (H4W5B2 wall). Therefore polar dominance of absolute mismatch occurs alongside, rather than drastically exceeding, polar dominance of absolute local signal.

Compute each group's relative mismatch as `Σ_cells |I_other−I_base| / Σ_cells |I_base|`, not relative mismatch of a nearly cancelled signed sum:

| Pair; 20–100 мкм | Polar μ0/9 | Mid μ1…8 |
|---|---:|---:|
| H4W4B2→H4W4B20 bulk | 3.9528% | 4.6092% |
| H4W4B2→H4W5B2 wall | 5.0902% | 5.5241% |
| H2 temporal, dt50→25, baseline dt25 | 1.8305% | 0.8588% |

For these spatial pairs the relative L1 at poles is **not greater** than in middle bands, unlike H2 temporal comparison (different mesh and experiment). Neither metric is the exact continuum error. The high physical derivative at poles could be stress/load/adjoint concentration, constrained by boundary conditions; mechanism is not established by these data.

## 4. Signed radial bin compensation — sensitivity of an error indicator to bin width

For each of the 10 μ bands, **sum signed cell differences before modulus** when aggregating the 20 finely resolved radial sub-bins. The same numbers are not recoverable from the absolute-value heatmap alone.

| Comparison | 200 fine bins Σ\|Δ\| (m−1) | 2 shells ×10 μ (m−1) | 1 shell ×10 μ (m−1) | Retained in 1-shell |
|---|---:|---:|---:|---:|
| Spatial bulk H4W4B20−H4W4B2 | 0.0322446414 | 0.0037125699 | 0.0027908761 | **8.6553%** |
| Spatial wall H4W5B2−H4W4B2 | 0.0411491493 | 0.0139462758 | 0.0048800695 | **11.8595%** |
| H2 time dt50−dt25 | 0.0227496541 | 0.0184356401 | 0.0043302987 | **19.0346%** |

Here “2 shells” means 20–50 and 50–100 мкм (boundary at 50 мкм), and “1 shell” means 20–100 мкм. Respectively **91.345%, 88.141%, 80.965%** fine-bin absolute L1 cancels at the one-shell scale. Spatial Δ flips sign 8–15 times per 19 radial adjacent-bin transitions, depending on μ and comparison. This is directly observed *redistribution and cancellation*; physical fields may themselves have signed radial structure. Coarsening does NOT establish an accurate solution, and coarse L1 cannot substitute for fine spatial error or full shape derivative balance.

## 5. A quantitative quadrature-bin occupancy diagnostic; not a physical correction

Use independent primary P10BB QP cell integrals `I0`, `I1` and QP cell volume `V0`, `V1`. As a **descriptive proportionality prediction only**, define `ΔVpred = I0 (V1/V0−1)` for observed signed `Δ=I1−I0`. Bulk: corr(Δ,ΔVpred)=`0.84253`, uncentered 1−SSE/ΣΔ²=`0.70829`; wall: `0.86812`, `0.75320`. If integrals are *diagnostically* rescaled to the same cell QP-volume proxy, `I1*(V0/V1)−I0`, their Σ|Δ| falls by `47.46%` bulk and `50.68%` wall. **This rescaling is not a valid correction to the discrete adjoint, not an error estimate, and does not explain the same-mesh H2 temporal mismatch.** It suggests testing sub-bin assignment and QP support at source before optimizing on the fine-bin raw L1 alone.

## 6. Decision and next uniquely bounded stage P10CK

P10CI R1 is now **COMPLETED, verified as mesh-only**. P10CJ is **COMPLETED, read-only independent analysis**. Strong poles may reflect a real sensitivity of the shape-adjoint kernel, its discretization, and/or local QP bin redistribution: still an open scientific question, not established singularity or Jacobian failure.

Next **P10CK (safe offline / unit-only)**: (1) read actual curved Tet10 mapping/QP Jacobian and numerical φ winding/sector from pinned original source or compact QP geometry if present; no modified Windows original; (2) design and test a **multi-resolution signed 4D accumulator** `G_{b,n}^{explicit/equilibrium/EDV/thermal-mass/thermal-diffusion/thermal-Robin}`, boundary terms and sum closure, for `(d,μ,φ,t)`; ensure φ integration/near-pole coordinate invariance and 20→2→1 radial conservation on synthetic/test data; (3) draft a **quality-gated adaptive M1 size field** based on a robust multi-scale indicator, not solely 3–5µm noisy bin `Σ|Δ|`, preserving wall geometry and min positive curved Jacobians. Constrain mesh-only planning; no `.msh` generated, no physical FEM launch, no approval for M1–M4 per D-017. A future physical adaptation run requires separate explicit user authorization, pinned SHA/build/source/output, resources and GO gates.

Artifacts: independent `p10cj_evidence_analysis.py` (SHA gate and cell joins), `P10CJ_INDEPENDENT_AUDIT.txt`, `P10CJ_MESH_QUALITY_VS_POLE_MISMATCH.png`, `P10CJ_RADIAL_BIN_CANCELLATION.png`. Exact user ZIP retained with chat upload, primary ZIP bytes not yet mirrored to GitHub. Plot data restricted to available 2D `(d,μ)` projections, **not** the requested full 4D `(r,θ,φ,t)` physical decomposition; do not label them 4D FEM.

Reproduction: Python3 with NumPy/Matplotlib; use `python3 p10cj_evidence_analysis.py --root <data-root>`. Put the five P10CI text members under `<data-root>/P10CI_EVIDENCE_READONLY_20261120/`; the P10CH 200-cell CSV at `<data-root>/P10CH_M1_OFFLINE_CANDIDATE_200CELLS.csv`; and the pinned P10BB/P10BE primary CSV under the two `stage3d07_readonly/` subpaths embedded in the script. Any missing/wrong SHA or key aborts. Outputs write only inside `<data-root>`. This script does **not** parse or modify `.msh`; the P10CI Windows R1 input produced those aggregated corner metrics.
