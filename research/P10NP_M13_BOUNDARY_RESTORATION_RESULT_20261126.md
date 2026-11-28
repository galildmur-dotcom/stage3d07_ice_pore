# P10NP — outcome of restoring boundary coordinates after Gmsh HighOrderElastic

Evidence: `P10NP_BOUNDARY_RESTORATION_RESULT.json`, `P10NP_GMSH_RESTORE_LOG.txt` from Windows Gmsh 4.15.2. Source M13 R2 pinned SHA256 `57403ba43fa299417d519046cebdf50fa4968b670c071a8b7882748b50f51e9c`.

**Status: DIAGNOSTIC_ERROR, not acceptable as M13 R3.** Native `HighOrderElastic` completed in 2.69257 seconds; immediately after optimization native minSICN=.3177166281753681 and minSJ=.6418251241754456, clearing the D031 numerical thresholds. However exact boundary and topology audits fail:

| Diagnostic | After optimization | After restoring coordinates of original boundary-node tags |
|---|---:|---:|
| Total global node IDs unchanged | yes | yes |
| Tet10 element tag set unchanged | yes | yes |
| Tet10 connectivity mismatches by element tag | 5893 | 5893 |
| Physical surface Tri6 connectivity mismatches by tag | 2306 | 2306 |
| Changed global node coordinates | 25489 | 21069 |
| Changed original boundary-node coordinates | 4420 | 0 |
| Boundary coordinates exact by original node tags | no | yes |
| Max same-ID displacement | 87.508 mm | 0.09653 mm |
| Quality evaluation | D031 numerical PASS | `RuntimeError('bad metric minSJ')` |

The huge 87.5 mm same-ID displacement and changed element node lists strongly suggest that **node/element reindexing or connectivity transformations** may accompany optimization; this is a hypothesis, not established by geometric correspondence. Restoring boundary coordinates by unchanged original node tag is **not** a valid reconstruction of original geometric boundary after these changes. The failed `minSJ` assessment means the restored candidate cannot be used. No optimized mesh was written, no FEM or marker.

## Scientific next step (proposed P10NQ)

On the in-memory optimized mesh, audit physical pore surface *geometrically*, independent of node tags: compare point sets and radii about the fixed cavity center, and establish any node permutation with a nearest-position or edge-incidence correspondence. Measure surface-element corner/midside geometry before attempting restoration. Separately classify mismatches in Tet10 connectivity as permutation of element records, permutation of local node indices, or global node-tag reassociation. Do **not** restore boundary nodes, output an optimized MSH, or attempt FEM until these differences are resolved. If the optimizer genuinely changes the CAD surface, investigate CAD-aware local remeshing rather than silently accepting numerical quality.
