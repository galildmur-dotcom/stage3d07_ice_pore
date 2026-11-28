# P10NM — canonical native Gmsh 4.15.2 diagnostic sweep (2026-11-26)

Input: `P10NM_M13_CONSTRAINED_DIAGNOSTIC_GMSH_RESULT.json` from Windows. The original mesh SHA256 is `57403ba43fa299417d519046cebdf50fa4968b670c071a8b7882748b50f51e9c`, with 18,004 Tet10. **This remains a non-meshed diagnostic series, not M13 R3; no FEM or marker use.**

| Pivot 8680 radial shift (mm) | native minSICN | native minSJ | D031 |
|---:|---:|---:|---|
| 0.0000 (original M13 R2) | .16294478890105799 | .28115937433961596 | HOLD |
| +.0075 | .18421698024660962 | .30871918057542824 | HOLD |
| +.0100 | .19120540512114387 | .3174590262749687 | HOLD |
| +.0125 | .1981413170001225 | .3259889096413908 | HOLD |

Other two off-pore vertex shifts: 8681=+.005 mm, 9115=+.005 mm for all trials. All three diagnostic meshes preserve the pore surface, connectivity and shared midside-node compatibility. The only element below minSICN .20 and minSJ .40 in every trial is Tet10 tag 9478. Native gamma min .24272495924632292 (>= .15), minDetJac min 1.6517904678607355e-13 (>0) are unchanged.

Observed progression is real but insufficient: at +.0125 mm minSICN misses the .20 threshold by .001858683; minSJ misses .40 by .07401109 (requires +22.70% relative). The source-side 729QP 10%-individual-volume guard excludes simple extension of the same pivot direction beyond +.0125 mm: at +.015 mm individual ratios reach .8969 to 1.1074. Therefore the **tested fixed-direction one-parameter extension** cannot meet both constraints within the imposed guard. This does **not** establish impossibility for a different combination of directions/displacements or a conforming CAD-preserving remesh.

## Suggested next scientific step P10NN

Investigate *directional* improvement of the fourth vertex and neighboring free vertex positions in the tangent-plane and normal-space basis of the local pore face, not just the same radial displacement scaling. Perform a bounded source-only 729QP screening of **all adjacent 67 Tet10**, including shared-edge midsides, fixed pore Tri6 and individual curved volume ratios .9..1.1; then send only non-dominated candidates to independent native Gmsh for canonical D031 checks. Explicitly monitor worsening among the neighbors to avoid shifting the bad element instead of fixing it. A failure of the bounded directional search motivates a **CAD-conforming local remeshing** strategy, with separate controlled mesh-generation authorization and marker.
