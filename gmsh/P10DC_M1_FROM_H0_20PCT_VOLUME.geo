// P10DC / D-018D: M1 is the H0 graded CAD size-field pattern, scaled globally.
// Target typical element volume ratio M1/M0 = 0.8, so h scale is cbrt(0.8).
// Do not use `sizefac`: the historical source declares it but does not apply it.
// SI metres. Exact old H0 mesh remains the M0 reference and is NOT remeshed.
// These sizes describe a NEW graded M1 candidate; no M1 mesh/physical solve yet.
nearSize = 0.00017638037567728565; // H0 0.000190 m * cbrt(0.8)
farSize  = 0.0036204392902179684;  // H0 0.003900 m * cbrt(0.8)
Include "sphere_pore_B6_refined.geo";
