# P10OM/P10ON — M15 HighOrderElastic independently validated, native reimport pending (2026-11-27)

## P10OL results

Received `P10OL_M15_THREE_OPTIMIZERS_DIAGNOSTIC_EVIDENCE.zip`. Source M15 SHA `fe16a9a0cff4a6496030e5b9c02dd7cadacaa8a2ac7754a5395518e98fe2eeb9` had minSICN 0.150975 and minSJ 0.314690 (failed). Gmsh 4.15.2 optimizer trials on independent copies:

- **HighOrderElastic** exit 0, ~5.6 s, candidate SHA `ad793c835bf3a3dcb92187f05da9d3dad5a2b4651a3b7cc23c0d2857054d4ada`, 20,380 Tet10. Optimized minSICN **0.26247598649995735** (threshold 0.20), minSJ **0.5896530140647129** (0.40), gamma **0.17359489143286277** (0.15), minDetJac **8.556134369918346e-14** (>0), native all pass.
- **Netgen** exit 0, did not improve the failed minima; no geometry acceptance.
- **Relocate3D** completed its node relocation (~8.8 s) but subsequent HighOrder began 6,578 patches, exceeded 900 s, worker stopped by watchdog with code 1. No candidate/accepted result. No retry allowed.
- No FEM and no new mesh generation.

## Corrected independent boundary audit

P10OL's first guard wrongly reported `boundary_max_m = 0.087508...` for both HighOrderElastic and Netgen, comparing *node IDs* before/after a Gmsh reimport/optimizer that renumbered them. This was a **false positive**. Independently parsed all three MSH2 files and compared 6,342 boundary-node coordinates via nearest-neighbor bijective mapping, then mapped each Tri6 face connectivity by physical tag. **Max boundary displacement exactly 0 m** for HighOrderElastic and Netgen; each physical surface Tri6 connectivity set matches source exactly up to relabeling. Distinct source and Elastic node labels must not be interpreted as material displacement.

## Independent curved Jacobian and topology

Using standalone mesh parser and Tet10 Duffy quadrature on 20,380 HighOrderElastic Tet10:
- 27 QPs/tet (550,260 samples): minDetJ 8.576483803238458e-14, nonpositive=0;
- 343 QPs/tet (6,990,340 samples): minDetJ 8.560312623512945e-14, nonpositive=0;
- 729 QPs/tet (14,857,020 samples): minDetJ 8.558719445033557e-14, nonpositive=0.
- Integrated solid volume 0.00017999581221305212 m³, consistent across quadratures. Finite sampling is not proof of positivity at every point.
- 29,925 nodes; 20,380 Tet10; physical Tri6 counts tags2..9 = 184,182,156,156,156,156,1824,354.
- All 2,814 external corner faces match physical surfaces 2–8; all 354 physical tag9 interface faces are internal; 39,353 internal face pairs, 0 nonmanifold. Pore Tri6 closed: V=914, E=2736, F=1824, Euler=2; all pore corner-edge incidences=2. Independent status PASS.

## Next read-only native gate (P10ON)

M15 HighOrderElastic has **independent geometry evidence PASS** but is **not yet declared fully accepted** until serialized candidate reopens natively in Gmsh 4.15.2 and D031 canonical quality passes. Prepared source-only Windows one-click reimport:

[Download P10ON M15 reimport](https://chatgpt.com/library?file_id=libfile_5033ed4bf1988191aa192f65d5ac0f8b&account_id=personal)

`P10ON_M15_ELASTIC_GMSH_REIMPORT_20261127.zip` (1,431,779 bytes), SHA256 `189c5d40701661b3d38c40ab610252158b4ce707ea2c0168af40a293ce311291`. Exact accepted-candidate MSH SHA pinned; all three independent JSON QA files bundled. Double-click `01_P10ON_REIMPORT_ELASTIC_M15_D031_NO_FEM.cmd`; return only `P10ON_M15_REIMPORT_D031_RESULT.json`. No mesh generation, optimization, physical FEM or one-shot consumption.

Only after this final gate may prepare the **first M15 real full4D FEM+analytic adjoint** with new unique marker, same physical protocol R/EDV_VAR/xi0/36×25 s, and compare M13→M14→M15 signed 4D fields.
