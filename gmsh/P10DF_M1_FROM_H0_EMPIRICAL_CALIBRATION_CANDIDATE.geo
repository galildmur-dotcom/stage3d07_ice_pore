// P10DF / D-018D: SOURCE-ONLY EMPIRICAL CALIBRATION CANDIDATE, NOT ACCEPTED M1.
// H0=M0 is the unchanged historical H0.msh SHA e28d6049... / 7388 Tet10.
// P10DC's near=.00019 and far=.0039 were H3-derived, NOT attested H0 settings.
// Anchors: H0/H3 measured pore-wall median edge, and H0/rejected-P10DE
// measured >18mm median of mu-bin corner-hmax medians.
// q=cbrt(0.8)=0.9283177667225558; NO physical error/goal indicators.
// near_m = .00019 * q * (.45237277518732666/.18618139238882903)
// far_m  = .0039 * q * (12.007900174938573/6.164339417865878)
// THESE ARE INVERSE PROXIES, NOT MEASURED HISTORICAL H0 GMSH PARAMETERS.
// A future separately authorized M1 mesh-only run must check global AND
// radial volume ratios against the real H0; do not launch FEM from this GEO.
nearSize = 0.00042855883184652975;
farSize  = 0.0070524788853066865;
Include "sphere_pore_B6_refined.geo";
