# P10KV — M8 R3 first analytic-adjoint signed 4D FEM Windows one-shot prepared (2026-11-25)

**PASS_SOURCE_PREFLIGHT, PRIVATE WINDOWS PACKAGE PREPARED, NATIVE M8 FEM NOT RUN.** Based on successful pinned P10KJ M7 R2 package (same 101-file C++ solver source, source manifest SHA `dc3f1b8d3fef2c7c0982b319225c3046c10567a7d4630649df34ae1f222214fc`), adapt only accepted mesh and guard metadata. Source original M7 P10KJ full4D real Windows evidence had already passed, but that is not evidence of M8 FEM. No old M7 one-shot may repeat.

## Fixed inputs and regime

- Accepted M8 R3 SHA256 `40949482ac74d80ae7ac44c88af527a705650d34c1ffcd0de7cd01dc2bd2fa8d`, 18,331 nodes, 12,546 Tet10, 648 pore Tri6, exact P10KU D031+D029 acceptance passport.
- Historical accepted M7 R2 SHA `875c9177de24612d0078f7a792b4b7641a2e604973cb1353500710c87693bb3d` retained as historical reference; M8 FEM is a *distinct* one-shot with new `P10KV_M8_ONE_SHOT_MARKERS` and exact M8 hash.
- R/EDV_VAR/ξ0/B6 5mm, 36×25s=900s, 4 requested OpenMP threads; fresh forward and same-mesh analytic Tet10 adjoint; no central FD geometry; signed full 4D 43,236 rows checked by the original independent P10GY temporal auditor.
- Windows independent heartbeat every15s, native process CPU/wall and phase telemetry, Windows Job limits 2400s wall, 8GiB private memory, 2GiB output.

## Verified source-only gates

Pinned solver 101/101 SHA PASS; original source manifest unchanged; temporal audit script pinned; `P10KV_M8_PREFLIGHT_PASS_NO_FEM` real mesh SHA/count/curved27QP/tags PASS (test bypassed only Windows-platform requirement in Linux; did not start Gmsh/FEM). Python compileall PASS, archive ZIP CRC PASS. Linux `--run` STOP before FEM marker on platform guard PASS. Independent progress-thread unit PASS (four beats at 0/.2/.4/.6s). The **65s Windows native Job/PSAPI silent-child preflight has not yet been executed**; it is required as first user step. No M8 physical run or M8 solver output claimed.

Private user archive: `P10KV_M8_R3_FULL4D_WINDOWS_ONE_SHOT_20261125.zip`, SHA256 `7e2e63688a42172194c80530297e0f8025dd91f7790ba63bae3e04adfabe6ce6`, 114 files, 2,843,487 bytes. Reproducible builder `research/tools/p10kv_build_m8_r3_full4d_windows.py` requires original pinned P10KJ package and accepted M8 R3 evidence. Do not publish raw forward histories and large mesh as public GitHub artifacts without separate scope.

## User run and independent science after evidence

1. Extract into NEW folder, preserving old consumed one-shots; run `01_P10KV_M8_PREFLIGHT_AND_WINDOWS_WATCHDOG_TEST.cmd` (65–80s), require `P10KV_WINDOWS_NATIVE_HEARTBEAT_SELFTEST_PASS` and exit0. No physical FEM/marker from this test.
2. Only after PASS run **once** `02_P10KV_ONE_M8_FIRST_FULL4D_FEM.cmd`. Estimated 20–35 min on user i7-7700K/64GB; hard wall cap 40min, 8GiB RAM, 2GiB output. Marker is consumed before FEM; no retry after STOP.
3. Return only `P10KV_M8_FIRST_FULL4D_EVIDENCE.zip` from newest `G:\ildar\Stage3D07\LOCAL_RUNS\P10KV_M8_R_DT25_*`.
4. Next P10KW independently verify actual 43,236 signed4D rows, global D_R jpeak, M8−M7 full 4D L1/L2, signed cancellation, per-pole nonpolar and last6 time steps, and process CPU/wall. Spatial convergence is **not** presumed, even if global gradient changes little.
