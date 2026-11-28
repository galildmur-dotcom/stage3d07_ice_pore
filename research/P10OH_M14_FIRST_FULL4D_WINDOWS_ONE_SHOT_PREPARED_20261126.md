# P10OH — accepted M14 and first full4D physical Windows run prepared (2026-11-26)

## Evidence and geometric acceptance

Received `P10OG_M14_REIMPORT_D031_RESULT.json` and verified that the serialized optimized M14 reopens in Gmsh without re-meshing or re-optimization: `P10OG_REIMPORTED_M14_D031_PASS_NO_FEM`, `canonical_gate_pass=true`. Optimized M14 mesh SHA-256: `9ee7de89b013bff50cb9b5f7ec0b87529af87751aca6bfd27d372b541fd4ea71`. This matches the independent P10OF mesh hash. 28,096 nodes, 19,271 Tet10. Physical surface counts tags 2..9: 184, 182, 156, 156, 156, 156, 1472, 354.

Gmsh reimport canonical minima: minSICN=0.23658177472062905 (threshold 0.20), minSJ=0.4456403265930177 (threshold 0.40), minGamma=0.1846776238254725 (threshold 0.15), minDetJac=1.3219544268316388e-13 (>0). All pass. P10OF independent curved Tet10 detJ at 27/343/729 points per tetrahedron remained strictly positive; pore Tri6 has Euler characteristic 2, correct boundaries and interior B6. Thus **M14 accepted for a first physical FEM run; this is not a claim of successful FEM**.

## Prepared deliverable

`P10OH_M14_FIRST_FULL4D_WINDOWS_ONE_SHOT_20261126.zip` (1,750,711 bytes), SHA-256 `e3b78a59383fa7d3d8a0cbbd8bc022e43aa6c70a70674b75954d71b5b60e9b98`.

[Download P10OH Windows archive](https://chatgpt.com/library?file_id=libfile_100b768a10988191bc394d5b2c29fe7f&account_id=personal)

Archive includes exact accepted `M14.msh`, 101 SHA-pinned production solver source files, mesh acceptance passport, `01_P10OH_PREFLIGHT_AND_WATCHDOG_NO_FEM.cmd`, and `02_P10OH_ONE_M14_FULL4D_FEM.cmd`. Linux source-only preflight was run without FEM or Windows compilation and passed: `P10OH_M14_PREFLIGHT_PASS_NO_FEM`, 101 files, exact M14 SHA, 19,271 Tet10, 36 steps at 25 s, sampled curved detJ minimum `1.3264922362905562e-13`. ZIP CRC validated.

Physical protocol unchanged relative to M13: `R / EDV_VAR / xi=0 / jpeak / B6=5mm / 36×25s / four threads`, same-mesh analytic adjoint, signed 4D and two-term evidence. No re-meshing and no further optimization. New unique one-shot marker; 15 s heartbeat, 65 s no-FEM Windows watchdog self-test, safety caps 5400 s / 12 GiB RAM / 3 GiB output.

### Operator action (no PowerShell)

Unzip into a fresh Windows directory. Double click 01 to obtain PASS. Only then **once** double-click 02; do not retry even if timeout/failure because the one-shot marker is spent. Return `P10OH_M14_FIRST_FULL4D_EVIDENCE.zip` from `G:\ildar\Stage3D07\LOCAL_RUNS\P10OH_M14_R_DT25_*`; if unavailable, return the manifest and native log.

**Research status:** `P10OH_PREPARED_NO_FEM`. Await real M14 physical evidence before any M13/M14 inference or paper conclusion.
