# P10OI independent M13 → M14 real 4D comparison (2026-11-26)

## Source evidence and pass

- P10NY M13 evidence `P10NY_M13_FIRST_FULL4D_EVIDENCE.zip`, `P10NY_M13_REAL_FULL4D_PASS`; mesh SHA `cf4ff4872b82fe3fd854d0ddcb31144eb69f42e8ddce8b1954f064243cf9f4ca`; Tet10=18,004; pore Tri6=1,168.
- P10OH M14 evidence `P10OH_M14_FIRST_FULL4D_EVIDENCE.zip`, `P10OH_M14_REAL_FULL4D_PASS`; mesh SHA `9ee7de89b013bff50cb9b5f7ec0b87529af87751aca6bfd27d372b541fd4ea71`; Tet10=19,271; pore Tri6=1,472.
- Same exact source-manifest SHA `20e38ffc44f4499d5114f9d0e714246f93f28d5ca1d14adb1c94bb1552dc940f`. Matched regime: R/EDV_VAR/xi=0/B6 5mm/36 steps × 25s/4 threads, horizon **900 seconds**, not one hour. Both one physical FEM attempt, fresh forward and same-mesh analytic adjoint, native exit 0, independent 4D closure PASS, independent two-term geometry/stress CSV PASS.
- Independently joined and subtracted **43,236 common signed 4D bin rows** from the two original CSVs, preserving step, radius, polar and azimuth bins; compared sums to native manifests within floating-point tolerance. No FEM was performed in P10OI.

## Result

| Quantity [m^-1] | M13 | M14 | M14 - M13 |
|---|---:|---:|---:|
| Signed total D_R jpeak | 2.367223100058 | 2.375881030306 | +0.008657930248 (+0.365742%) |
| Mechanical total | 2.301048587373 | 2.310016324478 | +0.008967737105 |
| Thermal total | 0.066174512685 | 0.065864705828 | -0.000309806856 |
| Mechanical explicit | -9.421418978740 | -9.338491843433 | +0.082927135307 |
| Mechanical equilibrium | 8.608360743006 | 8.594538395256 | -0.013822347750 |
| Mechanical history | 3.114106823107 | 3.053969772655 | -0.060137050452 |

The **sum of absolute per-bin total differences is 0.662266817373 m^-1**, about 76.5 times the signed difference magnitude; signed global convergence alone masks spatial and temporal cancellation. Polar bins 0 and 9 account for approximately 32.7% of absolute bin differences (0.216531818310 m^-1), which motivates further polar diagnostics. This is a **histogram diagnostic**, not a mathematically rigorous continuous error norm or verified asymptotic convergence order.

M13 wall 2124.314 s (35.41 min), M14 2273.523 s (37.89 min); respective private peak 3.58 and 3.83 GiB, mean busy logical CPUs 2.133 vs 2.141.

## Deliverable and next question

Independent report, 43,236-row difference CSV, time/radial/polar/azimuth aggregate CSVs and polar-time/radial-time PNGs:
[Download P10OI evidence](https://chatgpt.com/library?file_id=libfile_b70452a6005c8191bbd0110934f3ee11&account_id=personal)

Archive SHA-256 `a9c9ac18e8272be1cf393113bb102e9fd4523a356e4f69d7a8101d93a4adc0b0`, ZIP integrity PASS.

**Next research action:** determine spatial localization and sign/cancellation of **mechanical** 4D error, then draft κ∈[0,1] refinement field favoring polar risk regions and smooth transitions for the M15 candidate. Keep the mesh-quality gate and Gmsh high-order optimization before FEM; do not infer asymptotic convergence from M13/M14 scalar agreement alone.
