# P10FL — REAL M2 physical R1 and signed 4D closure (2026-11-22)

**Status: physically EXECUTED, process exit 0; independent CSV closure PASS.**
This is not a planned or synthetic result. The computation ran on an isolated
Linux g++ 14.2 / OpenMP 4-thread build of the pinned P10DL production solver,
with an M2-only argument/one-shot guard. Original P10DL/M1 package was not modified.

## Input and regime

- Original real P10FB M2 mesh, named `P10EA_M2_CANDIDATE.msh` at execution;
  SHA-256 `ff6500e2da4f4697e1788669e2404d33cdeb9435c1230cf14f5cc7619f1f6a44`.
- 14,723 nodes; 10,094 Tet10; 194 pore Tri6; pore median edge
  0.38549994614451821 mm; computed B6 volume 9.0047854332406515e-7 m³.
- R / EDV_VAR / xi=0; B6 cutoff 5 mm; **six steps x 150 s** (900 s
  *physical* time); `jpeak` primary, with `j6` and `jen` also evaluated.
- ONE fresh nonlinear forward; the *same* mesh in the exact analytic Tet10
  transient discrete adjoint; 18 mechanical adjoint linear solves;
  **central finite-difference geometry evaluations = 0**.
- 8 GiB address-space and 1800 s wall-clock limits, one-shot marker created
  before execution. Observed solver wall time 192.598288805 s.

## Direct physical results, units per metre of radius change

| Functional | Objective | Mechanical gradient (m^-1) | Thermal gradient (m^-1) | Total (m^-1) |
|---|---:|---:|---:|---:|
| j6 | 0.00217773896217928 | +0.0238647172643422 | +0.00234502952272967 | +0.0262097467870719 |
| **jpeak** | **0.0481090612996078** | **+2.97832473731115** | **+0.0806805929898078** | **+3.05900533030096** |
| jen | 0.000872629531156371 | +0.0159667248225167 | +0.000601179389563675 | +0.0165679042120804 |

For jpeak the mechanical decomposition is signed:

| Component | Gradient (m^-1) |
|---|---:|
| Explicit objective geometry | -16.1195716023540 |
| Mechanical equilibrium residual | +15.0384697536634 |
| Internal history | +4.05942658600174 |
| **Mechanical sum** | **+2.97832473731115** |
| Thermal adjoint | +0.0806805929898078 |
| **Total** | **+3.05900533030096** |

Because opposite-sign terms cancel, the component cancellation ratio is
11.8245896765. Reporting the total alone loses important sensitivity information.

## Validation

- Six nonlinear steps converged. Last step Newton relative residual
  1.88352125703e-11; first step 2.79852748681e-13.
- 18 adjoint solves; all independently checked residuals around 1e-12 to 1e-11;
  no linear-solver retries.
- Maximum mechanical equilibrium relative audit 2.90267946230e-8;
  thermal equilibrium 4.34591771594e-11.
- Component partition max relative discrepancy 1.26099130858e-16;
  checkpoint round-trip bitwise PASS.
- Signed `(r, theta, phi, t)` export has 7206 rows: six time steps x 1200
  volume bins plus six top Robin boundary rows. The total signed 4D integral
  equals **+3.059005330300839 m^-1** (minor CSV summation rounding versus
  official +3.0590053303009612 m^-1). Independent Python CSV audit PASS.
- 4D integration mechanical +2.9783247373110244 and thermal
  +0.08068059298981466 m^-1. The source run prints
  `P10DD_FULL4D_CLOSURE_OK` and `P10W_ANALYTIC_ADJOINT_OK`.

## Scientific boundaries and next stage

This demonstrates M2 can carry the specified *diagnostic physical FEM and
adjoint* without numerical failure, and the 4D bookkeeping closes. It **does
not establish mesh convergence**, GH3 radius perturbation accuracy, or
insensitivity to the 95/419 near-polar q>1.25 neighbor jumps documented in
P10FK. A particularly important next experiment is a *like-for-like M1 vs M2*
fresh physical comparison for jpeak, its signed components, and local 4D
contributions; only then decide whether a new M3/polar repair is justified.

## Reproduction / provenance

- Binary compiled directly from the verified P10DL standalone source ZIP,
  with only M2 filename/output-prefix/marker guards changed; production
  `src/stage3d10w_analytic_adjoint.cpp` and its included solver dependencies
  remained unchanged. `--selftest` PASS before physical execution.
- Outputs: `P10W_ANALYTIC_ADJOINT.csv`, `P10W_COMPONENTS.csv`,
  `P10W_STEP_COMPONENTS.csv`, `P10DD_SIGNED_R_THETA_PHI_T.csv`,
  `P10DD_FULL4D_CLOSURE_AUDIT.csv`.
- Full raw mesh and 178 MiB forward history are not published in GitHub.
  A portable evidence archive can hold the five numerical CSVs, audit script,
  SHA-256 checksums, and run metadata without the large forward history.
