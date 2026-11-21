// P10DN / M2: SOURCE-ONLY continuous field, NOT a Gmsh run authorization.
// M1 source CAD/Threshold is preserved exactly; only Background Field changes.
// Coefficient kappa(x,y,z)=F5 in [0,1]. Target V_M2/V_M1=1-0.2*kappa.
// Target h_M2/h_M1=(1-0.2*kappa)^(1/3) in [0.9283177667,1].
// Relative volume means local target, NOT guaranteed realized Tet10 pairing.
// Cartesian mu^2 guarantees no phi discontinuity at either spherical pole.
nearSize = 0.00042855883184652975;
farSize  = 0.0070524788853066865;
Include "sphere_pore_B6_refined.geo";

// F3: clamp((distance_from_pore_wall - 0.1mm)/0.4mm,0,1).
// Small +1e-24 keeps the expression finite even inside the excluded void.
Field[3] = MathEval;
Field[3].F = "min(1,max(0,(sqrt(x*x+y*y+(z-0.03)*(z-0.03)+1e-24)-0.0011)/0.0004))";

// F4: clamp((mu^2-0.6^2)/(0.8^2-0.6^2),0,1), mu=(z-0.03)/rho.
Field[4] = MathEval;
Field[4].F = "min(1,max(0,(((z-0.03)*(z-0.03)/(x*x+y*y+(z-0.03)*(z-0.03)+1e-24))-0.36)/0.28))";

// F5 = kappa: C1 smoothstep angular times 1-smoothstep radial.
Field[5] = MathEval;
Field[5].F = "(1-F3*F3*(3-2*F3))*F4*F4*(3-2*F4)";

// F6: scale the EXISTING M1 threshold size field F2, NEVER more than 20%
// smaller target element volume. DO NOT launch Gmsh from P10DN package.
Field[6] = MathEval;
Field[6].F = "F2*exp(log(1-0.2*F5)/3)";
Background Field=6;
