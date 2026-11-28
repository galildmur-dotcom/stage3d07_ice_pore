# P10HN — real P10HL native Gmsh 4.15.2 lc PASS, original Field[7] test prepared

Date 2026-11-24. User supplied `P10HL_RESULT.json`, `P10HL_LOG(1).txt`, and `P10HL_INSTALL_LOG.txt`. Package installation of `gmsh==4.15.2` finished successfully on Python 3.13, Win64. On actual Gmsh API 4.15.2, a synthetic 5-mm line with background MathEval size 0.5 mm produced:

| Property | User evidence |
|---|---:|
| Protocol status | `LC_EQUALS_BACKGROUND_CONSTANT_PASS` |
| Native callback count | 651 (649 from dim=1) |
| Actual `lc` range | [0.0005, 0.0005] m |
| Max relative `lc` deviation | 0 |
| κ range | [0.013420146, 0.024244950] |
| Returned size range | [0.000499312, 0.000499619] m |
| Nominal local volume ratio | [0.995878, 0.997719] |
| Native line meshing wall time | 0.0605 s |
| Native mesh | 1D: 12 nodes, 13 elements |
| Native 2D/3D/FEM/M2 | **0** |

**Scientific verdict:** the native 4.15.2 callback receives the exact constant background `lc` and successfully applies continuous original mechanical C2 κ. This is valid native proof for the *constant size synthetic test only*, not proof of correct original variable Field[7] or CAD.

## Next bounded experiment: original pinned variable Field[7]

Prepared P10HN Windows ZIP `research/proposals/P10HN_REAL_FIELD7_CALLBACK_1D_PREFLIGHT_20261124/P10HN_R1_REAL_FIELD7_1D_WINDOWS_20261124.zip` (SHA256 `08acdd3d0bd6c8edc100fbe081bf16d89e72a73aa523d78f601257f507899257`; 211,764 bytes). It copies the **exact SHA-checked original** `P10GT_HXT10.geo` file (`f1227074616375c28706e1e55cddde370b9a9fca069aab88513b4313c8239f51`), extracts its unchanged `Field[7].F=StrCat(...)` mathematical expression into an isolated field-only GEO, and attaches it to **one synthetic radial 1D line** in ice. The original CAD, M1 and M2 are not opened or modified.

The callback saves the actual Gmsh `lc`, independent numerical evaluation of the frozen original Field[7], κ, and returned size, explicitly comparing `lc/F7` with both 1 and pinned `Mesh.MeshSizeFactor=0.9378887276834518`. This is a stronger experiment than constant 0.5-mm `lc`; no claim about actual original-CAD meshing is made.

Preparation QA: original source SHA verified; formula source extraction / Python compilation independently worked; mathematical values at test endpoints 0.0004616510070248522 and 0.0075970525806110575 m. ZIP CRC and all bytes checked. Gmsh native run is pending the user's Windows execution. Estimated user runtime 2–30 s (existing Python Gmsh API), potentially 1–5 min for local isolated wheel setup. No FEM or 2D/3D.

Return `P10HN_RESULT.json` and `P10HN_LOG.txt`; for STOP `P10HN_ERROR.txt` or `P10HN_INSTALL_LOG.txt`. Even a positive P10HN result is **not D-025 GO**; actual 3D M2 still requires independent local curved Tet10 343/729 quadrature volume/quality checks and signed 4D physical continuity.
