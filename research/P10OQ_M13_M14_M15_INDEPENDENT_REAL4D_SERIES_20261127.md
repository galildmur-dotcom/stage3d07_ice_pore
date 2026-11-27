# P10OQ — independent real M13 → M14 → M15 4D signed comparison (2026-11-27)

## Real P10OP physics

User evidence `P10OP_M15_FIRST_FULL4D_EVIDENCE.zip`, native manifest `P10OP_M15_REAL_FULL4D_PASS`, exit 0, exactly one physical attempt, accepted HighOrderElastic M15 mesh SHA `ad793c835bf3a3dcb92187f05da9d3dad5a2b4651a3b7cc23c0d2857054d4ada`, 29,925 nodes, 20,380 Tet10, pore Tri6=1,824. Same immutable 101-source solver SHA `20e38ffc44f4499d5114f9d0e714246f93f28d5ca1d14adb1c94bb1552dc940f` and regime R/EDV_VAR/xi=0/B6=5mm/36×25s=900s, 4 threads, fresh forward+same-mesh analytic adjoint. Native runtime 2511.468 s = 41.86 min, peak private 4,345,987,072 bytes ≈4.05 GiB, 2.191 mean busy logical CPUs. Windows heartbeat 168/15s; independent 4D closure PASS, two-term signed explicit CSV QA PASS; no retry, P10OP marker consumed.

## Triple-mesh real physical evidence

| Quantity (m^-1) | M13 | M14 | M15 |
|---|---:|---:|---:|
| D_R jpeak | 2.367223100058 | 2.375881030306 | 2.368364542978 |
| Mechanical total | 2.301048587373 | 2.310016324478 | 2.303617736187 |
| Thermal total | 0.066174512685 | 0.065864705828 | 0.064746806791 |

The scalar sequence is non-monotone. Pairwise global signed differences:
- M14−M13 = **+0.0086579302483 m^-1** (+0.365742%);
- M15−M14 = **−0.0075164873281 m^-1** (−0.316366%);
- M15−M13 = **+0.0011414429202 m^-1** (+0.048219%).

Independently re-read three original P10DD signed 4D CSVs (43,236 entries each) and P10LG geometry+stress 4D splits (43,200 bins each). Verified exact common bin keys/temporal regime, per-bin explicit split closure, numerical global closure to each manifest, correct signed components; no FEM executed for P10OQ.

**Local unsigned differences / cancellation diagnostics**:

| Comparison | L1 sum of absolute common-bin total differences (m^-1) | Share in two polar μ bins |
|---|---:|---:|
| M14−M13 | 0.662266817373 | 32.70% |
| M15−M14 | 0.564019217690 | 30.61% |
| M15−M13 | 0.674760897659 | 37.45% |

The sequential L1 common-bin difference decreases by ~14.84% from M14−M13 to M15−M14, but M15−M13 local L1 remains substantial despite near-identical global derivative. This is a diagnostic of redistribution/cancellation, **not a certified a posteriori error, asymptotic rate or proof of spatial convergence**. Non-monotonicity and strong polar angular contribution remain scientifically material. Geometry/stress split per-cell deltas also included.

## Deliverable and next research step

[Download P10OQ independent triple comparison](https://chatgpt.com/library?file_id=libfile_7c96b90572fc81919cebd163d54ef858&account_id=personal)

Archive `P10OQ_M13_M14_M15_INDEPENDENT_4D_SERIES_20261127.zip` (11,262,050 bytes), SHA256 `6787e5f2c122606a71be0f64190ee13861255944385da321d6591f618a384250`, ZIP CRC pass. Includes three full 43,236-row delta CSVs with explicit geometry/stress columns, radial/time/polar/azimuth aggregates, PNG time-polar signed/absolute difference maps, and audit JSON.

**Next scientific action:** prior to committing another costly M16 FEM, determine whether M15−M14 local differences are dominated by polar location, stress-chain versus geometric normalization, and/or time windows; construct a smooth mechanical-only κ field with mandatory `HighOrderElastic` per D-032 and native+independent quality gates after mesh generation. Do not treat small scalar M15−M13 as convergence.
