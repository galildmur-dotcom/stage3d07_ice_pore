# P10OE — M14 CAD Tet10 + automatic Gmsh HighOrder Windows one-shot PREPARED (2026-11-26)

**STATUS: WINDOWS PACKAGE PREPARED; NATIVE GMSH M14 NOT RUN; FEM0.** The user explicitly approved automatic high-order optimization after every new mesh generation, before quality checks.

## Locked inputs

- Exact optimized, P10NX+P10OB accepted M13 SHA256 `cf4ff4872b82fe3fd854d0ddcb31144eb69f42e8ddce8b1954f064243cf9f4ca`.
- P10OC smooth M14 priority κ field 1200 cells SHA256 `9a379970ba821eac2222f35c717138b727de7f5b2809b331bdc6fe65e8324e4a`.
- Incremental M14 characteristic volume target `V/V_prev=1-0.35κ`, edge-size multiplier `(1-0.35κ)^(1/3)` (0.866239 at κ=1), composited multiplicatively with verified historical CAD size callback M2→M13.
- Original P10MV cumulative Gmsh 4.15.2, numpy, OCC sphere, 10 embedded CAD points, historical SHA pins retained. Source preflight validated 53 SHA-pinned files and the complete 3-file GEO include chain PASS.

## One guarded Windows operation

Package `P10OE_M14_MESH_AND_HIGHORDER_WINDOWS_20261126.zip`, SHA256 **`21f6e6e066d2f915001004e35216f6a996a7b2be6580181448eafb083242f94c`**, size 11,346,646 bytes, Library `libfile_dad364d17bc08191b2c99fd369836314`.

1. `01_P10OE_PREFLIGHT_NO_GMSH.cmd` only checks sources, M13 and field without consuming marker. Linux source-only preflight PASS.
2. `02_P10OE_ONE_M14_GMSH_AND_HIGHORDER.cmd` ONE attempt on Windows 11: native Gmsh 4.15.2 `generate(3)` Tet10 → save `P10OE_M14_RAW_UNVERIFIED.msh` MSH2.2 → `gmsh.model.mesh.optimize('HighOrder')` → save `P10OE_M14_HIGHORDER_UNVERIFIED.msh` → native Gmsh canonical metrics minSICN≥.20/minSJ≥.40/gamma≥.15/minDetJac>0 and compare all physical boundary node-tag sets and coordinates (≤1e−12 m).
3. Persist fresh P10OE local + Windows profile one-shot markers *before* Gmsh; never repeat consumed attempt. Native worker subprocess independent watchdog 15 s, resource polling caps 2400 s / 12 GiB / 350 MiB mesh; FEM forbidden.
4. Return only `P10OE_M14_UNVERIFIED_EVIDENCE.zip`, which includes raw+optimized mesh where available, guard JSON, native log, worker JSON/error, one-shot marker.

**Caveat:** Native Gmsh not installed in the current Linux workspace. Static Python compilation, exact source SHA preflight and delivery ZIP CRC PASS, but native optimization/quality results are not claimed. No automatic fallback to HighOrderElastic: it requires safely restoring raw CAD-backed mesh, not sequential optimization of a potentially damaged or boundary-modified state. The independent D029/D031 gate is mandatory before M14 FEM or acceptance.

This pipeline choice (generation → raw checkpoint → built-in HighOrder → boundary QA → independent D029/D031 → FEM only on accepted mesh) should be retained for M15+.
