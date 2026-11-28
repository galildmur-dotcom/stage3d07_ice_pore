# P10MZ — M13 R1: exactly two failing Tet10, source-only M13 R2 hypotheses

Original returned `P10MY_M13_R1_BAD_TET10_LOCATIONS.json` was produced by Gmsh 4.15.2 from exact M13 R1 SHA `3c0b292007dce69cb70559a215ce7367b6c33fc1f7c46a6ca3396041481a1b1e`. Exactly **2 of 18,048 Tet10** violate D031 (0.0111%). `minSICN`: 1 offender; `minSJ`: 2 offenders; `gamma` and `minDetJac`: none. The overall M13 R1 remains **D031 HOLD**.

| Tag | Location of centroid (m) | Wall distance | mu=cos(theta) | minSICN | minSJ | Raw M13 A κ | After C2 polar blend κ |
|---|---|---:|---:|---:|---:|---:|---:|
| 13346 | (-0.000782957, -0.000050549, 0.029348706) | 0.019686 mm | -0.638720 | 0.177766 | 0.322163 | 0.000868 | 0.053943 |
| 9035 | (-0.000081568, 0.000783486, 0.030652969) | 0.023168 mm | +0.638184 | 0.254742 | 0.366875 | 0.002374 | 0.053436 |

**Interpretation:** Neither defect is in the polar core (`|mu|>=0.8`), despite most spatial sensitivity attention having gone to poles. Both sit close to the beginning of the smooth polar transition (`|mu|≈0.638`), and receive only ~1.1% nominal incremental M13 characteristic volume shrink at their centroids. This geometric coincidence is **not proof** that the C2 transition caused the low quality.

The two defect centroids are 1.6996 mm apart, while one (tag 9035, north) lies just 0.1345 mm from the existing M11 R2 C2 repair center (within its 0.300 mm support; old weight ~0.667). The other (tag 13346, south) lies 1.8288 mm from that repair. Therefore a blind repeat or amplification of the M11 fix is inappropriate.

**P10MZ source-only repair hypothesis** (not executed): two disjoint compact C2 patches, radius 0.250 mm, constant core radius 0.020 mm, log-size correction `-0.045 * (1-S5((r-core)/(outer-core)))` in each. Hypothetical additional local volume factor at core `exp(-0.135)=0.8737`, beyond the nominal M13 A volume law in a *small isolated repair region*. The analytic profile is C2 in space and keeps the original M13 A and old M1–M12 factors; its actual impact on Tet10 quality is **unknown**. Even the sign of the minSJ response is not guaranteed. In a separately marked native R2 attempt, check the exact local coordinates, global D029 pole intervals, full D031 criteria, element count and adjacent-volume smoothness before considering FEM.

Script `research/tools/p10mz_m13_r2_repair_source_preflight.py` produces immutable diagnostic `p10mz_m13_r2_source_only/P10MZ_M13_R2_LOCAL_C2_REPAIR_HYPOTHESIS.json` from pinned data with **zero** Gmsh, mesh, FEM and marker use. No M13 R2 mesh package has yet been executed or accepted. The consumed M13 R1 one-shot marker must never be reused.
