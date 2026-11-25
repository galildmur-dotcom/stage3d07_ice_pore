# P10KP — M8 R2 polar plateau, mathematical SOURCE-ONLY unit (2026-11-25)

**PASS_MATHEMATICAL_UNIT_ONLY; REAL P10KM FIELD NOT INTEGRATED; NO GMSH, MESH OR FEM.**

After P10KO showed actual M8 R1/M7 near-polar Veff ratios N=0.9697823473 and S=0.9690504238 (STOP, required [0.75,0.85]), a distinct prospective M8 R2 geometric size-field correction is defined. The entire accepted M7 R2 CAD, ten embedded seeds, physical groups and cumulative size callback must remain unchanged.

Define d=1000*(|x-C|-R) mm and mu=(x_z-C_z)/|x-C| on the ice side. Let S5(t)=0 for t<=0, =6t^5-15t^4+10t^3 for 0<t<1, =1 for t>=1. Define radial a=1-S5((d-0.5)/0.5) and polar b=S5((|mu|-0.6)/0.2). For the original 4D-informed P10KM interpolated kappa0(x) in [0,1], define kappaR2=kappa0+(1-kappa0)*a*b and h8/h7=(1-0.20*kappaR2)^(1/3). Thus kappaR2=1 throughout d<=0.5mm, |mu|>=0.8, with C2 transition to original kappa0 for d>=1mm or |mu|<=0.6. The nominal element volume target in the plateau is 0.80, **not** a guarantee on the realized finite-element Veff.

A standalone no-I/O mathematical selftest in [p10kp_m8_r2_polar_plateau.py](tools/p10kp_m8_r2_polar_plateau.py) checked 858 combinations over six baseline kappa values, eleven radial distances and thirteen mu values. Range error=0, plateau error=0, N/S symmetry error=0; quintic endpoint second-derivative finite-step proxy <0.002. No consumed marker touched.

**Pending source-only gate:** integrate with the actual pinned P10KM Field and source bins, compute quadrature-weighted regional distributions of kappaR2 and h^3 in the predeclared N/S p0 regions, including boundary and azimuth audits. Do not label this P10KP design as full source-only PASS before that check. A subsequent entirely distinct M8 R2 Windows mesh-only package must have fresh markers, independent watchdog and 65s silent-child preflight; only then native Gmsh 4.15.2 and independent D031 all curved Tet10/quality/CAD/tags plus D029 near-p0 N/S Veff in [0.75,0.85]. Do not rerun consumed M8 R1 or launch M8 FEM without separate geometry/adaptation GO. All future physical comparisons remain R/EDV_VAR/xi0/B6 5mm, 36x25s, same-mesh analytic adjoint and signed4D.
