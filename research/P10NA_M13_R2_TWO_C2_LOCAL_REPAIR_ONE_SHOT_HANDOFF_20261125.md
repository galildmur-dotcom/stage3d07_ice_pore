# P10NA — guarded M13 R2 two-C2-local-repair mesh-only Windows package

**Status:** built, SHA source preflight passed 52/52, Python modules compiled; native Gmsh 4.15.2 **not executed**, no mesh generation, FEM or marker used during preparation. Reproducible builder: `research/tools/p10na_build_m13_r2_guarded_mesh_windows.py`.

Archive `P10NA_M13_R2_TWO_LOCAL_C2_REPAIR_MESH_ONLY_WINDOWS_20261125.zip`, SHA-256 `bb94655add7891d94f28bed5f955b01cd2dffac8d65c46662a7d5f0866197664`.

The unaccepted M13 R1 (SHA `3c0b292007dce69cb70559a215ce7367b6c33fc1f7c46a6ca3396041481a1b1e`) has exactly two D031 failures (Tet tags **9035** and **13346**); D029 previously passed (north volume ratio 0.790733, south 0.808915). The old M13 R1 cross-folder marker is consumed and **must never be reused**.

P10NA retains the exact original rotated 3D CAD, embedded seed directions, all inherited M1–M13 smooth size factors, M11 R2 repair, and M13 A source SHA `5c63f14eb16ae9b2e5eb35b9257fcb17e401e82d53e17e29a787fbfd0ac73383`. The sole new factor is

`h_M13_R2 / h_M13_R1_source = exp(-0.045*(w_9035+w_13346))`

where each `w` is C2: unit on a ball of radius 0.020 mm, quintic `1-S5` to zero at 0.250 mm and identically zero outside. The two supports are disjoint (centers separated by ~1.700 mm). Nominal local volume reduction may be up to 12.63% *beyond* inherited A refinement at each repair core; this is a local geometric quality intervention and **not a new global adaptation step**. It is **not proven** to improve minSICN/minSJ and must undergo new D029+D031.

Windows operations:

1. Extract ZIP into a **new** folder, Python 3, numpy and Gmsh Python API 4.15.2.
2. Run `01_P10NA_M13_R2_PREFLIGHT_NO_GMSH.cmd` (hash-only, no marker). Source QA passed on Linux with `P10NA_guard.py --source-only`; native Windows Gmsh preflight remains to be performed in guarded run before marker consumption.
3. If PASS, run **once** `02_P10NA_ONE_M13_R2_GMSH_MESH_ONLY.cmd`. New *M13 R2-specific* cross-folder one-shot marker, independent 15-s heartbeat, 20-min wall, 8-GiB memory and 250-MiB mesh limits. No FEM.
4. Return exactly one `P10NA_R2_M13_UNVERIFIED_EVIDENCE.zip`; do not retry after marker consumption, even if Gmsh fails. Proceed separately to curved 729-QP D029 and independent Gmsh D031 before any physical FEM.

Do not label an R2 mesh accepted based on successful Gmsh exit alone. If new D031 still fails, identify the actual bad element locations before deciding further changes.
