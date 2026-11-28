# P10OA — independent audit of user P10NZ M12→M13 comparison evidence (2026-11-26)

## Evidence boundary

Received `P10NZ_M12_M13_COMPARISON_EVIDENCE.zip`, SHA256 `a5b6964b0e30f742e1605a8a3c79600edf3df68fff18dfc2a26cf12e0af8be3a`. ZIP CRC 2/2 PASS, contains summary and 43,200 signed4D difference rows. User has **not** supplied original `P10NY_M13_FIRST_FULL4D_EVIDENCE.zip` in this turn; consequently this is an audit of comparator output, not a direct native-M13 FEM log audit. M12 original physical baseline had already been verified separately.

Comparator reports physical status `PASS_PHYSICAL_COMPARE`, pinned M12 and optimized M13 SHA, identical source-manifest SHA `20e38ffc44f4499d5114f9d0e714246f93f28d5ca1d14adb1c94bb1552dc940f`, R/EDV_VAR/xi0/jpeak/B6 5mm/36×25s. It claims original M13 evidence SHA `092cef395a7629f4f37c322aa5c73e8017ced1b4494064fdb976d7c02f37961e`; this needs confirmation from the raw archive.

## Global signed shape derivative

| term, m^-1 | M12 | M13 | M13−M12 |
|---|---:|---:|---:|
| total | +2.370838129490 | +2.367223100058 | **−0.003615029432** (−0.152479%) |
| mechanical total | +2.305013337731 | +2.301048587373 | −0.003964750358 |
| thermal total | +0.065824791759 | +0.066174512685 | +0.000349720926 |
| explicit geometry/normalization | +1.270584395262 | +1.275600137102 | +0.005015741840 |
| explicit stress-chain | −10.671486637517 | −10.697019115841 | −0.025532478324 |
| mechanical explicit aggregate | −9.400902242255 | −9.421418978740 | −0.020516736485 |
| mechanical equilibrium | +8.612036576220 | +8.608360743006 | −0.003675833215 |
| mechanical history | +3.093879003766 | +3.114106823107 | +0.020227819341 |

The large cancelling mechanical explicit/history shifts prevent attributing the small global shift to convergence.

## Spatial-temporal localization

Independent reparse: 43,200 unique (step,radial,mu,phi) bins; sum of signed CSV differences matches JSON global to <1e-13 m^-1 for tested fields. L1 sum of absolute 43,200 bin differences `0.6376773168552733 m^-1`; Euclidean L2 of 43,200 differences `0.00895173730425422 m^-1`; absolute-to-signed cancellation factor 176.4. These are **raw grid-bin norms, not physically volume-weighted convergence estimates**.

- radial bin 0 (wall 0–20 um): **−0.031592446627 m^-1**.
- radial bin 1 (20–50 um): **+0.03020488 m^-1**.
- radial bin 2 (50–100 um): +0.00687013 m^-1; bin 3 −0.01343493; bin 4 −0.01236010.
- south polar mu0: −0.00058956 m^-1; north polar mu9: −0.00654049; middle mu1..8: +0.00351502. Sign cancellation also occurs across latitude.
- largest time-step sum magnitude at step 35 (t_end 875s): −0.00334251229; step 34 −0.00233656; step 36 −0.00215550.
- largest |single bin| at step 35, radial0, north mu9, phi4: −0.00103773519 m^-1; another at step35 radial1, south mu0, phi4: +0.00094851349 m^-1.

## Verdict and next gate

**P10OA_COMPARATOR_CSV_INDEPENDENT_REPARSE_PASS / M13_RAW_FEM_AUDIT_PENDING**. The global −0.1525% change is not sufficient to assert local spatial convergence, as there are significant opposite signed near-wall changes and latitudinal asymmetry. Do not initiate M14 adaptivity based only on this comparator. Obtain the exact original `P10NY_M13_FIRST_FULL4D_EVIDENCE.zip` (SHA given above) to audit native exit, one-shot marker, source and complete CSVs independently. Then decide M14 by targeted pole/wall error indicators, while preserving smooth mesh transitions and signed 4D attribution; do not do central FD geometry.
