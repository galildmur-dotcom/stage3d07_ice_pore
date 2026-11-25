# P10ND — M13 R2 D031 HOLD; minima worsened after local size C2 corrections

Canonical Gmsh 4.15.2 result `P10NC_M13_R2_GMSH_QUALITY_RESULT.json` for exact M13 R2 SHA-256 `57403ba43fa299417d519046cebdf50fa4968b670c071a8b7882748b50f51e9c` reports `D031_QUALITY_HOLD`. Comparison with M13 R1, for which only two elements had failed:

| Metric | M13 R1 minimum | M13 R2 minimum | D031 limit | Result |
|---|---:|---:|---:|---|
| minSICN | 0.1777656211 | **0.1629447889** | ≥0.20 | worse, FAIL |
| minSJ | 0.3221630762 | **0.2811593743** | ≥0.40 | worse, FAIL |
| gamma | 0.2391958513 | 0.2427249592 | ≥0.15 | PASS |
| minDetJac | 1.5238275959e-13 | 1.6517904679e-13 | >0 | PASS |

First percentile: M13 R2 minSICN 0.4011 and minSJ 0.7996 (both comfortably above acceptance thresholds). A few outliers probably dominate the HOLD. However, their *locations and count are unknown* until native localization; a worse minimum alone does not prove that the originally flagged Tet10 are still bad, nor that the two compact C2 patches caused the new minima. P10NB D029 on M13 R2 passed with pole 729QP Veff reductions north 21.22%, south 21.01%.

**No M13 R3 attempt is authorized or prepared at this stage.** Do not adjust acceptance thresholds; both existing one-shot markers (M13 R1 and R2) remain consumed. Do not perform FEM.

`research/tools/p10nd_build_m13_r2_bad_tet_readonly.py` produces `P10ND_M13_R2_READONLY_BAD_TET10_WINDOWS_20261125.zip`, SHA-256 `e4fd217eae83556363c28bef610ebe30e9be4cf086a9d2bf2bea435ebb17a968`. It embeds the precise R2 `.msh`, exact failed D031 result, Python read-only locator derived from previously verified P10ME implementation and one-click Windows launcher. The locator evaluates canonical Gmsh 4.15.2 minSICN/minSJ/gamma/minDetJac for all 18,004 Tet10 and provides all under-threshold IDs, centroids, wall distances, angular coordinates and twenty worst per metric. It does not mesh, smooth, run FEM or consume markers.

User should run `01_P10ND_M13_R2_READONLY_BAD_TET10.cmd` in a **new** Windows folder and return `P10ND_M13_R2_BAD_TET10_LOCATIONS.json`. Only then compare R1/R2 failures geometrically and decide whether local size controls, surface-node positions, CAD seed topology or a different local mesh strategy is justified.
