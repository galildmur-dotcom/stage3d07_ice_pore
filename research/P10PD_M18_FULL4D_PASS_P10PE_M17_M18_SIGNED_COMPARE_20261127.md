# P10PD M18 real full-4D FEM PASS and P10PE independent M17-M18 4D comparison (2026-11-27)

## P10PD evidence
- User evidence ZIP P10PD_M18_FIRST_FULL4D_EVIDENCE.zip SHA256 6d75dc44ca1d3a3a86170b6a8577cb90d38e35e8349cc44b6d862832b432a5d5; CRC PASS; Library libfile_bcba700c28e481918c7ba731509c5f9f.
- Status P10PD_M18_REAL_FULL4D_PASS. Accepted M18 mesh SHA256 ddd9ee5eafdaa6e1b6959e5bd5d842cc37181dacdaef13d7ad21c45031da9ee1; 41463 nodes; 27849 Tet10; 3410 pore Tri6; Jacobian 27QP all positive.
- 36 steps x 25s, total simulated horizon 900s, R/EDV_VAR/xi=0/B6=5mm; 4 threads.
- Native EXE 0, wall 4093.622s, peak private memory 5,938,540,544 bytes, 273 independent heartbeats. Observed average logical CPUs busy 2.244 (host 28.05%).
- Native log: P10W_ANALYTIC_ADJOINT_OK, geometry_partial=ANALYTIC_TET10, central_fd_evaluations=0, 108 mechanical adjoint solves; max mechanical equilibrium relative 7.6441e-9, thermal 4.9858e-11, checkpoint roundtrip bitwise=1.
- Independent temporal signed 4D audit PASS, 43236 rows, 36 steps, 1200 volume bins/step; jpeak dR=2.367014709423416 per m.
- Independent explicit geometric-stress two-term audit PASS: 43200 rows, geometry 1.2456295042104435 per m, stress -10.509164163734368 per m, sum -9.263534659523877 per m. Per-bin closure PASS.
- P10PD physical attempt consumed ONCE; no repeats.

## Independent P10PE spatial-temporal comparison
- Reference M17 archive SHA256 5661ecc401019959c9cad9f0277f16f2c47d4c0bdb61450ab3465582ee3e078d; M17 accepted full4D physics PASS.
- Independent exact key match of 43200 VOLUME rows in M17/M18 CSV by (step, region, radial, mu, phi). 36 boundary TOP rows excluded from spatial error comparison.
- Global dR jpeak: M17=2.3650868492076955 per m, M18=2.367014709423416 per m; signed delta=+0.001927860215720667 per m; relative +0.0008151329480211268 = +0.0815132948%.
- 4D total L1 difference divided by M17 total L1 = 0.05748914275524516 = 5.7489%. This indicates substantial signed cancellations despite small global delta; it is NOT a discretization convergence proof.
- 4D total relative L1 difference by latitude: southern polar mu0=4.02274%, northern polar mu9=3.35490%, mid mu1..8=7.31653%. Polar contributions still can cancel: signed southern +0.00503534, northern -0.00932455, middle +0.00621707 per m.
- Strongest absolute changes of the per-step bins near last times: steps 35, 34, 33, 36, 32, 31. Radial bins 1..4 had 7.9-9.4% relative L1 changes; bins 8/9 zero in both.
- Mechanical component signed changes: explicit -0.017139, equilibrium -0.009389, history +0.027569 per m; thermal total +0.000887. Mechanical total +0.001041; total +0.001928. Local cancellation demands further spatial polar/temporal scrutiny.
- Machine-readable comparison report P10PE_M17_M18_SIGNED_4D_COMPARISON.json in Library libfile_3f7afb0387bc8191b137a0bfae710bff; generated with read-only comparator P10PE_M17_M18_SIGNED_4D_COMPARISON.py.

## Next scientific stage
Do not repeat P10PD. Analyze signed delta and positive/negative cancellation in (r,theta,phi,t), with special attention to time steps 31-36, polar caps, radial bins 1-4. Only then decide next adaptive M19 mesh indicators; always mandatory HighOrderElastic after any newly generated mesh and all independent QA before physics.