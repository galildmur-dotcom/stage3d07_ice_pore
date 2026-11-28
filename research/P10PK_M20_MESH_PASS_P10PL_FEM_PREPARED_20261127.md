# P10PK M20 mesh acceptance and P10PL physical one-shot preparation (2026-11-27)

P10PK evidence ZIP SHA-256: `81bba6a3174ce8b53799263245bd2515432e9c5e334e28b2ece5a4d6f91218b9` (CRC PASS).

- One M20 CAD mesh attempt; no FEM, no retries.
- Guard status: `ALL_GATES_PASS_M20_CANDIDATE_REVIEW`.
- Exact accepted M20 Tet10 mesh SHA-256: `b568adac49d19f561f8ee6d4c420ff10df51ae32cb8d2e2c1ba46af28d78f8a5`.
- 61,446 nodes; 41,250 Tet10; pore surface 5,598 Tri6.
- Mandatory `HighOrderElastic` actually ran, optimizer elapsed 9.87s.
- Independent topology and boundary unchanged PASS; 27/343/729 QP curved detJ all >0.
- Independent Gmsh reimport: minSICN 0.2860698032, minSJ 0.7018859106, gamma 0.1662535889; zero threshold violations. New standalone physics-package independent mesh QA confirmed 41,250 Tet10, 0 nonpositive.
- Mesh and audits elapsed 163.13s; native peak private 1.05GB.

## P10PL physical M20 package

Archive `P10PL_M20_FIRST_FULL4D_WINDOWS_ONE_SHOT_20261127.zip` SHA-256 `43323d83401c16415b74f0a6e672c78f75d2fc3df0148f586f97e83fd61fe7af`.

- Source manifest 101 files, unchanged, SHA-256 `20e38ffc44f4499d5114f9d0e714246f93f28d5ca1d14adb1c94bb1552dc940f`; exact solver revision `P10LM_M9_TWO_TERM_EXPLICIT_INSTRUMENTED_P10LG_V1`.
- Same analytical Tet10 R shape derivative, EDV_VAR, xi0, GH3, B6 5mm, 36 ×25s, signed 4D and independent audits, no geometry central FD.
- Immutable accepted M20 mesh and SHA-pinned native + independent QA results.
- Distinct irreversible one-shot M20 physical markers under project LOCAL_RUNS and Windows LOCALAPPDATA; 15s watchdog heartbeat, 65s native selftest before FEM.
- 41,250 Tet10 ×27QP ×96-byte history states project a ~3.75GiB forward cache. Cap 7GiB output, minimum 11GiB free on G:, memory 12GiB, wall 3 hours.
- Run via double-click `01_P10PL_ONE_M20_FULL4D_FEM.cmd`; no PowerShell.
- **Not yet executed**. User returns `P10PL_M20_FIRST_FULL4D_EVIDENCE.zip` (or failed-attempt diagnostic), never repeats after consuming marker.

Mesh acceptance authorizes **one** first M20 FEM attempt, not a claim of spatial convergence.