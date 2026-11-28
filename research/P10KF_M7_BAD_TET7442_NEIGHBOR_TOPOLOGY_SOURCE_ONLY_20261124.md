# P10KF — local topology of M7 failed Tet10 7442 (2026-11-24)

**Source-only/read-only PASS**. Actual M7 R1 remains D031 GEOMETRY_STOP and D029 ADAPTATION_TARGET_MISS. Never rerun consumed P10KB R1 and never launch FEM on unaccepted M7.

## Exact local geometry of the failed element
Independent read-only Gmsh connectivity and minSICN from the uploaded real mesh M7 `6867fbafefa7efbbd00ce4aaa70a673c5bab40385fa2d0abae2be310a6eb4865`.

- Tet10 **7442**, **minSICN = 0.1626225147** (threshold ≥0.20). Centroid `(0.000877608113, -0.000083362336, 0.029325718610) m`; distance **0.109865 mm** from pore wall; μ **−0.607535** (southern middle latitude, not pole tip).
- **Four face-neighbor Tet10**; all have **minSICN ≥ 0.4044989**. The bad cell has **zero faces on the pore surface**, i.e. it is not a boundary surface triangle. Corner edge lengths spread 0.268–0.562 mm. There is **exactly one** SICN<0.20 among all 11,673 M7 Tet10.
- Nearest of the unchanged ten original embedded pore CAD seeds lies about **1.0132 mm** away from the failed centroid; no direct seed proximity is demonstrated.
- Within 0.65 mm centroid radius from the defect: M7 **172** Tet10, local SICN 5th percentile **0.521726** and one SICN below .20; accepted M6 **158** Tet10, 5th percentile **0.492175**, **zero** below .20. Nearest-centroid physical M6 element has minSICN **0.61825**; note this is not an element-by-element mapping.

**Inference only:** a localized unfavorable tetrahedral topology/remeshing transition is more likely than widespread M7 field discontinuity. The prior P10KE polar collar has weight exactly zero at μ=-.607535 and does not itself repair this element.

## Separate adaptation weakness
The actual P10KC D029 M7/M6 polar Veff ratios were 0.952659 N and 0.935660 S (4.73% and 6.43% volume reductions). P10KE constructed a polar C² collar `κ_R2=1-(1-κ_R1)(1-wθ wr)` with source-only model cube ratios approximately 0.80176 N and 0.80204 S, subject to the **same max 20% local volume reduction**. This is **not a prediction certified for real meshed Veff** and is not a D031 fix.

## Decision and next distinct mesh
- Preserve accepted physical M6, original CAD, ten CAD seeds and all one-shot markers.
- Next distinct M7 R2 mesh-only hypothesis: broaden polar C² collar as P10KE, **without** locally forcing size reductions around bad mid-latitude Tet7442. Treat D031 quality as independent hard gate; do not lower minSICN threshold. If new topology remains poor, source-only study of local CAD/size-transition adjustment before further attempts.
- Windows runner must give independent 15s heartbeats, 65s silent-child preflight and hard resource limits; no FEM.
- After one candidate, independent D031 (minSICN≥.20, minSJ≥.40, gamma≥.15, 27/343/729QP detJ, CAD volume closure) and independently supported D029 actual polar Veff relative to M6. Do not conflate D029 and D031.

Artifacts: `P10KF_M7_TET7442_LOCAL_TOPOLOGY_QA.json` and `P10KF_M6_M7_LOCAL_SICN_NEIGHBOURHOOD.png`. Code: `p10kf_m7_bad_tet_topology_source_only.py`. Gmsh was used in read-only open/query mode only (no `mesh.generate`, no FEM).
