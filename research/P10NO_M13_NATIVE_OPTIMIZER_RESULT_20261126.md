# P10NO — measured Gmsh 4.15.2 optimizer experiment

Windows files: `P10NO_HIGHORDER_RESULT.json`, `P10NO_HIGHORDERELASTIC_RESULT.json`, `P10NO_GMSH_OPTIMIZATION_LOG.txt`. The source was pinned M13 R2, 18,004 Tet10.

| State | native minSICN | native minSJ | status |
|---|---:|---:|---|
| original | 0.16294478890105799 | 0.28115937433961596 | D031 HOLD |
| HighOrder | 0.16294478890105799 | 0.28115937433961596 | D031 HOLD |
| HighOrderElastic | 0.3177166281753681 | 0.6418251241754456 | Quality PASS, geometry/topology HOLD |

`HighOrder` changed 4,420 nodes, all boundary nodes. `HighOrderElastic` changed 25,489 nodes, including the same 4,420 boundary nodes. Both returned successfully; the elastic optimizer took 2.755 seconds. Both changed boundary coordinates despite setting `Mesh.HighOrderFixBoundaryNodes=1` (likely discrete-entity behavior; precise cause not established). The earlier checker also observed raw connectivity-array differences; this may reflect reordered element records and **must be checked by global element tag**, not assumed to be a topology change. No optimized mesh was saved or accepted.

Scientific implication: there is a substantial feasible-looking quality improvement in the full high-order optimization **if** boundary geometry can be preserved. Next P10NP explicitly restores the original boundary coordinates in memory through `setNode` after elastic optimization, then evaluates canonical D031 again, alongside topology checks by element identifiers. A failure would motivate a more controlled optimizer or a CAD-preserving remesh. No M13 R3 or FEM is authorized yet.
