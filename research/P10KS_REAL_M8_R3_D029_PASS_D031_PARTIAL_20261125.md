# P10KS — real M8 R3 mesh, independent D029 PASS / D031 partial (2026-11-25)

**D029 PASS, FULL D031 PENDING CANONICAL GMSH QUALITY API; NO FEM.** Original user evidence `P10KR_R3_M8_UNVERIFIED_EVIDENCE.zip` (not re-run): Gmsh 4.15.2 exit0, protected wall25.024s, native mesh23.497s, distinct R3 one-shot CONSUMED, 2 monitor heartbeats, FEM0. New exact mesh SHA256 `40949482ac74d80ae7ac44c88af527a705650d34c1ffcd0de7cd01dc2bd2fa8d`: 18,331 nodes, 12,546 Tet10, 648 pore Tri6, 10 CAD embedded seeds per worker; all physical tags 2–9. Compare fixed accepted M7 R2 exact SHA256 `875c9177de24612d0078f7a792b4b7641a2e604973cb1353500710c87693bb3d` (17,558 nodes, 12,001 Tet10, 592 pore Tri6).

Independent read-only P10HV curved Tet10 parser with 27/343/729 quadrature over all elements (no mesh generation, FEM0): new min determinant `[6.282764771e-13, 6.231844912e-13, 6.225988890e-13]` all positive; CAD ice-volume closure 729QP `+6.815797704e-9`, tags 2–9 present. Gmsh native log says high-order optimization succeeded, volume worst distortion 0.452662, but canonical Gmsh minSICN/minSJ/gamma have **not** been independently obtained and must not be inferred from that log. Thus **D031 not fully passed**.

## Actual D029 fixed near-p0 regions: d≤0.5mm, |mu|≥0.8

| Metric | North | South |
|---|---:|---:|
| M8R3/M7R2 Veff 729QP | **0.789648941428** | **0.790568153315** |
| Actual reduction | **21.0351%** | **20.9432%** |
| M8 Neff 729QP | **934.8322** | **955.1744** |
| M8/M7 ratio 343QP | 0.789691677091 | 0.791359116680 |
| Relative ratio drift 343→729 | 0.005412% | 0.10005% |
| D029 target [0.75,0.85] | PASS | PASS |

The actual M8 R3 adaptation meets the predeclared **15–25%** target on both sides, unlike M8 R1 (~3%). Do not misread 20% nominal field as exactly 20% realized volume. D029 is a geometric adaptation status, not evidence of convergence of D_R jpeak.

Independent script `research/tools/p10ks_m8_r3_independent_d029_d031.py`, historical reproducible parser `research/tools/p10hv_independent_scan.py`; full QA JSON `research/evidence/P10KS_INDEPENDENT_QA_20261125.json`.

## Next P10KT — read-only Gmsh quality gate

Prepare a *read-only* Windows package with exact M8 mesh and Gmsh Python 4.15.2, using `gmsh.model.mesh.getElementQualities(tags,qualityName=...)` for minSICN ≥.20, minSJ ≥.40, gamma ≥.15, minDetJac >0 and physical tags 2–9. No generation, no consumed marker, no FEM, expected 5–30s and under 2GiB RAM on user PC. Return JSON and decide complete D031 only after independently verified results. Keep FEM blocked until both D029 and D031 pass and a distinct resource-scoped physics attempt is prepared.
