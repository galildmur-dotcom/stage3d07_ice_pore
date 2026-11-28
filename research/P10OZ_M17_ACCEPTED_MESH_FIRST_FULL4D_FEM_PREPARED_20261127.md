# P10OY M17 accepted; P10OZ M17 full4D physical one-shot prepared (2026-11-27)

## Reviewed user P10OY single-run mesh evidence

- Guard status `ALL_GATES_PASS_M17_CANDIDATE_REVIEW`, one CAD mesh attempt consumed, FEM attempts 0.
- M17 RAW SHA-256 `b43149da39bddc344748e32d262abd2e3f47a0bc875872456898e76e11c6c18c`.
- M17 **HighOrderElastic** serialized optimized SHA-256 `54eee71ab234ec7c2eeb0dadd87bde7e897209bed828f9cc3153a7bcc5988dfd`.
- CAD+HighOrder worker 84.58s; independent auditor+native reimport 8.01s; total 92.96s; peak 604,196,864 bytes; optimizer 4.6579s.
- Accepted mesh: **24,540 Tet10**, **36,417 nodes**, **2,772 pore Tri6**; physical groups 2..9 counts 184, 182, 156,156,156,156,2772,354.
- Topology PASS: no nonmanifold faces, full external-face correspondence, internal group 9, disjoint physical groups; pore V/E/F=1388/4158/2772, Euler=2, all edges incident twice. Original RAW vs optimized boundary match.
- Independent curved Tet10 detJ positive in 662,580 + 8,417,220 + 17,889,660 = **26,969,460 evaluations** across 27/343/729 points per element; min at 729 QPs = 4.30636036090093e-14. Finite sampling is not a continuous mathematical positivity proof.
- Fresh Gmsh 4.15.2 serialized reimport PASS: minSICN 0.29299225259735945; minSJ 0.6733014946733864; gamma 0.242675840531132; minDetJac 4.305537361888725e-14; zero threshold violations.
- **Decision: M17_ACCEPTED_MESH_ONLY**. One-shot mesh marker consumed, never repeat P10OY.

## P10OZ physical M17

Prepared a separate Windows one-shot full signed-4D analytic FEM archive, copied from accepted guarded M16 version with **no solver-source modifications** and all 101 solver source SHA pins preserved.

- Regime R / EDV_VAR / ξ=0 / j_peak / B6=5mm / 36 steps ×25 sec =900 sec / 4 threads, direct forward + same-mesh analytic Tet10 adjoint; full signed-4D mechanical and thermal, geometry and stress explicit decomposition, independent signed 4D closure.
- Exact accepted M17 mesh embedded, pinned `54eee71ab234ec7c2eeb0dadd87bde7e897209bed828f9cc3153a7bcc5988dfd`.
- Independent P10OY acceptance JSON exact SHA pinned `ca30d21cdbcc7e0d808c7df1ce7dc669d5b2ea65492c5b679f3745dae0a01a72`.
- Preflight source checks, 27QP curved geometry, Windows native silent heartbeat selftest 65sec before one-shot; no FEM in preflight. Actual physical one-shot marker P10OZ distinct in both LOCALAPPDATA and LOCAL_RUNS, consumed before native FEM; no automatic retry.
- 15-sec independent progress. 5400s wall cap, 12GiB process memory, 3GiB output. Return one ZIP from LOCAL_RUNS.
- Local preflight tested with only Windows platform check bypassed (101 sources+mesh/geometry JSON complete PASS); both CMD relative paths verified, Python bytecode compile and ZIP CRC PASS. Windows execution / FEM **not yet performed**.
- ZIP `P10OZ_M17_FIRST_FULL4D_WINDOWS_ONE_SHOT_20261127.zip`, SHA256 `cbdc51adb1946279e506216a4ce5367438d6c7a993c98df76ce089b89008e36b`.
- [Download P10OZ](https://chatgpt.com/library?file_id=libfile_7c6fb8de27b08191af0edc461a975c04&account_id=personal).

User runs 01 preflight then 02 physical only once and returns `P10OZ_M17_FIRST_FULL4D_EVIDENCE.zip`. Upon PASS, derive M18 spatial field from real signed M17−M16 mechanical 4D and continue consolidated one-run CAD+HighOrderElastic+independent QA protocol.
