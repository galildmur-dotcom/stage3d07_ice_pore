# P10PF: M17->M18 signed 4D cancellation and proposed M19 kappa (2026-11-27)

Status: SOURCE_ONLY_DIAGNOSTIC_PASS. No CAD, no Gmsh, no mesh generation, no FEM. P10PD one-shot not repeated.

## Exact evidence
- Accepted M17 physical archive SHA256 5661ecc401019959c9cad9f0277f16f2c47d4c0bdb61450ab3465582ee3e078d.
- Accepted M18 physical archive SHA256 6d75dc44ca1d3a3a86170b6a8577cb90d38e35e8349cc44b6d862832b432a5d5.
- Read-only comparison of 43,200 uniquely matched 4D volume bins (36 steps x 10 radial x 10 mu x 12 cyclic phi), all finite; both independent physical QA reports PASS.
- Global derivative M17 2.3650868492076955 per m, M18 2.367014709423416 per m; signed delta +0.001927860215720667 per m (+0.0815133%).
- Positive local delta sum +0.23949964060484027 per m; negative local delta sum -0.2375717803891148 per m. Sum of abs 0.477071420993955 per m, cancellation ratio 247.4616246045761.
- Of absolute signed differences: 55.9163% arise in time steps 31..36 (end of 900 s); 51.9756% from radial bins 0..3 (<250 um from wall); 26.9332% in polar caps mu 0 and 9.
- Relative L1 change of full total 4D field was 5.7489% M17-normalized from P10PE. 0.0815% global agreement alone does not establish pointwise/local convergence.
- Top radial contributions of abs(delta) approximately bins 0:10.7%, 1:13.5%, 2:13.7%, 3:14.1%, 4:13.0%, 5:10.0%, 6:9.5%, 7:15.6%, bins 8/9 zero.

## Proposed mesh-only next step M19
- Source-only smooth M19 priority kappa on 1200 (r,mu,phi) cells stored in P10PF_M19_PROPOSED_KAPPA_1200.csv. Input proxy sum_t(abs(delta_total)+0.25 abs(delta_mech_explicit)); smooth radial (0.25,0.5,0.25), mu/phi periodic (0.2,0.6,0.2); phi-averaged polar caps; near-pore radial attenuation and symmetric polar geometric-risk prior.
- Prior aligns with earlier observed polar sensitivity, not a certified local error estimate. Do not treat discrete cell kappa directly as Gmsh mesh size without smooth interpolation and geometry feasibility review.
- Proposed characteristic volume V_target/V_old=1-0.35 kappa: at kappa=1, -35% characteristic volume; at 0, unchanged. Isotropic local edge factor=(1-0.35 kappa)^(1/3). Historical user allowed 25-50% reductions in highest-priority regions.
- No new M19 mesh generated. Before physics: CAD/field review, actual M19 generation, mandatory Gmsh HighOrderElastic, native and independent topology/boundary/curved determinant/quality QA, one-shot marker.

## Deliverable
- P10PF_M17_M18_LOCAL_4D_DIAGNOSTIC_20261127.zip SHA256 4d646af3661643589531ef0036992c2b262e4df09807607cc583e628e15ff34d, Library libfile_d2d020246518819191c5ed7a45dffeae.
- Includes both immutable physical evidence archives, deterministic source-only Python comparator, optional one-click Windows CMD with no PowerShell/FEM, full diagnostic JSON, 1200-row kappa CSV and 100-row radial-latitude signed/positive/negative delta CSV.