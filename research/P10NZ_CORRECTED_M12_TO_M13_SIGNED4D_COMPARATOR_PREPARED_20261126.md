# P10NZ — corrected M12→M13 signed4D comparator prepared (2026-11-26)

## Correction to P10NY framing

The preceding accepted **physical** M-series stage was **M12**, not M9. M9 was an earlier source-instrumentation baseline. The primary spatial comparison must be **M13−M12**, with older M9 used only for historical context. The previously written P10NY report proposing M9 as the only baseline is superseded in this regard.

## Verified M12 physical evidence

- Genuine source archive `P10MO_M12_FIRST_FULL4D_EVIDENCE.zip`, Library id `libfile_cc832e812eb8819195597f6ccdf159fd`.
- M12 SHA256 `e3c5c5dc9bbcae3d0b2649e7afd4af49b47f6cb6db63329492975fb920abbd13`; 23,732 nodes, 16,333 Tet10, pore1,032 Tri6.
- Real physical `P10MO_M12_REAL_FULL4D_PASS`, one-shot already consumed. Source pin `20e38ffc44f4499d5114f9d0e714246f93f28d5ca1d14adb1c94bb1552dc940f`; R/EDV_VAR/ξ0/B6=5mm/36×25s; fresh forward + same-mesh analytic adjoint.
- Verified `D_R jpeak = +2.3708381294895258 m^-1`. The archive contains all 43,200 signed4D volume bins and independent `P10LG_EXPLICIT_GEOMETRY_STRESS_4D.csv` two-term bins.

## Comparator

`P10NZ_M12_M13_SIGNED4D_COMPARATOR_WINDOWS_20261126.zip`, SHA256 `ab5280ba4d5c9b45476bb19d658d18f118cd81922dad4852fb435d5f321af1c5`, 5,622,644 bytes, Library id `libfile_5a72146e11588191bea575f1c0b92ecd`.

Bundled actual M12 archive + standalone Python stdlib read-only comparator + one Windows double-click CMD. It accepts exactly `P10NY_M13_FIRST_FULL4D_EVIDENCE.zip` after real M13 FEM; guards CRC, M12/M13 exact mesh SHA, physical PASS status, one fresh forward, same-mesh analytic adjoint, equal pinned solver SHA, physical regime, signed4D 43,200 bins, per-bin two-term closure. Produces signed M13−M12 per-bin CSV and JSON summaries global / 10 radial bins / south-middle-north / 36 time steps. Neither FEM nor Gmsh is invoked by P10NZ.

Quality: package CRC PASS, synthetic 43,200-bin identical M12→M13 comparator test PASS with zero differences. Actual M13 physical results **not yet available**. The separate P10NY M13 one-shot computation is still pending and must run at most once with its existing fresh P10NY marker; do not repeat M12 or M9 FEM. Do not claim spatial convergence before comparing results.
