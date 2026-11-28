# P10OK — M15 native quality rejection and separate volume-optimizer diagnostic (2026-11-27)

## P10OJ physical mesh evidence

User-supplied `P10OJ_M15_UNVERIFIED_EVIDENCE.zip` contains 3,683,934-byte raw and HighOrder MSH files, byte-identical SHA256 `fe16a9a0cff4a6496030e5b9c02dd7cadacaa8a2ac7754a5395518e98fe2eeb9`. Gmsh 4.15.2 generated 20,380 Tet10, 1,824 pore Tri6 from cumulative CAD size field M2…M14 plus independent true M13→M14 mechanics-based κ_M15 (maximum characteristic volume decrease 30%). Native Gmsh run exit=0, wall 70.574 s, mesh-generation attempts 1, FEM attempts **zero**.

Native D031 quality before and after `optimize('HighOrder')` is identical:
- minSICN **0.1509752510170189**, threshold 0.20; **2 elements fail**;
- minSJ **0.31469012633881044**, threshold 0.40; **5 elements fail**;
- gamma 0.17164221711296643 ≥ 0.15 PASS;
- minDetJac 8.133340383955039e-14 > 0 PASS.
- Boundary physical tag/node connectivity preserved and max boundary node movement 0 m.
- Optimizer reported no exception, but ran 0.052 s and changed no MSH bytes.

**Scientific decision: M15 REJECTED FOR FEM.** Successful Gmsh operation and positive Jacobian are insufficient under agreed 3D shape-quality gate. Do not reuse consumed P10OJ one-shot marker or launch any M15 physics.

The official Gmsh 4.15.2 API documentation explicitly lists independent volume optimization `Netgen`, node relocation `Relocate3D`, and high-order optimization `HighOrder` as distinct operations: https://gmsh.info/doc/texinfo/#gmsh_002fmodel_002fmesh_002foptimize.

## Prepared P10OK no-FEM diagnostic

[Download P10OK Windows program](https://chatgpt.com/library?file_id=libfile_7277d3be52f48191b964ea45141fdd29&account_id=personal)

`P10OK_M15_TWO_OPTIMIZERS_WINDOWS_20261127.zip` (1,426,471 bytes), SHA256 `c0b3b199702bb285d547454fbd6ba6dc5238726eb3eca8b362afa73f2f0e7b39`. Original M15 SHA pinned inside. The one-shot Windows script first preflights and then, on **two separate fresh copies** of saved M15, tries (1) `Netgen` + `HighOrder`, (2) `Relocate3D` + `HighOrder`. Original M15 never overwritten, no CAD mesh generation, no FEM. It records worst 12 elements with positions for each quality metric, physical boundary Tri6 connectivity and maximum node displacement. Independent per-method process failure is logged; no automatic geometric acceptance, no further reruns; caps 900 s per method with 15 s console heartbeat.

Source code syntax and archive CRC were checked locally. Native Gmsh execution must occur on Windows with Python Gmsh API 4.15.2. Return `P10OK_M15_TWO_OPTIMIZERS_DIAGNOSTIC_EVIDENCE.zip`; then audit candidate topology, curved QP and Gmsh reimport D029/D031 before any FEM.
