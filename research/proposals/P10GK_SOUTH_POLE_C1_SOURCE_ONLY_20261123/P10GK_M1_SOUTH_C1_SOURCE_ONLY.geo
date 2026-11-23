// P10GK R1 SOURCE ONLY: proposed M1 C1 south-pole correction. NO native -3 permission.
// Include byte-pinned P10GH CAD-pole rotated geometry and original M0 radial F3.
// P10GJ global scale stays EXACTLY the same; frozen D-027 hard gates stay unchanged.
Include "M0_ROTATED.geo";

// Dimensionless clamp t_r for 0.5 mm plateau -> 1.0 mm exterior transition.
// d = sqrt(x^2+y^2+(z-.03)^2+1e-24) - 0.001 [m].
Field[4] = MathEval;
Field[4].F = "min(1,max(0,(sqrt(x*x+y*y+(z-0.03)*(z-0.03)+1e-24)-0.0015)/0.0005))";

// Dimensionless clamp t_s for physical SOUTH cone: mu<=-0.8 plateau,
// smoothly fading to zero extra refinement at mu>=-0.6.
Field[5] = MathEval;
Field[5].F = "min(1,max(0,(((z-0.03)/sqrt(x*x+y*y+(z-0.03)*(z-0.03)+1e-24))+0.8)/0.2))";

// W_r = 1-S(t_r), W_s = 1-S(t_s), S(t)=t^2*(3-2*t).
// Although the intermediate clamps are only C0, S' vanishes at both ends,
// hence the FINAL field is C1 across all cap/fade seams (away from pore centre).
Field[6] = MathEval;
Field[6].F = "F3*(1-0.06*(1-F4*F4*(3-2*F4))*(1-F5*F5*(3-2*F5)))";
Background Field = 6;

// Same global M0->M1 target, same HXT/Tet10; no automatic -3 from this GEO.
Mesh.MeshSizeFactor = 0.9378887276834518;
Mesh.Algorithm3D = 10;
Mesh.ElementOrder = 2;
Mesh.HighOrderOptimize = 1;
Mesh.MshFileVersion = 2.2;
Mesh.Binary = 0;
