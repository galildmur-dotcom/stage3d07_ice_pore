# P10OB — raw M13 full4D FEM accepted; independent M12→M13 replay PASS (2026-11-26)

## Raw physical package

Received exact `P10NY_M13_FIRST_FULL4D_EVIDENCE.zip`, SHA256 **`092cef395a7629f4f37c322aa5c73e8017ced1b4494064fdb976d7c02f37961e`**, identical to the digest claimed by P10NZ comparator. ZIP CRC 10/10 PASS. Native manifest status `P10NY_M13_REAL_FULL4D_PASS`, native exit 0, no stop reason, one physical attempt, fresh forward, analytic same-mesh adjoint, R/EDV_VAR/xi0/jpeak/B6=5mm/36×25s/4 threads.

M13 optimized mesh SHA **`cf4ff4872b82fe3fd854d0ddcb31144eb69f42e8ddce8b1954f064243cf9f4ca`**, 26099 nodes, 18004 Tet10, 1168 pore Tri6, physical groups2..9, 486108 curved 27QP, no nonpositive detJ samples, min sampled detJ1.7454418527270142e-13. Independent geometry acceptance P10NX had stronger 729-point diagnostics; no remeshing was performed.

Source revision `P10LM_M9_TWO_TERM_EXPLICIT_INSTRUMENTED_P10LG_V1` is only an inherited *source revision identifier*, **not the current mesh or comparator**. P10NY manifest source pin `20e38ffc44f4499d5114f9d0e714246f93f28d5ca1d14adb1c94bb1552dc940f` equals M12 source pin.

Windows runtime: **2124.314 s (35.405 min)**, peak polled private memory **3,839,729,664 bytes (3.576 GiB)**, Windows Job cap 12 GiB, wall cap 5400 s, independent heartbeat 142×15s, CPU telemetry 4531.19 CPU-s / 2.133 average logical CPUs / 26.66% host CPU of 8 logical CPUs. The observed 26.66% is actual average and cannot be inferred as 4 fully busy threads. Native log explicitly reports forward solves=1; 36 adjoint times × 3 functional solves=108 mechanical adjoint solves; max mechanical equilibrium relative residual9.26624e-9, thermal4.90456e-11, partition error2.1003e-16, checkpoint bitwise=1, central FD geometry evaluations=0. 4D CSV closure PASS, 43236 P10DD rows; P10LG physical signed split 43200 rows and per-bin closure PASS.

## Independent cross-archive audit

Re-ran **P10NZ** read-only comparison directly on *raw* physical M12 `P10MO_M12_FIRST_FULL4D_EVIDENCE.zip` and raw M13 P10NY ZIP; recalculated all **43,200** signed 4D bin differences. Comparison to *user-submitted* `P10NZ_M12_M13_COMPARISON_EVIDENCE.zip`: **exact equality of every 11 numeric field in all 43,200 bins**, max absolute CSV difference **0.0**, global summary difference **0.0**. Thus prior P10OA comparison is now supported by independent raw-source audit, not merely a comparator-derived assertion.

| quantity, m^-1 | M12 | M13 | M13−M12 |
|---|---:|---:|---:|
| Full `D_R jpeak` | +2.370838129490 | +2.367223100058 | **−0.003615029432** (−0.152479%) |
| mech total | +2.305013337731 | +2.301048587373 | −0.003964750358 |
| thermal total | +0.065824791759 | +0.066174512685 | +0.000349720926 |
| mech explicit | −9.400902242255 | −9.421418978740 | −0.020516736485 |
| geometry normalization | +1.270584395262 | +1.275600137102 | +0.005015741840 |
| stress-chain | −10.671486637517 | −10.697019115841 | −0.025532478324 |
| mech history | +3.093879003766 | +3.114106823107 | +0.020227819341 |

Local 0–20um radial difference −0.031592446627 m^-1, 20–50um +0.03020488; north polar μ9 −0.00654049, south polar μ0 −0.00058956; peak per-time signed delta step35 t875s −0.003342512293. Raw per-bin L1=0.6376773168552733 m^-1; 176.4× larger than |global signed delta|, indicating substantial compensation. Raw per-bin norms are not a volume-weighted physical error estimate.

## Scientific verdict

**P10OB_M13_PHYSICAL_ACCEPTED_M12_TO_M13_RAW_REPLAY_PASS** for this specific R/EDV_VAR/xi0/jpeak/36×25s regime. M13 not automatically converged: globally small signed difference masks first-shell and polar contributions. Prior M12 physical one-shot and current M13 physical one-shot both consumed; never rerun either. Next *source-only* scientific phase P10OC: quantify local signed vs absolute differences, time/latitude/radial hotspot patterns and mesh quality/size changes, then design a smooth κ(x) for the M14 *candidate*, not another physical FEM before explicit geometric acceptance. Avoid central FD geometry and avoid saying spatial convergence is proven.
