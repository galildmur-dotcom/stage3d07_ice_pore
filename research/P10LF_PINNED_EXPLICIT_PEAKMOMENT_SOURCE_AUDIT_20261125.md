# P10LF — read-only audit of the pinned analytic Tet10 `j_peak` explicit derivative

**Status: source-contract and synthetic quotient-algebra PASS; physical cause of the M8→M9 wall-layer difference remains UNRESOLVED.** No FEM, Gmsh mesh, forward-state replay, marker or solver modification was performed.

## Why this audit matters

P10LE found M8→M9 signed `D_R j_peak` increment **+0.150290623141 m⁻¹** in the first 0–20 μm wall layer, driven descriptively by `mech_explicit` **+0.196024672713 m⁻¹**, cancelled by the rest of the domain **−0.138339384742 m⁻¹**. A finer mathematical decomposition is needed before attributing this to a surface Jacobian defect, normalization, EDV local stress sensitivity or physical singularity.

## Exact pinned source contracts

Source files checked in the P10LC exact 101-SHA solver tree:

- `stage3d10dd_4d_partition.hpp::mechanical_step` accumulates physical 27-QP curved Tet10 `dv`, `dgrad`, `deps`, material `law.jvp`, and a normalized explicit objective.
- `src/stage3d10v_analytic_shape.hpp::directional` uses the same analytic local geometric and constitutive `jvp` formula. The P10DD diagnostic checks its per-step explicit term against `weights[1]*analytic.objective[1]` and separately checks equilibrium/history against the analytic P10V operator.
- `src/stage3d10f_functional_adjoint.hpp::point_source(Kind::PeakMoment)` supplies the spectral stress gradient. Unlike `Kind::Energy`, it leaves `direct_strain` and `lambda_next` at zero. The separate adjoint history contribution is **not** zero.
- `src/stage3d10v_analytic_shape.hpp::velocity_at` uses radial outward normal `n*f` for `R`, with a compact smooth radial taper. On the cavity, positive radius perturbation expands the hole.

### Algebraic split actually warranted by the implementation

For one physical time step, let \(V=\sum_{q\in B6}v_q\), \(\bar f=\sum_qv_q f_q/V\), and \(w\) denote the existing time/peak chain weight. The explicit diagnostic is

\[
\frac{w}{V}\sum_{q\in B6}\left\{\underbrace{(D_Rv_q)(f_q-\bar f)}_{\text{geometric volume and normalization}}
 +\underbrace{v_q\,\langle\partial_\sigma f_q,D_R\sigma_q\rangle}_{\text{spectral-stress constitutive chain}}\right\}.
\]

In the actual source, \(D_R\sigma_q\) is obtained from \(D_R\varepsilon_q\), the curved Tet10 basis-gradient derivative `dgrad`, and the EDV material JVP at frozen local state. **There is no separate explicit boundary surface integral in this code path.** Nor can the current `mech_explicit_per_m` CSV separate those two summands. The apparent 0–20 μm localization can also include the global \(\bar f\) normalization effect, so it cannot be interpreted automatically as a purely local stress singularity.

Independent synthetic quotient identity using complex-step differentiation of 3- and 1200-cell normalized sums: maximum absolute error **1.38778e−17**, with no finite-difference perturbation of the physical FEM or solver. This confirms the split algebra, **not** the accuracy of the nonlinear EDV JVP on real states.

## Important geometric observation: mesh-dependent B6 element selection

`src/stage3d10k_h0_coupled_pilot.cpp::observation_elements` selects *whole elements* when the average of their four corner nodes satisfies `norm(center−pore_center)<0.006 m` (radius 6 mm). This is the production normalized B6 observation contract, evaluated separately for each mesh. It is not an exact cut-cell integration over the physical B6 boundary. Therefore a change of mesh can change the effective discrete observation domain and the normalization, even when physical B6 is nominally fixed.

| Measure | M7 | M8 | M9 |
|---|---:|---:|---:|
| B6 observed volume (m³) | 9.004699101693e−7 | 9.004774522420e−7 | 9.004689934885e−7 |
| Normalized `j_peak` objective | 0.0475212762121 | 0.0475050574880 | 0.0474903613993 |

Relative B6 volume changes: M7→M8 **+8.3757e−6**; M8→M9 **−9.3936e−6**. The underlying objective changes only −0.03413% and −0.03094% respectively while `D_R j_peak` differs by roughly 0.47–0.51% between adjacent meshes. The objective appears substantially more stable than its shape derivative over these three grids. **Small volume drift alone does not establish a bound on the geometry-derivative error**, especially for a highly weighted peak-moment functional.

## What has and has not been established

Established: P10DD/P10V source-contract parity, correct R sign convention, algebraic two-term explicit objective split, exact-source checks and synthetic quotient normalization. The observed first-wall-layer drift is real within the signed4D partition. Existing P10LC archive lacks frozen QP states, the `dv*src.value` subterm, and `lambda_sigma*law.d_sigma` subterm. A source-only audit **cannot** identify which of these is responsible for M8→M9.

Not established: a bug, a missing surface term, nonlinear constitutive JVP failure, mesh-dependent B6 cutoff effect large enough to explain Δ, a continuum singularity, or asymptotic spatial convergence. Do not infer a Richardson order from M6–M9. Do not rerun consumed M9 one-shot.

## Next P10LG: plan for an independently gated *diagnostic-only* instrumentation

Create an opt-in diagnostic source revision (with its own exact SHA pins) that records at every existing `(r,mu,phi,t)` bin **two explicit terms**: `(dvol)*(src.value−global_mean)` and `vol*(lambda_sigma·law.d_sigma)`, using the same QPs/states and no extra quadrature/forward/adjoint runs. Include a per-time-step and global exact closure back to the original explicit 4D CSV, and report B6 selected-element count/volume per mesh. If experimentally comparing cutoff effects, retain the physical B6 definition and use read-only geometry probes first.

**Do not run another expensive physical solve without a separately marked and resource-bounded user-approved experiment.** First review the instrumentation and its unit tests offline. A new M10 mesh is not justified solely by existing global cancellation.

Reproducer and QA: `research/tools/p10lf_pinned_explicit_shape_source_audit.py`, `research/evidence/P10LF_SOURCE_EXPLICIT_QUOTIENT_AUDIT.json`.
