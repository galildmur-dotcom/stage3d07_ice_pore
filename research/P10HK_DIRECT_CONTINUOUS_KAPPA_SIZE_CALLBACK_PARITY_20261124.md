# P10HK R1 — direct continuous mechanical κ callback preflight

Date 2026-11-24. Goal: bypass the inaccurate interpolation of original smooth C2 κ through coarse real M1 Tet10 PostView, while respecting approved mechanically weighted signed M0/M1 4D physics and preserving original pinned M1/CAD.

Gmsh 4.15.2 officially offers `gmsh.model.mesh.setSizeCallback(callback)`, where the callback receives `(dim, tag, x, y, z, lc)` and returns the requested mesh size. This is a *documented API opportunity*, not yet proof that `lc` equals the intended pinned original Field[7] at the callback site. Reference: https://gmsh.info/doc/texinfo/#gmsh_002fmodel_002fmesh_002fsetSizeCallback .

This stage implements a precomputed scalar-coordinate callable with the **exact original four-dimensional compact Wendland C2 kernel**, same radial/angular scaling, same denominator, same [0,1] clamping, using frozen P10HA 1200 spatial bins and mechanical-only component. The direct proposed size mapping is `h = lc * (1 - 0.17 * κ(x,y,z))^(1/3)`; hence only a *nominal* local characteristic volume reduction of 0–17%, not actual curved Tet10 D-025 evidence. The approved 15–25% at κ=1 remains compatible with nominal 17%, but must be checked from actual new tetrahedra later.

## Independently run numerical result

20,000 deterministic random spatial test points sampled at the pore wall and 0.02/0.1/0.5/2/5/15/25 mm away, with all polar angles/azimuths. On the preparation runtime:

| Property | Observed |
|---|---:|
| Max |κ_direct - κ_frozen_P10HC| | 6.6613e−16 |
| Original NumPy batch, 20,000 samples | 0.56 s |
| Scalar direct κ, 20,000 samples | 0.61 s |
| Scalar callable latency | about 31 µs/query |
| Simulated size callback latency | about 31 µs/query |
| Nominal local characteristic volume ratio | 0.83–1.00 |
| Native 1D/2D/3D meshing / FEM attempts | **0** |

These times are **not** a forecast of actual Gmsh 3D run time. A runtime with millions of callback invocations may suffer a material per-call cost and require further acceleration; that is exactly why source-only timing comes first.

## Windows handoff

The immutable ZIP `research/proposals/P10HK_DIRECT_CALLBACK_SOURCE_ONLY_20261124/P10HK_R1_DIRECT_KAPPA_CALLBACK_BENCH_WINDOWS_20261124.zip` was built and then unpacked and executed independently; its SHA256 is `d7273ed214a6c96a6c9ee7ec15e726eeee29a6f27c7a71313c0d0a9168ac541e`. One-click `01_P10HK_BENCHMARK_NO_GMSH_NO_MESH.cmd` requires only existing Python+NumPy. Expected user i7-7700K duration 2–15 s. Return `P10HK_RESULT.json`, or `P10HK_ERROR.txt` if stopped.

## Strict next gate: P10HL native callback baseline and input domain

Before enabling mesh generation, verify *in actual Gmsh* whether passed `lc` is pinned original Field[7] (especially at north/south polar and nonpolar wall positions); validate original CAD, geometry tags and callbacks without FEM. Do not assume a callback alone makes a valid independent background size field. If native preflight requires 1D/2D, it must be proposed as separately guarded diagnostics; **no automatic 3D M2**. A future M2 requires independent 343/729 quadrature volume/quality D-025 checks and same-mesh forward/adjoint.
