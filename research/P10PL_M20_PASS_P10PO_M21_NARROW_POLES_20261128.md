# P10PL M20 physical PASS; P10PM localization diagnosis; P10PN/P10PO narrow-polar M21 (2026-11-28)

## M20 real physics
- Attached P10PL M20 evidence ZIP SHA-256: `ab5c98b6f3a3c4576eeb31027b8d8f7ef33f02a73a9f83d8827a067173c0d508` (CRC PASS).
- Status `P10PL_M20_REAL_FULL4D_PASS`; 36 forward/36 analytical adjoint, independent signed 4D closure and explicit two-term QA PASS.
- Mesh M20 SHA `b568adac49d19f561f8ee6d4c420ff10df51ae32cb8d2e2c1ba46af28d78f8a5`, 61,446 nodes, 41,250 Tet10.
- `D_R jpeak(M20) = 2.356542538474087 m^-1` vs M19 `2.3593864685556034 m^-1`, delta `-0.0028439300815166213 m^-1` (-0.12054%).
- Elapsed `6097.6746 s`, private peak `8786386944 B`. No repeat.

## Independent M19→M20 comparison
43,200 signed 4D volume cells, closure PASS; signed absolute cancellation ratio `121.51267045763558`. Fractions: final steps31–36 `0.5187180340548377`; radial first four `0.4698783291122599`; polar mu0/9 `0.24843333912476456`. Source-only report `P10PM_LOCAL_4D_DIAGNOSTIC.json` SHA `571742cf5d4e00fac8bdd7c7c3ac684c4a7d969b19ac852c64fe8ace8d48e74c`.

## New meshing rule: strictly focused M21, NO DIFFUSION of additional refinement
Visual diagnosis was supported by actual surface edges: prior M20 0-10° median 29.94µm, 10-20° 30.76µm, 20-30° 32.47µm; M20's `LAT[-1]=0.9` clamps latitude and creates a 25.84° polar plateau, while incremental kappa remains nonzero even at equator. New local increment does NOT reuse the 10-bin latitude interpolation.

- Core `theta_pole <= 8°`; quintic C2 taper `8°..23°`; exactly zero extra refinement beyond 23°.
- Core normal distance `d <= 0.08mm`; quintic C2 taper `0.08..0.50mm`; zero extra refinement beyond 0.50mm.
- Separate North/South polar caps, no azimuth seam; zero extra refinement at equator.
- At kappa=1, nominal characteristic volume reduction 40%, isotropic edge factor 0.84343. Prior accepted M20 accumulated field remains and cannot be coarsened by this step.
- P10PN independent numeric source-only QA PASS; all 61 historical source pins checked. Gmsh not available in prep environment, **M21 generation and actual acceptance remain pending**.
- P10PO one-shot CAD Tet10, mandatory `HighOrderElastic`, independent 27/343/729QP, topology, Gmsh reimport, and **new actual localization acceptance gate** comparing 10° band surface edge medians of M20 and M21 (new 0-10° median <0.98 times M20; at least 2 percentage points stronger than 70-90°; 70-90° decreases no more than 15%).
- Never repeat consumed M21 mesh attempt, no FEM and no PowerShell.
- Windows bundle `P10PO_M21_NARROW_POLES_HIGHORDERELASTIC_ALL_QA_WINDOWS_20261128.zip` SHA `4e3b17eb07fa4f5a5872860213ecf8ae0463a3afd3c1b145c7873f9ed2118ee9`.
- Send one `P10PO_M21_COMPLETE_MESH_AND_AUDIT_EVIDENCE.zip`. Only if all passes may a physical M21 attempt be prepared.

**Caveat:** 10×10×12 signed4D bins do not resolve a sub-10-degree physical error; narrow M21 is a testable hypothesis per the user's explicit no-blur constraint, not a certified optimal error-driven size field.