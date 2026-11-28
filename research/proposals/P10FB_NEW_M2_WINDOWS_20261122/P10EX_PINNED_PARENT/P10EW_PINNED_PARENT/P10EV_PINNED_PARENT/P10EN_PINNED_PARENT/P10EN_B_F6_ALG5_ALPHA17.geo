// P10DV / M2: SOURCE-ONLY exact flattened field, NOT a Gmsh run authorization.
// M1 source CAD/Threshold is preserved exactly; only Background Field changes.
// Kappa inlined in Field6; [0,1]. Target V_M2/V_M1=1-0.17*kappa.
// Target h_M2/h_M1=(1-0.17*kappa)^(1/3) in [0.9397796375,1].
// Relative volume means local target, NOT guaranteed realized Tet10 pairing.
// Cartesian mu^2 guarantees no phi discontinuity at either spherical pole.
nearSize = 0.00042855883184652975;
farSize  = 0.0070524788853066865;
Include "sphere_pore_B6_refined.geo";

// Single non-reentrant-safe MathEval: only F2 is a Field reference.
// No Field3/Field4/Field5 MathEval definitions are needed.
Field[6] = MathEval;
Field[6].F = "F2*exp(log(1-0.17*((1-(min(1,max(0,(sqrt(x*x+y*y+(z-0.03)*(z-0.03)+1e-24)-0.0011)/0.0004)))*(min(1,max(0,(sqrt(x*x+y*y+(z-0.03)*(z-0.03)+1e-24)-0.0011)/0.0004)))*(3-2*(min(1,max(0,(sqrt(x*x+y*y+(z-0.03)*(z-0.03)+1e-24)-0.0011)/0.0004)))))*(min(1,max(0,(((z-0.03)*(z-0.03)/(x*x+y*y+(z-0.03)*(z-0.03)+1e-24))-0.36)/0.28)))*(min(1,max(0,(((z-0.03)*(z-0.03)/(x*x+y*y+(z-0.03)*(z-0.03)+1e-24))-0.36)/0.28)))*(3-2*(min(1,max(0,(((z-0.03)*(z-0.03)/(x*x+y*y+(z-0.03)*(z-0.03)+1e-24))-0.36)/0.28))))))/3)";
Mesh.Algorithm = 5;
Background Field=6;
