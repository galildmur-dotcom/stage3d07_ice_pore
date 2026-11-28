# P10KE — source-only diagnosis of M7 R1 D031 failure and weak polar adaptation (2026-11-24)

**Status: PASS_SOURCE_ONLY_NO_NEW_GMSH_NO_MESH_NO_FEM.** M7 R1 remains UNACCEPTED; one-shot P10KB marker consumed, never repeat it.

## Grounded diagnostics from actual M7
Independent P10KC/P10KD: only one curved Tet10 below D031 minSICN≥.20: element **7442**, minSICN **.162622515**, centroid `(.0008776081,-.0000833623,.0293257186)` m, distance **.109865 mm** from pore wall, μ **−.607535**, hence intermediate *southern* latitude, **not north pole**. minSJ .412> .4, gamma .225>.15, 27/343/729 QP detJ positive. D029 actual polar Veff(M7)/Veff(M6) **0.952659 N, 0.935660 S**, only 4.73% and 6.43% reduction versus 15–25% intent.

Direct evaluation of original M7 R1 smooth source κ at the actual bad tet centroid is **0.0018173823**, corresponding to h7/h6 **0.999865** (negligible local size change). Thus the bad-tet appearance is a new mesh-topology / transition effect, not evidence that the local new adaptation drove h sharply lower at that very point. This is an inference, not a proved causal mechanism. D031 and D029 must remain independent.

At the true north pole κ(d=0,.02,.1mm)=**.8103,.6430,.1488**; south=**.1580,.1066,.0313**. The old indicator loses amplitude extraordinarily fast in both polar collars. P10KE independent sampling of 1200 source centers, weighted by M6 mechanical QP supports, gives old volume-cube proxy averages: north **0.95648**, south **0.99201**; these help explain weak observed real mesh response, but do not predict it exactly.

## Candidate P10KE smooth alternative (NOT a mesh)
Keep original accepted M6 mesh and cumulative size callback invariant. Preserve max 20% incremental volume reduction, 0≤κ≤1; change only spatial extent of the polar source, using C² quintic `s5`:
- `wθ=s5((|μ|−.68)/.18)` for polar directions;
- `wr=1−s5((d_mm−.30)/.50)`, flat d≤.30mm, smoothly zero by .80mm;
- `κ_R2=1−(1−κ_R1)(1−λ wθ wr)`, λ∈{.5,.75,1};
- `h_R2/h_M6=0.8^(κ_R2/3)` (source-only cube proxy, not real Veff).

M6-QP weighted *proxy* for polar north/south:
| λ | north cube proxy | south cube proxy |
|---|---:|---:|
| 0 (R1) | .956480 | .992011 |
| .50 | .875283 | .891967 |
| .75 | .837613 | .845806 |
| 1.0 proposed source only | **.801764** | **.802041** |

λ=1 is the proposed broad C² collar **hypothesis**, not a demonstrated actual 20% Tet10 volume reduction. Seam discrepancy 0, pole identity 0, min h7/h6 ≥.92831777; no point exceeds 20% volume reduction. The added collar vanishes at μ=−.6075 bad tet 7442, i.e. **it does not itself fix D031**. Separate diagnosis of local D031 topology is mandatory; never claim geometry GO from this source-only result.

## Next P10KF
Safely investigate 7442's actual face-neighbor topology, localized C² transition/seed geometry and independent quality-preserving alternatives before issuing a **new distinct** M7 R2 guarded mesh-only attempt. Maintain 15s independent heartbeat. On returned real mesh run full D031 Tet10 quality + D029 actual supported Veff relative to immutable M6. Only geometry GO allows later FEM approval; physics still 36×25s with CPU instrumentation.

Inputs pinned: `P10KC_M6_M7_INDEPENDENT_D031_D029.json` SHA `2ef1d1cef8552c788a1d9fb2f2be56f17d71182622359ca94013b25e7813c654`; `P10KD_LOCAL_BAD_TET10_D031.json` SHA `3d2e1c07387eea287c1e17c5305d5aea333291efb4fe97d2ede27dccdc22c05f`; original M7 source SHA `851fd56d8df84b5e6dd9990ac6b5edf56227a39598e7b634a6448b76ef3f4454`.
Artifacts: `P10KE_M7_C2_POLAR_COLLAR_SOURCE_ONLY.png`, `P10KE_M7_R2_PROPOSED_C2_SOURCE_1200_BINS.csv`, `P10KE_M7_R2_SOURCE_ONLY_QA.json`.
