# P10OP — first M15 full 4D physical one-shot prepared (2026-11-27)

## M15 accepted geometry

Received real Windows P10ON reimport result `P10ON_REIMPORTED_M15_ELASTIC_D031_PASS_NO_FEM`, saved optimized M15 mesh SHA-256 `ad793c835bf3a3dcb92187f05da9d3dad5a2b4651a3b7cc23c0d2857054d4ada`, nodes=29,925, Tet10=20,380, pore Tri6=1,824, physical tags2..9 counts 184,182,156,156,156,156,1824,354. Native D031 reimport minSICN 0.26247598649995457 (≥0.20), minSJ 0.5896530140647036 (≥0.40), gamma 0.17359489143286 (≥0.15), minDetJac 8.556134369916378e-14 (>0), all PASS. Independent P10OM curved Tet10 Jacobian at 27/343/729 QPs all positive, 6,342 boundary coordinates and Tri6 connectivity preserved under node relabel, volume topology PASS, pore Euler2, physical B6 internal tags PASS.

Policy D-032: for *future mesh generation*, `HighOrderElastic` mandatory after RAW mesh creation; P10OP uses **already accepted optimized M15**, no new Gmsh operation.

## Delivered Windows physical archive

[Download P10OP Windows one-shot](https://chatgpt.com/library?file_id=libfile_12f26abae5c08191a8bac82883b451ae&account_id=personal)

`P10OP_M15_FIRST_FULL4D_WINDOWS_ONE_SHOT_20261127.zip` (1,848,011 bytes), SHA256 `b483c41e6125f2065f9ae1651284b88a0f803687f95f87a7e420631f274e9456`. Includes exact M15.msh, P10OP geometry acceptance passport pinned to physical M15, same 101-file immutable P10LM instrumented production solver source and manifest SHA `20e38ffc44f4499d5114f9d0e714246f93f28d5ca1d14adb1c94bb1552dc940f`, renamed unique P10OP heartbeat/split auditors, two non-interactive Windows CMD files.

On Linux, independent **source-only preflight PASS**: 101 solver pins, exact accepted M15 SHA, 20,380 Tet10, 36×25 s, curved 27-QP minimum detJ `8.576483803239581e-14` >0. Python source syntax PASS, archive CRC PASS. No FEM or Windows compilation was run here.

Protocol unchanged and directly comparable to M13/M14: R/EDV_VAR/xi0/jpeak/B6 5mm/36×25s (900 s total)/4 threads, same-mesh analytic Tet10 adjoint and independent signed 4D (43,236 rows) plus geometry/stress split (43,200 rows). New P10OP-specific local+profile one-shot markers, 65 s watchdog self-test before marker, 15 s progress heartbeat, wall 5400 s, peak RAM 12 GiB, output 3 GiB. No central-FD geometry.

### Operator

1. Unzip in a fresh Windows directory.
2. Double-click `01_P10OP_PREFLIGHT_AND_WATCHDOG_NO_FEM.cmd`; wait PASS. No PowerShell.
3. **Once only** after PASS double-click `02_P10OP_ONE_M15_FULL4D_FEM.cmd`. Never retry even after timeout/STOP, marker will be consumed.
4. Return one `P10OP_M15_FIRST_FULL4D_EVIDENCE.zip` from `G:\ildar\Stage3D07\LOCAL_RUNS\P10OP_M15_R_DT25_*`; if absent, send manifest and native log.

**Status:** `P10OP_PREPARED_NO_M15_FEM`. Do not claim M15 physical convergence until the actual evidence and independent M13→M14→M15 signed 4D comparison are examined.
