# P10OT M16 independent audit and P10OU D031 reimport, 2026-11-27

P10OS evidence received and verified: candidate `b417aeb71193f38f706e11bf64a365cdc5708ff14580d9460f9bfc3bdf95b972`; RAW `eb34e68c82c042bba6f9a77830983412cba319d0d3fdfdb8fad14dded714256a`; HighOrderElastic 3.4758 s; native minSICN 0.26342805, minSJ 0.74976751, gamma 0.22803947, minDetJac 5.379367e-14, all 0 violations, no mesh.generate/FEM.

Independent Python MSH2 reader (zero Gmsh invocations), P10OT:
- **PASS_INDEPENDENT_READONLY**; 21,683 curved Tet10, 32,155 nodes.
- Physical Tri6 groups 2..9 counts: 184, 182, 156, 156, 156, 156, 2286, 354.
- 3,276 exterior faces exactly equal physical tags 2..8; internal tag 9; no nonmanifold faces or group overlaps.
- Pore V=1145 E=3429 F=2286, Euler=2 and each pore edge incidence 2.
- RAW to elastic: 7,266 boundary nodes, physical Tri6 connectivity and rounded coordinate sets equal.
- Curved Tet10 detJ: 27 QPs/element min 5.382225256e-14; 343 min 5.379752764e-14; 729 min 5.379590297e-14. **0 nonpositive among 23,829,617 QP evaluations**.
- Integrated volume all grids ~0.0001799958119489005 m³, stable.
- Finite sampling is not a formal proof of strictly positive detJ everywhere.
- No FEM.

Next gate: **P10OU** independent native Gmsh 4.15.2 reimport of the serialized candidate. Read-only; no HighOrderElastic repeat, no mesh.generate, no FEM. Windows single CMD and exact SHA, counts/physical tags/four native quality metrics. Delivery ZIP SHA-256 `d21c6ea8979cb3241202f7e92aeaa186b9fd6f2cd8a382d61006a9d977953aab`.

[Windows P10OU ZIP](https://chatgpt.com/library?file_id=libfile_ce66264c3b848191ae6b7514815c8f5f&account_id=personal)

M16 is **not finally accepted** until P10OU evidence is returned and reviewed. No M17 field or FEM yet.
