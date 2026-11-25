# P10MI — M11 R2 FULL_GEOMETRY_GO; first physical FEM package prepared

Date: 2026-11-25. Research branch: `research/p10bb-w5b2-20261118`.

## Read-only canonical D031 result received

Evidence `P10MH_M11_R2_GMSH_QUALITY_RESULT.json` (Gmsh 4.15.2) matches exact M11 R2 mesh SHA256 `b3ad647bf3ac295c87f388782447efd33f880e11e331f497402c6596aca6c726` with 15,055 Tet10, physical tags 2–9, no mesh generation and no FEM.

| Gmsh criterion | observed minimum | acceptance gate | result |
| --- | ---: | ---: | --- |
| minSICN | 0.26451908329153795 | >= 0.20 | PASS |
| minSJ | 0.42289828344732916 | >= 0.40 | PASS |
| gamma | 0.1879201363180416 | >= 0.15 | PASS |
| minDetJac | 2.7563213859840794e-13 | > 0 | PASS |

All four qualities have zero nonpositive element values. Prior independent D029 scan in `P10MG_M11_R2_D029.json` passed CAD closure, physical tags and 27/343/729QP curved Jacobian positivity. 729QP near-pole effective volume ratios M11 R2/M10: north `0.7967152952448513`, south `0.8348759881024829`.

**Decision: M11 R2 FULL_GEOMETRY_GO**, unlike M11 R1 (one D031 failing Tet10). This is only geometric acceptance, not FEM convergence.

## Prepared P10MI physical package

Builder: `research/tools/p10mi_build_m11_r2_first_full4d_windows.py`.

Windows deliverable: `P10MI_M11_R2_FIRST_FULL4D_WINDOWS_ONE_SHOT_20261125.zip` (not committed to Git). Contains the exact M11 R2 mesh and geometry acceptance passport, unchanged SHA-pinned 101 solver files, first preflight CMD then one physical FEM CMD; guarded independent P10MI marker namespace. Physical regime unchanged: R/EDV_VAR, xi0, B6=5 mm, 36×25s, 4 threads. Two-term signed explicit geometry and stress diagnostic retained.

Offline build QA: mesh SHA and full source preflight PASS, C++ C++20/OpenMP syntax check PASS. Actual Windows native silent 65 s watchdog **not yet executed**. Physical FEM attempts **0**, marker unconsumed. User must run preflight, then separately invoke the single one-shot FEM; no automatic retry after failure.

Expected one returned archive: `P10MI_M11_FIRST_FULL4D_EVIDENCE.zip`. Next scientific stage: independent M11/M10 signed 4D comparisons and polar refinement convergence test, without prematurely asserting asymptotic convergence.
