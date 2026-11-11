// Stage 3D-10X: independent volumetric-refinement pilot (not FEM evidence).
// Put this file in Stage3D07/gmsh/ alongside P10O_H4_WALL_X2.geo.
// Gmsh 4.15.x; metres; MSH2.2 ASCII quadratic Tet10 + Tri6.
//
// Scientific control: retain the H4W2 pore-wall size field and refine the
// interior 0.25..2 mm neighbourhood independently. Do NOT interpret the
// prescribed size ratio as the measured Tet10 edge ratio: run P10O audit.
// This file creates a NEW mesh; it must never overwrite H4W2 or H4W4B2.

Include "P10O_H4_WALL_X2.geo";

// A moderate first pilot. The extra volume field is 20% smaller than the
// baseline H4 field over most of d=0.5..1.5 mm, tapers off around d=2 mm,
// and leaves the prescribed pore-wall step unchanged.
If(!Exists(bulkReduction))
  bulkReduction = 0.20;
EndIf
If(!Exists(bulkEnd))
  bulkEnd = 0.002000;
EndIf
If(!Exists(bulkTaper))
  bulkTaper = 0.000200;
EndIf

If(bulkReduction<=0 || bulkReduction>=1)
  Error("P10X: bulkReduction must be between 0 and 1");
EndIf
If(bulkEnd<=0 || bulkTaper<=0)
  Error("P10X: invalid bulkEnd/bulkTaper");
EndIf

// P10O include defines:
//   Field[1]: distance to pore surface [m]
//   Field[2]: original H4 size field
//   Field[3]: H4W2 near-wall size field
//   Field[4]: min(2,3) = H4W2 background field.
// The new smooth reduction is applied to Field[2] only. Thus
// min(2,3,5) <= min(2,3) pointwise in requested size-field values.
Field[5] = MathEval;
Field[5].F = Sprintf("F2*(1-%g/(1+exp((F1-%g)/%g)))",
                     bulkReduction, bulkEnd, bulkTaper);
Field[6] = Min;
Field[6].FieldsList = {2, 3, 5};
Background Field = 6;

// All OCC solids/surfaces, physical tags 1..9, Tet10 interpolation and
// high-order meshing options are inherited unchanged from P10O.
