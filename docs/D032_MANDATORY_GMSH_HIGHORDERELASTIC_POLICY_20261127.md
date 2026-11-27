# D-032 — Mandatory Gmsh HighOrderElastic for future Stage3D07 M-series meshes (2026-11-27)

**User-approved permanent policy:** For every future new or adaptively generated 3D Tet10 mesh M(n), immediately after Gmsh generates the mesh, save the unoptimized RAW MSH2.2 snapshot, invoke `gmsh.model.mesh.optimize('HighOrderElastic', force=False)` as a **mandatory optimization stage**, then save the optimized snapshot and evaluate quality. Do not silently substitute `HighOrder` for `HighOrderElastic` as the default. If HighOrderElastic errors or fails any geometric acceptance metric, stop before FEM, preserve evidence, and separately diagnose other methods on copies; never auto-promote a candidate. This policy applies to future M-series construction, not retroactive changes of accepted meshes or replay of consumed one-shots.

**Canonical gate remains unchanged:** minSICN ≥0.20, minSJ ≥0.40, gamma ≥0.15, minDetJac >0; strict Tet10 and physical surface Tri6 tags 2–9; pore/B6 topology; boundary correspondence invariant under permitted node renumbering; independent 27/343/729-point curved Jacobian samples and Gmsh D031 serialized reimport; only then separate first physical FEM with new marker.

## Why this correction matters

M15 original P10OJ Gmsh `HighOrder` did not improve minSICN=0.150975 and minSJ=0.314690. User recalled successful earlier `HighOrderElastic` experience in M13. P10OL trial `HighOrderElastic` improved minSICN to 0.26247598649995735, minSJ 0.5896530140647129, gamma 0.17359489143286277, minDetJac 8.556134369918346e-14, all native PASS. First P10OL `boundary_max_m=0.0875` was a false alarm due to comparing node IDs across reimport numbering; independent tag-invariant geometric comparison proves max displacement zero and Tri6 face connectivity unchanged for all 6342 boundary nodes.

Independent curved quadrature: 20,380 Tet10, no nonpositive determinant in 550,260/6,990,340/14,857,020 points (27/343/729 per tetrahedron); minima 8.57648e-14, 8.56031e-14, 8.55872e-14. Independent face topology: external 2814 matches physical tags2..8, internal physical tag9 354, nonmanifold 0; pore Euler2. Gmsh 4.15.2 serialized reimport user evidence `P10ON_M15_REIMPORT_D031_RESULT.json`: **`P10ON_REIMPORTED_M15_ELASTIC_D031_PASS_NO_FEM`**, 29,925 nodes, 20,380 Tet10, surface tags2..9 counts 184,182,156,156,156,156,1824,354, all quality metrics PASS, mesh SHA `ad793c835bf3a3dcb92187f05da9d3dad5a2b4651a3b7cc23c0d2857054d4ada`.

**M15 geometry is now accepted for a distinct physical FEM stage; no M15 FEM has yet been executed.** Future mesh generation must use mandatory HighOrderElastic, preserving the full gate. Record exact method and native quality before and after in result manifest.

Source evidence: `research/P10OM_M15_ELASTIC_INDEPENDENT_GEOMETRY_P10ON_REIMPORT_PREPARED_20261127.md`; P10OL and P10ON raw evidence. This D-032 supplements the working SOP.
