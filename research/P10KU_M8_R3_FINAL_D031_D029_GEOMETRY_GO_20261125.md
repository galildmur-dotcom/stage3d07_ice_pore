# P10KU — M8 R3 independent final D031 + D029 GEOMETRY GO (2026-11-25)

**GEOMETRY_GO_ONLY_NO_FEM.** This decision combines original real Windows M8 R3 Gmsh mesh evidence P10KR, independent all-curved Tet10 27/343/729QP analysis P10KS, and new independent Windows Gmsh 4.15.2 quality result `P10KT_M8_R3_GMSH_QUALITY_RESULT.json`. It is **not** proof of spatial convergence of any shape derivative and does not authorize a repeated M8 mesh attempt or FEM on a different mesh.

Exact M8 R3 mesh SHA256 `40949482ac74d80ae7ac44c88af527a705650d34c1ffcd0de7cd01dc2bd2fa8d`; 18,331 nodes; 12,546 Tet10; 648 pore Tri6; tags 2–9. Accepted baseline M7 R2 SHA256 `875c9177de24612d0078f7a792b4b7641a2e604973cb1353500710c87693bb3d`. M8 R3 mesh one-shot marker **CONSUMED**, never repeat. No physical FEM on M8.

## Final independent D031 criteria

| Metric | Measured all 12,546 Tet10 | Predetermined criterion | Decision |
|---|---:|---:|---|
| Gmsh minSICN | 0.2612426889247915 | ≥0.20 | PASS |
| Gmsh minSJ | 0.45266249348871035 | ≥0.40 | PASS |
| Gmsh gamma | 0.2407560549698764 | ≥0.15 | PASS |
| Gmsh minDetJac | 6.195489181010888e-13 | >0 | PASS |

Nonpositive quality counts all zero. Independent curved Tet10 determinant minima at 27/343/729QP `[6.282764771199006e-13,6.231844911607066e-13,6.225988889958802e-13]`, all positive. Independent 729QP CAD ice-volume closure `6.815797704007309e-09` (absolute ≤1e-6). Surface tags 2–9 retained; native worker reported all 10 CAD embedded seeds. This completes **D031 GEOMETRY_QUALITY_GO** under the finite sampled/Gmsh adaptive checks (not a theorem of positivity at every continuum point).

## Independent D029 realized polar adaptation

729QP fixed physical support d≤0.5 mm and |μ|≥0.8, identical physical region definitions M7/M8:

| Metric | North | South |
|---|---:|---:|
| M8R3/M7R2 characteristic effective volume | 0.7896489414283336 | 0.7905681533151143 |
| Actual reduction | 21.0351058572% | 20.9431846685% |
| M8 Neff | 934.8321956909 | 955.1743871768 |
| Relative 343↔729 ratio drift | 0.00541198% | 0.10004999% |

Both ratios lie inside predeclared `[0.75,0.85]`, Neff≥30 and quadrature drift≤1%; **D029 ADAPTATION_TARGET_GO**. Do not confuse nominal 20% local size-field reduction with the realized FEM effective volume result.

## State and next experiment

New geometry M8 R3 is accepted for a **separately guarded** FEM calculation, with source/time/regime pinned: R/EDV_VAR/ξ0/B6 5mm, 36×25s, four requested OpenMP threads, primal and analytic Tet10 same-mesh adjoint, no central finite-difference geometry, 43,236 signed 4D rows and independent 15-second heartbeat. One-shot separate marker, Windows 65s watchdog preflight, memory/wall estimates, CPU time vs wall and phase logging. User runs Windows, not this audit. Subsequent independent M8−M7 4D comparison must check global derivative, cancellation, polar/nonpolar and late-time contributions; no claim of convergence before this.

Source QA: `research/evidence/P10KS_INDEPENDENT_QA_20261125.json` and P10KT user native quality JSON (not a newly generated FEM or mesh). Existing M7 and M8 R3 mesh/FEM markers must not be reused.
