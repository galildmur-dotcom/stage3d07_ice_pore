# P10OJ — first M15 geometry-only candidate from true M14−M13 mechanical 4D differences (2026-11-27)

## Scientific source

P10OI independently verified 43,236 aligned signed 4D records for real M13/M14 physical runs. Both used an identical 101-file production solver source manifest, R/EDV_VAR/xi=0, 36×25 s = 900 s, analytic same-mesh adjoint. Integral D_R jpeak changed from 2.367223100058 to 2.375881030306 m^-1 (+0.365742%), but L1 per-bin difference is 0.662266817373 m^-1, with polar bins 0+9 accounting for ~32.7%. Thus scalar cancellation masks localized residuals.

The M15 proposed spatial κ grid has 10 radial × 10 latitude × 12 cyclic-longitude bins. Raw priority = sum over all 36 times of |Δ mechanical_total| + 0.25 |Δ mechanical_explicit|, using actual **M14 minus M13** signed 4D rows, not synthetic or thermal estimates. Longitude is averaged in pole caps; separable radial/latitude/periodic-azimuth smoothing [0.25,0.50,0.25], [0.2,0.6,0.2], [0.2,0.6,0.2]. Radial attenuation outside B6 and fifth-order smoothstep interpolation C2. κ ∈ [0,1], κ_max = 1.

M15 additional *nominal characteristic volume* target = -30% at κ=1; incremental edge multiplier (1-0.30κ)^(1/3), min 0.887904. This is a *smooth empirical adaptation priority*, not certified FEM a posteriori error.

## Prepared one-shot Windows Gmsh-only program

[Download P10OJ M15 candidate Windows package](https://chatgpt.com/library?file_id=libfile_694b416c5eb48191b4bf84d377ee9f43&account_id=personal)

`P10OJ_M15_CAD_HIGHORDER_WINDOWS_ONE_SHOT_20261127.zip`, 12,696,129 bytes, SHA256 `77128464318ac7e58764aae265c3f064b56a9eed30273c783ef8f426470b9804`.

- Includes exact accepted M14 parent mesh pinned SHA `9ee7de89b013bff50cb9b5f7ec0b87529af87751aca6bfd27d372b541fd4ea71`, complete cumulative CAD size-field dependencies and new real-4D κ CSV SHA `baa642c732a5d989aa209d570053e157b3344f20e29655701cd4fece4cbfedd8`.
- Source-only preflight **PASS**: all 57 pinned files, 3 transitive GEO includes, no Gmsh, no FEM; new C2 field audit PASS on 960 grid-center samples plus randomized seams.
- Windows double-click 01 preflight then exactly once 02 Gmsh CAD Tet10 generation; write raw MSH2.2, Gmsh 4.15.2 `mesh.optimize('HighOrder')`, then native quality metrics minSICN ≥0.20, minSJ ≥0.40, gamma ≥0.15, minDetJac >0 and boundary Tri6/nodal displacement audit. Monitored every 15 s, 3600 s cap, 12 GiB max, no FEM. Both per-folder and LOCALAPPDATA profile one-shot markers uniquely identify P10OJ/M15, distinct from consumed older markers.
- Operator sends `P10OJ_M15_UNVERIFIED_EVIDENCE.zip`. Even native PASS is **not geometry acceptance**: must then independently audit curved Jacobians, topology and Gmsh reimport D029/D031 before permitting physical FEM.
- Package integrity CRC PASS; local Linux Python compilation PASS. Native Windows Gmsh execution has **not** happened.

**Status:** `P10OJ_M15_GMSH_ONLY_PREPARED_NO_MESH_NO_FEM`. No M15 physical result exists.
