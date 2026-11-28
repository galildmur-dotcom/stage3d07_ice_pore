# P10PO M21 narrow poles mesh accepted; P10PP first full4D FEM prepared (2026-11-28)

Evidence `P10PO_M21_COMPLETE_MESH_AND_AUDIT_EVIDENCE.zip`, SHA-256 `10a810082126d281166cb5eb25cbf760fb762f5ff81cb3928596b6cc75b67a26`. CRC PASS, one mesh attempt, FEM attempts 0.

## Accepted M21
- Status: `ALL_GATES_PASS_M21_NARROW_POLES_CANDIDATE_REVIEW`; independent `PASS_ALL_GATES_CANDIDATE_M21`, `localization_gate_pass=true`.
- Exact accepted Tet10 mesh SHA-256: `0908d7f66e3db2e3880089f245872a854c22f67dc6bee3ec87924131e7039dee`.
- 65,231 nodes, 43,774 Tet10, 6,048 Tri6 pore.
- Gmsh `HighOrderElastic` executed (9.44s), boundary topology and coordinates unchanged, physical groups 2–9 correct.
- Independent curved detJ at 27/343/729 QP, 0 nonpositive. Gmsh reimport quality minSICN `0.28524419545638735`, minSJ `0.766022084626518`, gamma `0.16015872545577112`, minDetJac `6.514511661802098e-15`: PASS.

## Actual localization M20→M21
| Distance from closest physical polar axis | M20 edge median (µm) | M21 (µm) | Ratio |
|---|---:|---:|---:|
| 0–10° | 29.94224 | 25.46323 | 0.850412 |
| 10–20° | 30.75783 | 28.72793 | 0.934004 |
| 20–30° | 32.46467 | 32.44686 | 0.999451 |
| 30–40° | 44.48957 | 44.13209 | 0.991965 |
| 70–80° | 318.69201 | 318.92152 | 1.000720 |
| 80–90° | 314.25566 | 315.45292 | 1.003810 |

**The user's no-blur requirement is satisfied in the actual serialized mesh**, not just the proposed size function. The inherited M20 broad baseline remains; only the new M21 increment is localized.

## P10PP first physical M21 (pending user execution)
ZIP `P10PP_M21_FIRST_FULL4D_WINDOWS_ONE_SHOT_20261128.zip`, SHA-256 `8ed14646ad6e1984316c0b7ddefcd459599d353d95766d6797840609550ede8f`.

Exactly the original 101 pinned physical solver files; analytical Tet10 shape derivative R, EDV_VAR, GH3, jpeak B6 5mm, 36×25s, full signed 4D independent closure and two-term explicit split. Accepted M21 mesh and reports exact-SHA pinned, physical preflight rechecks curved 27QP and localization. No CAD/mesh; no geometry central FD; no PowerShell. One irreversible M21 physical marker, 65s pre-marker watchdog test, 15s progress, 12GiB RAM, 3h runtime cap, 7GiB output cap, >=11GiB free on G:, projected complete forward cache `3.9812 GiB`.

User launches `01_P10PP_ONE_M21_FULL4D_FEM.cmd` exactly once and sends `P10PP_M21_FIRST_FULL4D_EVIDENCE.zip`. **Not yet executed.**

No scientific claim of mesh-independent physical derivative until signed4D M20→M21 comparison.