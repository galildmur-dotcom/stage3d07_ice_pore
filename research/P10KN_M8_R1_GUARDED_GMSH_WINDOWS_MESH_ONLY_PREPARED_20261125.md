# P10KN — guarded M8 R1 Windows Gmsh mesh-only prepared (2026-11-25)

**PREPARED_SOURCE_ONLY_NO_GMSH_NO_M8_MESH_NO_FEM**. User-deliverable `P10KN_M8_R1_GUARDED_GMSH_MESH_ONLY_WINDOWS_20261125.zip`, SHA256 `8849c8f5fd5d97dd1cb94f0bce8cfea6d4a92094b1065b8b37fcee5179668621`, 3,987,631 bytes, ZIP CRC PASS, 33 files, pinned 29 source/data SHA files. Library `libfile_819cd79a4b888191a330325b608561e0`.

The P10KN worker is derived from the accepted **P10KG M7 R2** generator, preserving original rotated 3D CAD, 10 fixed on-pore embedded CAD seeds, volume and surface tags, all historical M2→M3→M4→M5→M6→M7 R2 cumulative C2 fields and distinct polar collar. Exact accepted M7 SHA `875c9177de24612d0078f7a792b4b7641a2e604973cb1353500710c87693bb3d` pinned and checked before any mesh. The only intended physical mesh-size change is multiplication by P10KM C2 incremental factor `h8/h7=(1−.20κ8)^(1/3)` from 1,200 signed4D source bins. Max 20% nominal **element volume** reduction (not 20% linear dimension); source P10KM independent seam/pole/positive shape gate already passed. The worker requests original Gmsh 4.15.2 Tet10-only volumetric elements, Tri6 pore and intact embedded CAD seeds, writes `P10KN_M8_R1_CANDIDATE_UNVERIFIED.msh`.

### User execution, distinct markers

1. Unpack archive to a **new folder**, preserving structure. Execute `01_P10KN_M8_PREFLIGHT_AND_HEARTBEAT_TEST.cmd`: exact SHA29 checks, transitive GEO Include closure, Python gmsh4.15.2 check, true Windows 65s silent-child + 15s independent stdout heartbeat self-test. No Gmsh mesh, no FEM, no one-shot marker.
2. Only after PASS execute **once** `02_P10KN_ONE_M8_R1_MESH_ONLY.cmd`. Before native Gmsh worker, distinct local `P10KN_R1_ONE_M8_ATTEMPT_CONSUMED.marker` plus persistent `%LOCALAPPDATA%/Stage3D07_OneShot_Markers/P10KN_R1_M8_875c9177de24612d_ONE_ATTEMPT.marker` are consumed. Never repeat even if worker fails, since distinct one-shot experiment. Old M6/M7 markers remain untouched.
3. Independent progress lines every 15 s even during native Gmsh silence. Wall limit 900 s, RAM limit 8GiB, log limit32MiB, M8 mesh output limit250MiB. Expect mesh in tens of seconds if similar to M7 R2 (~21 s), but non-guaranteed; preflight 65–75s. No solver build, no FEM.
4. Return one `P10KN_R1_M8_UNVERIFIED_EVIDENCE.zip`, containing worker/guard result, native log, candidate M8 `.msh`, and consumed marker. A candidate is **NOT accepted** until separate P10KO independent D031 curved 27/343/729QP, minSICN≥.20,minSJ≥.40,gamma≥.15, detJ>0, CAD-volume closure, surface tags, embedded seeds, adjacency/size smoothness, and D029 actual north/south Veff M8/M7 acceptable volume ratio (target .75–.85 for 15–25% reduction, when supported) pass. No M8 FEM before geometry GO.

### Independent checks performed here

- `python -m py_compile` new guard, worker, watchdog: PASS.
- Actual `python P10KN_guard.py --source-only`: PASS SHA **29/29**, GEO Include closure **3/3**, no new mesh / marker / FEM.
- Source-only field P10KM `source_bins=1200`, C2, 847 3D sample checks, seam6.1e−16 and poles0 (prior stage). Exact M7 hash checked at build time.
- No native Windows 65s self-test or real M8 Gmsh attempted here; those require user Windows run. No claim of actual future M8 geometry quality.

Pin package builder source [research/tools/p10kn_build_m8_mesh_only_windows.py](https://github.com/galildmur-dotcom/stage3d07_ice_pore/blob/research/p10bb-w5b2-20261118/research/tools/p10kn_build_m8_mesh_only_windows.py). The size-field design source remains [P10KM](https://github.com/galildmur-dotcom/stage3d07_ice_pore/blob/research/p10bb-w5b2-20261118/research/P10KM_M8_SOURCE_ONLY_4D_ADAPTIVE_FIELD_DESIGN_20261125.md). Stop at P10KN delivery. User launches manually and does not require another permission request.
