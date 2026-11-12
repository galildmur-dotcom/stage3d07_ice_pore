# Stage3D10Y — analytic radial attribution of the P10W shape derivative

Status: diagnostic implementation. **Spatial convergence is NOT established.**

## Mathematical meaning

For each time step and functional, P10W computes a shape derivative with
three mechanical terms: direct observable, mechanical equilibrium, and EDV
internal-history propagation. P10Y leaves those equations unchanged and
partitions their **analytic Tet10 Gauss-point terms** by the physical distance
`d = (|x-(0,0,0.03)| - 0.001) * 1000` (millimetres) on the nominal mesh.
Each Gauss point belongs to exactly one radial bin:

`[0,.02), [.02,.05), [.05,.1), [.1,.25), [.25,.5), [.5,1),
 [1,2), [2,5), [5,15), [15,+inf)` mm.

At each point, the analytic residual variation is contracted with the current
mechanical adjoint and assigned to its bin. The EDV state-derivative term is
contracted with the future-history adjoint at that point. For each observable,
the normalized explicit term in shell `s` is

`weight * (dNumerator_s - average * dVolume_s) / observationVolume`,

where `average = numerator / observationVolume` is GLOBAL over the fixed
physical B6 observation region and is evaluated at the nominal geometry.
The direct term is zero outside the B6 integration region. The other two
mechanical terms may be nonzero outside B6, because the governing equations
couple the observation domain to the remainder of the body.

The sum over all bins is verified independently for the three components
and their total, at every time step and over the entire history. This is an
identity audit of the numerical implementation, not a mesh-convergence test.

**Important:** the thermal-adjoint shape contribution remains GLOBAL and is
not included in `P10Y_SHELL_SUMMARY.csv`. Accordingly, no radial map of the
full coupled derivative is claimed. The full derivative is still available
in the inherited `P10N_DELTA_SCAN.csv`.

No finite-difference geometric partials or perturbed mechanical trajectories
are used by P10Y (`ANALYTIC_TET10`, `central_fd_evaluations=0`).

## Build and verification

Configure **MinGW Release** in Qt Creator and build the target
`stage3d10y_analytic_shell_audit`. Also build and run
`stage3d10y_analytic_shell_unit` once; it prints
`P10Y_ANALYTIC_SHELL_UNIT_OK`. The main program's `--selftest` verifies
dependencies and bin boundaries, not the full coupled radial decomposition.

Run in Git Bash from the repository root (adjust ONLY the executable path
if Qt Creator uses another build directory):

```
"G:/ildar/Stage3D07/build/Desktop_MinGW_Release/stage3d10y_analytic_shell_audit.exe" \
  --mesh "G:/ildar/Stage3D07/P10M_MESHES/H4W2.msh" \
  --out "G:/ildar/Stage3D07/P10Y_RUNS/H4W2_R_PREFLIGHT" \
  --steps 6 --dt 150 --mode R --cutoff-mm 5 --threads 4 --preflight
```

The preflight does not compute the expensive mechanical forward/adjoint.
For production remove `--preflight` and change the output directory to the
NEW `G:/ildar/Stage3D07/P10Y_RUNS/H4W2_R_6x150` (existing output folders
must never be reused).
If a compatible P10W forward cache exists, `--reuse-forward ABS_PATH`
can be supplied to the production run; this avoids a repeated nonlinear
forward solve. Never reuse a cache from another mesh or model.

## Outputs and analysis

- `P10Y_STEP_SHELL_COMPONENTS.csv` — one row per time step × functional × bin.
- `P10Y_SHELL_SUMMARY.csv` — history-summed components per functional × bin.
- `P10Y_PARTITION_AUDIT.csv` — per-functional global-vs-shell conservation.
- `P10N_DELTA_SCAN.csv` — inherited full geometric gradient, including the
  nonlocalised thermal term.
- `RUN_MANIFEST.json` — mesh hash, executable hash, arguments and outcome.

First compare H4 vs H4W2 for the **same mode, model, time interval,
observation domain and radius**. For each functional and shell `s`, compute

`Delta_s = mechanical_s(H4W2) - mechanical_s(H4)`.

Report the signed difference, absolute difference, and the absolute sum of
the three component differences. Identify the shell of maximum absolute
change and the component responsible. Then compare H4W2 vs H4W2B20 to
check whether farther bulk refinement materially changes those shells.
Because these are different meshes, `Delta_s` compares integrated values
within **the same geometric shell**, not matched individual element values.

Until shell comparisons are made, **do not claim** where the largest mesh
discrepancy occurs, whether the wall layer is adequate, or spatial
convergence. An element-by-element difference across nonmatching meshes
would additionally require a common physical projection/interpolation.

Time/memory: P10Y has the same one-forward/18-adjoint structure as P10W,
but spends additional time accumulating QP contractions and shell audits.
On the user's i7-7700K with 64 GiB RAM allow roughly 3–4 hours for H4W2
based on the previous P10W duration ~2.52 h. This is an indicative
estimate, not a measured P10Y benchmark. For H4W2B20 allow about 5–6 h
based on the prior P10W duration ~4.67 h. Do not launch several heavy
P10Y runs simultaneously on this workstation.
