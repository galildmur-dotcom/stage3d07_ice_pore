# P10OR — M16 M15−M14 real mechanical-4D adaptive Tet10 + mandatory HighOrderElastic (2026-11-27)

## Scientific field

M13→M14→M15 independent P10OQ physical signed-4D comparison `research/P10OQ_M13_M14_M15_INDEPENDENT_REAL4D_SERIES_20261127.md` verified M15−M14: signed global −0.007516487328132249 m^-1, L1 common-bin difference 0.5640192176902566 m^-1, two polar μ zones 30.6135% L1; not evidence of asymptotic convergence.

New 1200-bin κ_M16 from real **M15 minus M14 mechanical** signed 4D changes, not synthetic values: for each (r,μ,φ), sum all 36 times of |Δ mechanical total| + 0.25|Δ mechanical explicit|. Polar caps are azimuth-averaged, then radial/latitude/cyclic-azimuth convolution and fifth-order smoothstep interpolation preserve C2 continuity in the callback. Stronger weight near pore, smooth attenuation to zero beyond B6. κ∈[0,1], κmax=1. Field SHA256 `920c9ac9a0e7fb3601d5b07e01b5edbc56fc945fa7c0aa8671360c374367af16`.

M16 extra **characteristic volume** reduction target 30% at κ=1, corresponding edge multiplier (1−0.30κ)^(1/3); empirical smooth adaptation priority, not certified error. This increment builds on cumulative verified CAD callback from M2…M15. Parent M15 geometry exact SHA `ad793c835bf3a3dcb92187f05da9d3dad5a2b4651a3b7cc23c0d2857054d4ada`.

## Mandatory D-032 optimization

Immediately after one CAD Tet10 generation, write RAW ASCII MSH2.2, then call `gmsh.model.mesh.optimize('HighOrderElastic', force=False)` (not `HighOrder`) and write separate optimized MSH2.2. Verify minSICN≥0.20, minSJ≥0.40, gamma≥0.15, minDetJac>0 and physical Tri6 boundary connectivity/coordinate invariance under node relabeling (coordinate-based fingerprint). **No FEM.** Independently audit curved Jacobians, volume/pore topology and native serialized D031 before accepting M16 or preparing physical FEM. Do not auto-retry one-shot upon stop.

## Prepared Windows package

[Download P10OR M16 Windows one-shot](https://chatgpt.com/library?file_id=libfile_0fe6e51ab4f08191aedc52948e68e697&account_id=personal)

`P10OR_M16_CAD_ELASTIC_WINDOWS_ONE_SHOT_20261127.zip`, 14,156,327 bytes, SHA256 `ee0347ed624ed34695616e2c1e0dca670a5226d9a821bef8e75c19ca0b7fdf15`. Includes 61 SHA-pinned source/geometry/field files; exact accepted M15 parent, full cumulative preceding CAD fields, κ_M16 QA. Local source-only preflight passed on all 61 files/3 transitive GEO includes, M16 field audit passed on 960 grid centers plus random continuity; Python syntax PASS, ZIP CRC PASS. Native Windows mesh attempt **not executed** here.

Operator (no PowerShell): unzip in a fresh directory; double-click `01_P10OR_PREFLIGHT_NO_GMSH_NO_FEM.cmd`, wait PASS, then double-click `02_P10OR_ONE_M16_GMSH_HIGHORDERELASTIC.cmd` exactly **once** (new separate local and LOCALAPPDATA markers). 15 s heartbeat, 3600 s wall, 12 GiB RAM. Return `P10OR_M16_UNVERIFIED_EVIDENCE.zip`; do not run FEM or reuse the marker.

**Status:** `P10OR_PREPARED_NO_NEW_MESH_NO_FEM`. Require actual native evidence, independent D029/D031 and serialized Gmsh reopening before first M16 physical run.
