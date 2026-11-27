# P10OY: accepted M16 physical signed-4D -> consolidated one-run M17 mesh+audit prepared (2026-11-27)

## M16 physical evidence: P10OW

Received `P10OW_M16_FIRST_FULL4D_EVIDENCE.zip`. Manifest `P10OW_M16_REAL_FULL4D_PASS`. Immutable accepted M16 mesh `b417aeb71193f38f706e11bf64a365cdc5708ff14580d9460f9bfc3bdf95b972`. R, EDV_VAR, ξ=0, B6=5mm, 36×25s, 900s, 4 threads, source revision `P10LM_M9_TWO_TERM_EXPLICIT_INSTRUMENTED_P10LG_V1`.

- fresh same-mesh analytic Tet10 forward+adjoint 36/36, native exit 0; wall 2597.341 s, peak private 4,625,256,448 bytes (~4.31 GiB), 174 independent 15s heartbeats.
- `P10GY_INDEPENDENT_TIME4D_CLOSURE_PASS`: 43,236 signed rows, 43,200 VOLUME cells, (D_R j_{peak}(M16)=2.366412779242022\,m^{-1}).
- mechanical components: explicit -9.285327852258783, equilibrium 8.581679355477569, history 3.0043077232989823; thermal mass 0.0023585070059775263, diffusion 0.06339504571827678, Robin 0.
- independent two-term split `P10OP_TWO_TERM_PHYSICAL_CSV_QA_PASS`: explicit geometry +1.2460342461993799, explicit stress -10.531362098458208 = -9.285327852258805. Per-bin 36×1200 closure PASS.
- Prior M15 full4D evidence `P10OP_M15_FIRST_FULL4D_EVIDENCE.zip`: (D_R j_{peak}(M15)=2.368364542977775\,m^{-1}). Difference M16−M15 = -0.001951763735753 per metre; ~-0.0824% relative to M15. This is evidence-based signed full4D comparison, not a global mesh-error bound.
- P10OW one-shot FEM marker consumed. DO NOT re-run M16 physical.

## True M17 design from paired M16−M15 real signed-4D mechanical

Independent source-only M17 design compared 43,200 matching VOLUME cells, t=25…900 s, spatial radial 10 × latitude 10 × azimuth 12:
`score(r,mu,phi)=sum_{t=1}^{36}(|Δ mechanical_total|+0.25|Δ mech_explicit|)`.
Smooth with 3×3×3 symmetric positive convolution, periodic azimuth and pole-azimuth averaging; C2 quintic interpolation and compact support at 5mm from the existing field class. Normalize max κ to 1; size multiplier `(1−0.30κ)^(1/3)`: up to 30% incremental characteristic-volume decrease at κ=1, no change at κ=0. Retain cumulative M2..M16 size callback, original 10 embedded CAD seed directions. Thermal contribution separately preserved for scientific output but omitted from κ as previously authorized.

SHA-256 M15 full4D CSV `c3c818ff66c893abd324c2dc53ef16ff00920a56242b2ba62e948b6318400df2`, M16 `c35fe4e6ea70b664a5050ecd00a0979904cb6e889cd505da5030f828ced8fb69`, M17 field `d8616c19c488fd57e00a93dcb49a3e77f00a46398241a320bfb588c1417b0ad8`.

## One-click package P10OY

`P10OY_M17_ONE_RUN_HIGHORDERELASTIC_ALL_QA_WINDOWS_READY_20261127.zip` (~24.6MB), SHA-256 `13f4a7779a08a96f0bd7737d4fa01f79557e7438a9b5e85efb1ddcb543906c91`.
[Download](https://chatgpt.com/library?file_id=libfile_55a9a715d4888191b3d9a5e96fe5e5bd&account_id=personal).

**One double-click:** `01_P10OY_ONE_M17_MESH_HIGHORDERELASTIC_ALL_QA.cmd`.

- source-only SHA preflight of 61 immutable historic mesh sources and 4 new source artifacts; exact Gmsh Python 4.15.2; no preflight marker consumption;
- single fresh CAD 3D Tet10 generation with one persistent cross-folder Windows attempt marker; serialize RAW;
- mandatory `gmsh.model.mesh.optimize('HighOrderElastic',force=False)`, save optimized mesh; formerly missing `before_groups,before_nodes=boundary_snapshot()` corrected;
- native four quality metrics and boundary-invariance;
- separate **independent** serialized-MSH2 topology, physical Tri6, curved Tet10 positivity at 27/343/729 QPs;
- separate fresh Gmsh 4.15.2 process reimport check of counts, physical tags, canonical quality. No repeated optimization or generation.
- one evidence ZIP, pass or fail; heartbeat every 15s, mesh wall limit 3600s, audit 1200s, memory cap 12GiB. **Zero FEM**.
- static preflight independently tested on available sandbox with 61 PIN + new SHA source hashes; Python syntax & independent auditor tested on accepted M16. Native Windows M17 Gmsh mesh and QA have **not** been run; awaiting user evidence. No M17 accepted yet.

Next: user runs once, sends `P10OY_M17_COMPLETE_MESH_AND_AUDIT_EVIDENCE.zip`; review and commit acceptance; only then prepare M17 physical same-mesh full4D run.
