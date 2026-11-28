# P10OD — M14 continuous size-field feasibility PASS; no mesh/FEM (2026-11-26)

**Status: P10OD_SOURCE_ONLY_SIZE_FIELD_PASS_NO_MESH_NO_FEM.** No Gmsh 4.15.2 API available in current analysis environment; *do not claim an M14 mesh exists*. This source-only gate follows P10OC signed4D localization.

## Pinned inputs

- P10NX geometrically and P10OB physically accepted optimized M13 MSH2.2, SHA256 `cf4ff4872b82fe3fd854d0ddcb31144eb69f42e8ddce8b1954f064243cf9f4ca`, 26,099 nodes, 18,004 Tet10.
- P10OC 1200-bin proposed κ CSV, SHA256 `9a379970ba821eac2222f35c717138b727de7f5b2809b331bdc6fe65e8324e4a`.
- P10MV original cumulative CAD callback was inspected: M13 generated as a new full CAD Tet10 mesh using historical cumulative size factors; the final accepted M13 required further high-order Gmsh optimization and geometry QA. A naive direct node change or a single unverified extra field would be an unsafe leap.

## P10OD candidate **field**, not candidate mesh

Use the physical radial-distance coordinate `d_mm = (||x-C||−R)*1000`, `mu=(z−C_z)/||x−C||` and periodic φ. Interpolate κ between 10 radial bin centers, 10 equal-μ bin centers, and 12 cyclic azimuth centers with quintic smoothstep `6t^5−15t^4+10t^3` so interval derivatives through order 2 vanish at each knot; average both polar cap rows over φ to avoid artificial azimuth hotspots; smoothly taper κ from 3.5mm to zero at 5mm. Result continuous with C2 scalar coordinate interpolation in this discretized parameterization. The ambient Cartesian regularity is not certified at the exact pole/other geometric singularities and must be audited in native Gmsh before mesh acceptance.

Incremental relative volume `V_target/V_prev = 1−0.35κ`, edge-size callback `h_target/h_prev = (1−0.35κ)^(1/3)`, κ in [0,1]. At κ=1, 35% characteristic volume reduction, edge factor **0.86623910534**; at κ=0 unchanged. This is within user-approved 25–50% maximum refinement zone. In the near-pore geometry, original CAD and physical tags must remain fixed; size field is never a license to move the cavity wall.

Source-only Python tests PASS on pinned input: exactly 1200 bins; 960 spherical-center evaluations; 3000 random cyclic/continuity probes, explicit seam tests; relative volume-edge cube identity error <=1e−12, no out-of-range κ. No FEM, no mesh generation, no marker consumed.

Package `P10OD_M14_C2_FIELD_FEASIBILITY_WINDOWS_20261126.zip`, SHA256 `a49c9d89955333bcd56784dd2d74ffd194e50f8583e54f69dab587806621f129` (1,271,943 bytes), Library `libfile_a3fe01ec7390819186af24a63b7c6647`. Includes pinned accepted M13 mesh, κ, source, QA result, one-click Windows CMD (no PowerShell) and README; ZIP CRC PASS.

**Next P10OE**: construct distinct mesh-only Gmsh 4.15.2 Windows one-shot from original CAD with cumulative accepted stage history + newly pinned incremental M14 field; preserve M13 source and markers; enforce counts, tags, boundary shape, positive analytic Tet10 detJ; collect native quality and D029/D031, optimize high-order only with exact boundary preservation, then separately decide FEM. Source-only P10OD does not authorize declaring an M14 mesh accepted.
