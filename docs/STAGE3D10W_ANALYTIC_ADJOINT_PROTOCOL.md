# Stage3D10W — analytic fixed-state geometry partials in the transient adjoint

Status: **implementation pilot, not a validated scientific gradient**.
Base: `9c94f64b4b1b9f33ae9b57b5e03c06f69c705e4c` plus Stage3D10V patch.

## Discrete differentiation

For a fixed Tet10 connectivity let nodal coordinates be
`X(a) = X(0) + a V`, where `a` has units of metres. The vector `V` is
the exact derivative of the specified Stage3D08 deformation map at `a=0`.
The thermal and mechanical state is held fixed **only while computing an
explicit partial derivative**. The adjoint accounts for state changes.

At time step `n` the discrete equations have the schematic form

```
R_T,n(T_n, T_(n-1), X) = 0,
R_m,n(u_n, q_(n-1), T_n, X) = 0,
q_n = Phi_n(u_n, q_(n-1), T_n, X).
```

`stage3d10v_analytic_shape.hpp` computes partials
`(R_m,n)_X V`, `(Phi_n)_X V`, `(j_n)_X V` by differentiated curved-Tet10
Jacobians, volume weights, `B`-operators, production constitutive JVP, and
the derivative of B6 observation-volume normalization. `p10l::assemble`
computes `(R_T,n)_X V` by its analytical thermal shape operator. **No
perturbed mesh or finite-difference quotient enters the P10W gradient**.

After the existing backward mechanical/history and thermal adjoints are
solved, the gradient is assembled from explicit partials:

```
dj/da = sum_n [ w_n * (j_n)_X V
                + lambda_m,n . (R_m,n)_X V
                + zeta_n . (Phi_n)_X V
                + psi_T,n . (R_T,n)_X V ].
```

The signs and weights are those of the existing P10N discrete adjoint;
`zeta_n` denotes the future history multiplier. Verify the assembled
formula independently against FULL nonlinear forward differences, not
merely against fixed-state partial differences.

## Scope and limits

- Target: `stage3d10w_analytic_adjoint`; modes `R`, `tz`, `y20`.
- Current full trajectory: **EDV + local E(T) (VAR), deterministic ξ=0,
  900 seconds**, and the three existing P10N observables `j6`, `jpeak`,
  `jen`. `j_safety` is **not yet integrated** into the full adjoint.
- A fourth smooth-safety observable exists in the isolated P10V unit
  experiment only; it is **not** the approved physical `j_safety`.
- The `--selftest` flag checks inherited P10I adjoint dependencies only.
  The standalone `stage3d10v_analytic_shape_unit` checks local analytic
  derivatives against central differences.
- The run is not GH3, not an E/ED/EDV campaign, and not a proof of
  spatial or temporal convergence.
- The P10W run-manifest/registry integration has **not** been added yet.
  Until it is, treat full runs as engineering diagnostics, not as
  registrable production experiments.

## Required independent checks before scientific use

1. Run P10W `--preflight` on H0; verify mesh, fixed topology, gauge,
   positive Jacobians, analytical thermal-operator identities.
2. Run `stage3d10v_analytic_shape_unit` and P10W dependency selftest on
   Windows MinGW Release. Record both independent marker lines.
3. Compare P10W to a **separately executed P10N** gradient using the
   same forward state, mesh, time step, cutoff, normalization, and
   finite-difference amplitudes. Inspect each `j6`, `jpeak`, `jen` and
   each `R`, `tz`, `y20`, not only their aggregate maximum.
4. On the same mesh, vary the independent FD amplitude and check for a
   truncation/roundoff window. Retain residual and adjoint solver tolerances
   well below the observed gradient disagreement.
5. Perform spatial refinement H0/H2/H3/H4 and near-pore refinements.
   For each mode and observable report signed derivative `D_h`, pairwise
   differences, and normalized error with a common fixed reference.
   Separate variation in physical geometry from interpolation/remeshing
   errors; do not infer convergence from solver `_OK` messages.
6. Perform time-step refinement, then extend to E/ED/EDV, CONST/VAR and
   GH3, and implement the **actual approved** `j_safety` definition and
   derivative before reporting safety sensitivity in the paper.

## Safe preflight example (on the investigator's computer)

Qt Creator build target: `stage3d10w_analytic_adjoint` (MinGW Release).
Run arguments (use a **new** output directory each time):

```
--mesh G:\ildar\Stage3D07\meshes\H0.msh --out G:\ildar\Stage3D07\LOCAL_RUNS\P10W_H0_R_PREFLIGHT_20261110 --mode R --steps 6 --dt 150 --cutoff-mm 5 --threads 4 --preflight
```

Expected: `P10W_PREFLIGHT_OK` and `central_fd_evaluations=0`. This
creates the preflight directory, but **does not run** the nonlinear or
adjoint trajectory. Preserve the directory and console log for audit.
