# P10MY — M13 R1 D031 HOLD: address-specific read-only diagnostics

User-returned `P10MX_M13_R1_GMSH_QUALITY_RESULT.json`, generated with canonical Gmsh 4.15.2 on the exact M13 A mesh SHA `3c0b292007dce69cb70559a215ce7367b6c33fc1f7c46a6ca3396041481a1b1e`, proves **D031_QUALITY_HOLD**. M13 R1 (18,048 Tet10) passes D029 but not full geometry acceptance.

| Canonical quality | Observed minimum | Threshold | Result | p01 |
|---|---:|---:|---|---:|
| minSICN | 0.17776562112858055 | >=0.20 | FAIL | 0.3938935539956561 |
| minSJ | 0.32216307620215057 | >=0.40 | FAIL | 0.7997936177164421 |
| gamma | 0.23919585130994098 | >=0.15 | PASS | 0.36810410813930294 |
| minDetJac | 1.5238275959171504e-13 | >0 | PASS | 3.5845243412913015e-13 |

All measured qualities have zero nonpositive values; D029 found positive curved 27/343/729-QP determinants and near-polar effective volume ratios 0.790733 north / 0.808915 south. Do not silently relax threshold criteria. One-shot M13 R1 mesh attempt is consumed; do not retry. **Physical FEM is blocked.** The outliers appear rare relative to the distribution, but their precise count and location must be measured before proposing a local fix.

The separate `P10MY_M13_R1_READONLY_BAD_TET10_WINDOWS_20261125.zip` package was prepared by `research/tools/p10my_build_m13_bad_tet_readonly.py` and has SHA-256 `fe92699f61e26ca411969192477585349254889f49b5f1522e25e7d41e06d0e0`. The package contains the exact M13 mesh, exact D031 JSON, one-click script and canonical Gmsh 4.15.2 element locator. Run `01_P10MY_READONLY_BAD_TET10.cmd` on Windows; send `P10MY_M13_R1_BAD_TET10_LOCATIONS.json`.

The locator only reads and verifies existing data. It reports all offending Tet10 IDs, centroids, wall distance, polar/middle location and top 20 worst per metric. No mesh generation, FEM, marker, or replacement of prior evidence. After the locator is returned, design a separately identified **M13 R2** local C2 repair; verify new D029/D031 before FEM. Preserve M13 A source and 20% nominal volume step.
