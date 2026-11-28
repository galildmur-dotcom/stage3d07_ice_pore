# P10KP — verified real P10KM 1200-bin field, source-only (2026-11-25)

**PASS_SOURCE_ONLY_REAL_FIELD_NO_MESH_NO_FEM.** Independent of Gmsh/FEM, imported the exact P10KM 1200-bin source from pinned P10KN delivery and old P10HA coordinates. Input SHA256: P10KM CSV `235fc2e0e31d7e55dbf6d1d3ed4a127ca11903cf12a038ee1561006cc0134766`; P10HA reference `98bc99af9783e14f7800f08ecd04fc6bee8093d0490b359e3a024f4c6c4566a3`. Same P10IU Field implementation, `beta='0.1'`.

P10KP blends existing 4D priority field with exact C2 polar plateau: `kappaR2=kappa0+(1-kappa0)*P(d,mu)`, P=1 for d<=.5mm and |mu|>=.8, C2 taper to zero for d>=1mm or |mu|<=.6. Nominal incremental `h8/h7=(1-.2*kappaR2)^(1/3)`. All 60 center bins per side in predeclared near-p0 (radial0..4, extreme polar mu bin) lie in plateau, although actual finite mesh Veff remains unknown.

| Actual input field and source-center proxy | North | South |
|---|---:|---:|
| Source-center count | 60 | 60 |
| Legacy source support QP weight | 57132 | 74808 |
| Weighted old kappa | .195412857813 | .222158634598 |
| Weighted new kappa | 1.0 | 1.0 |
| Old nominal volume ratio | .960917428437 | .955568273080 |
| New nominal volume ratio | .800000000000 | .800000000000 |

QA: 1200 center bins, 605 independent interpolated Cartesian evaluation samples, exact plateau error0, seam1.2143e-17, pole coordinate error0, kappa in [0,1], nominal volume in [.8,1]. Mathematical unit checked 858 further cases. Read `research/evidence/P10KP_REAL_FIELD_QA_20261125.json` and `research/evidence/P10KP_REAL_FIELD_1200_BINS_20261125.csv`; reproduce with `research/tools/p10kp_m8_r2_actual_field_audit.py` and original P10KN pinned source directory. This is not actual new Tet10 regional D029 measurement; support QP are prior source weights, not measured M8 quadrature.

**Next P10KQ**: generate a new distinct M8 R2 guarded Windows mesh-only package, preserving exact M7 R2 CAD/10 embedded points, cumulative callback and pinned P10KM source, integrating only this P10KP incremental field. New unique R2 markers; real Windows native 65s independent heartbeat preflight; no re-run M8 R1. On user's native evidence check full D031 (Gmsh SICN/SJ/gamma, 27/343/729QP curved detJ, CAD/tags) and actual D029 polar near-p0 Veff M8R2/M7 N,S in [.75,.85] independently before any FEM. No physical settings changed, future FEM remains R/EDV_VAR/xi0/B6 5mm 36x25s and analytic same-mesh signed4D, subject to separate gate.
