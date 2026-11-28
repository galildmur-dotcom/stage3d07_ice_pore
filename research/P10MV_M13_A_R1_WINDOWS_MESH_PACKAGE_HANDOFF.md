# P10MV — one-shot Windows M13 R1 mesh package (A only)

Status: **PACKAGE BUILT AND READ-ONLY SOURCE PREFLIGHT PASSED; NATIVE GMSH NOT RUN.**

Package: `P10MV_M13_A_R1_GUARDED_MESH_ONLY_WINDOWS_20261125.zip`, SHA-256 `e7ec364b3506b0777bd11066391b94f56aca3b496bdeece3e288d1e651f28998`. Reproducible builder: `research/tools/p10mv_build_m13_a_windows_package.py`.

The archive carries 53 files (49 hash-pinned source/geometry/mesh evidence files plus Windows wrappers and README), complete original transitive GEO include graph, and self-contained accepted M12 R1 parent mesh. The M13 worker is a **distinct** adaptation of the M12 worker; all inherited M1–M12 factors and the M11 R2 C2 repair remain unchanged. Its only size-law addition is `kappa13 = polar_blend_m8(m13.kappa(position),dmm,mu)` and `incremental_m13 = (1-.20*kappa13)**(1/3)`. Variant A SHA `5c63f14eb16ae9b2e5eb35b9257fcb17e401e82d53e17e29a787fbfd0ac73383`. Variants B/C are excluded.

QA actually performed on Linux: source-only `P10MV_guard.py --source-only` passed 49/49 pinned hashes and the 3-file GEO graph; Python modules byte-compiled; archive CRC verified. Native `gmsh 4.15.2` API, Windows execution and actual Tet10 generation remain **untested**: execute via the separate Windows preflight and single-use guarded mesh step. Preflight does not consume the one-shot marker; the single mesh command consumes an M13-specific profile-level marker across folders immediately before starting native Gmsh. No FEM is included.

User execution instructions:

1. Extract archive into a **new empty Windows folder**, without copying old markers.
2. Launch `01_P10MV_M13_A_PREFLIGHT_NO_GMSH.cmd` (SHA-only, no native Gmsh, no marker). If it passes, launch `02_P10MV_ONE_M13_A_R1_MESH_ONLY.cmd` **exactly once**. The guard also checks `gmsh` Python API version 4.15.2 before consuming the marker.
3. Independently reported heartbeat at ≤15 s (native progress detail unknown), maximum native wall 20 min, RAM 8 GiB, max mesh file 250 MiB. Never retry even if it fails; return the result for diagnosis.
4. Return one `P10MV_R1_M13_UNVERIFIED_EVIDENCE.zip`. **Do not run FEM yet.** Next independent steps: D029 full 729-QP curved geometry and actual volumes; D031 Gmsh quality; only then physical M13 on user approval/SOP.

The acceptance threshold cannot be inferred from the nominal size law. The mesh remains unaccepted until D029/D031 passes, including real volume changes and pole/near-wall quality.
