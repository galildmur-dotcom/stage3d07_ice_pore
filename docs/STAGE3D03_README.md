# Stage 3D-03 — 3D Thermoelasticity E (C++20, Tet10)

**Date:** 2026-10-09. **Authoritative model:** Stage 3D-00 v4 (see `reference/`).
**Scope:** 3D spherical air pore in fresh-water ice; one-way coupling from a transient thermal field to *quasi-static* linear thermoelasticity E. **No ED, EDV, inertia, adjoints, shape derivatives or j6 in this stage.** All units SI in the FEM solver.

## Contents
- `src/mechanical.cpp`: elasticity, E_CONST/E_VAR, 3x3-block CSR, block-Jacobi PCG, exact gauge, VTU output, G03 + MAT-T01…06 tests.
- `src/tet10_shared.hpp`, `src/geometry_stage3d01.cpp`: Gmsh 2.2 ASCII curved Tet10/Tri6 importer and shape functions, preserving Stage 3D-02 Tet10 vertex/midnode order.
- `src/thermal.cpp`: retained verified Stage 3D-02 thermal executable source for regenerating the input temperature fields.
- `meshes/`: H0/H1/H2 Gmsh curved Tet10 and no-pore 3D slab verification mesh.
- `results/*_dt300_xi0/`: **actual** thermal VTUs from Stage 3D-02 (input fields, ξ=0; t=900,1800,3600 s).
- `results/mechanics_H0/`, `...H1/`, `...H2/`: real E_CONST and E_VAR results at 3600 s.
- `results/mechanics_H0_t900`, `...H0_t1800`, `...H0_q4`: time and 64-point-vs-27-point pilot.
- `results/G03_UNIT/`: numerical verification evidence; `results/paired_fields_vtk_check.csv` independent VTK readback.
- `reference/`: original approved 3D-00 v4 technical decisions, material table and tests.

## Build in Qt Creator / command line
Open `CMakeLists.txt` in Qt Creator, choose a C++20 kit (MSVC or GCC/Clang), configure and build target `stage3d03_mechanical`. Windows Gmsh is **not required for running the already included meshes**. Gmsh is needed to regenerate or change geometry only.

Commands on Linux (also suitable for Windows with modified executable paths):

```bash
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build --config Release -j2
ctest --test-dir build --output-on-failure
./build/stage3d03_mechanical --mesh meshes/H2.msh \
  --temp results/H2_dt300_xi0/thermal_3600s.vtu \
  --out results/my_mechanics_H2 --model both --time 3600
```

Run full campaign automatically:

```bash
python scripts/reproduce_stage03.py
```

To **also recompute the thermal inputs from scratch** (retained Stage 3D-02 solver), run:

```bash
python scripts/reproduce_stage03.py --thermal
```

Quick smoke: `python scripts/reproduce_stage03.py --quick --skip-vtk`.
Python packages `vtk` and `numpy` are **optional** for `scripts/check_stage03.py`, not required for the C++ solver. The check against approved material table uses Python standard library. Matplotlib optional for regenerating plotting PNGs.

## Mechanics and gauge
Candidate A: `ux=0` on x=±0.03 m, `uy=0` on y=±0.03 m. On the top, bottom and pore faces: zero traction, including zero pore gas pressure. One free `z`-translation is eliminated numerically by temporarily fixing a single `uz` DOF, solving, and shifting **all** `uz` so `∫Ω uz dV=0` (consistent Tet10 quadrature). This does not impose a physical foundation; reaction in the temporary anchor is tested to be negligible.

Constitutive E-only stress: `σ=λ(T) tr(ε−αθI) I + 2μ(T)(ε−αθI)`, where `θ=T−T0` in kelvin. `ν=0.35`, `α=149×10^-6/3 K^-1`, `Eref=9.5 GPa`, `Tref=−20°C`. `E_CONST=Eref`; `E_VAR=Eref·[8.93−0.012 T°C]/9.17`, i.e. the agreed **relative** Sinha slope, NOT a unique experimentally calibrated modulus for arbitrary lake ice. All assembled moduli are local, evaluated at element quadrature points from the interpolated thermal field.

Three-dimensional curved Tet10 stiffness uses 27-point positive Duffy quadrature (`--quad 3`); `--quad 4` switches to 64-point for quadrature sensitivity. PCG uses a 3×3 nodal block-Jacobi preconditioner. C++ code checks `detJ>0`, FEM equilibrium, gauge and both models' fields.

## Visualize in ParaView
Open `results/mechanics_H2/E_VAR_t3600.vtu`; color by **Cell Data** `Principal_max_MPa` or `Von_Mises_MPa`. `Point Data` has `Displacement_m`, `Temperature_C`. Try `Warp By Vector` using `Displacement_m`, with an explicitly reported visualization scale factor (the actual max displacement is ≈4.24 micrometres). `results/E_CONST_H0_time_series.pvd` and `results/E_VAR_H0_time_series.pvd` open 900/1800/3600 s as animation.

VTU field stresses are sampled at each element's barycentric reference point, **not projected/recovered nodal maxima**. Physical maxima, `j6`, and their sensitivities require later stages and convergence analysis.

## Scientific limitation
Element-centroid maxima on H0/H1/H2 are **not monotonic**; the 0.21% difference between models on a fixed mesh is not proof of a physically resolved change in the true maximum. `t=3600` results here consume thermal input with `Δt=300 s`; mechanical convergence with respect to thermal `Δt` remains open. No new claims about ED/EDV or robust shape sensitivity are drawn from these results.
