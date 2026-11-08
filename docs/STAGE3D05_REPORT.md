# Stage 3D-05: nonlinear EDV material-point update — scientific/technical verification

**Date:** 2026-10-09  
**Status:** G05 **PASS** for the pointwise constitutive integrator. Stage 3D-06 spatial E/ED/EDV FEM has **not** been performed.

## 1. Authority and scope

Canonical source: `reference/3D_BASELINE_SPEC_v4.md`, section 4; `reference/3D_CAMPAIGN_v4.csv` Stage 3D-05, and `reference/TEST_CATALOG_v4.csv` G05. The current stage adds an independent nonlinear material-point solver while preserving the previous, **elastic-only** Tet10 solver (`src/mechanical.cpp`) and Stage 3D-04 ED point solver. None of the numbers in this report are stresses near the spherical air pore. This stage does **not** involve the geometric shape derivative, spatial fields with EDV, GH3/GH5, the local stress functional `j6`, or a discretely coupled adjoint.

## 2. Physical law and units

Let `e = eps - alpha*(T-T0)*I`, `d = dev(eps)` (thermal strain is purely spherical, hence `dev(e)=d`), `s = dev(sigma)`, and `q = sqrt(3/2*s:s)`. The canonical model is

- `sigma = K_b tr(e) I + s`;
- `s = 2G(d - e_d - e_v)`;
- `de_d/dt = A_d(T) * (a*s - e_d)`, with `a=(3/2)K_d`;
- `de_v/dt = c(T) q^(m-1) s`, `c(T)=(3/2)K_N(T)`;
- `A_d(T)=1.5e-3 [1/s] * Arr(T)`;
- `K_d=1.2e-3 [MPa^-1] = 1.2e-9 [Pa^-1]`;
- `K_N(T)=2.56e-7 [MPa^-m/s] * Arr(T)` and `m=3.1`;
- `Arr(T)=exp[-(Q/R_g)*(1/T - 1/T_r)]`, `Q=66900 J/mol`, `T_r=263.15 K`;
- `E_const=9.5e9 Pa`, `E_var(T)=E_ref*(8.93-0.012*(T-273.15))/9.17`, `nu=0.35`.

Conversion of `K_N` to SI uses **`K_N,Pa = K_N,MPa / (10^6)^m`**, not `/(10^6)`; it is numerically crucial. All strains are *tensor strains*: the shear storage convention is `eps_xy`, not engineering `gamma_xy=2 eps_xy`. The history variables `e_d` and `e_v` are separate symmetric deviatoric tensors, dimensionless, initially zero. The specified fixed temperatures in tests are Kelvin; thermal expansion uses a reference `T0=253.15 K`.

## 3. Stable scalar nonlinear solve

For a backward Euler step of duration `dt`, with `b=dt*A_d(T)`, `beta=dt*(3/2)*K_N(T)` and `a=(3/2)*K_d`, elimination of both internal tensors gives

`dbar = dev(eps) - e_v_old - e_d_old/(1+b)`,  `A = 1/(2G) + b*a/(1+b)`.

The new deviatoric stress solves the algebraic tensor equation

`dbar = (A + beta*q^(m-1)) * s`, with `q = sqrt(3/2)*||s||`.

If `qtrial = sqrt(3/2)*||dbar||/A`, it reduces to the strictly monotone **scalar** equation

`q + (beta/A)*q^m = qtrial`, `q >= 0`.

The actual nonlinear root is computed in MPa using `x=q/(10^6 Pa)`, a bracketed Newton method and bisection fallback. The bracket `[0,qtrial]` ensures that no negative intensity is accepted. Once `s` is reconstructed, both `e_d` and `e_v` are updated. The new state is returned separately and previous state is never modified by `update`.

The consistent mechanical operator is the tensor inverse with deviatoric *tangential* coefficient `1/(A+beta*q^(m-1))` and *radial* coefficient `1/(A+m*beta*q^(m-1))`. The full `6×6` tangent includes bulk elasticity `K_b`; shear columns are defined for tensor shear strain, requiring the correct metric factors for major symmetry. The analytic partial derivative `d sigma/dT` holds the previous material history and total current strain fixed; it includes `dG/dT`, `dK_b/dT`, `dA_d/dT`, `dK_N/dT` and `eps_T(T)`. This is a **local** derivative, not yet the full-history total/adjoint derivative of the coupled FEM solution.

## 4. Thermodynamic control

At **constant T** a compatible algorithmic free energy is

`psi = 0.5*K_b*(tr(e))^2 + G*||d-e_d-e_v||^2 + ||e_d||^2/(2a)`.

The chosen formal dissipation is

`D = A_d*a*||s - e_d/a||^2 + (3/2)*K_N*q^(m-1)*(s:s) >= 0`.

The tests verify that the isothermal incremental inequality `psi_new-psi_old + dt*D_new <= sigma_new:(eps_new-eps_old)` holds for the prescribed strains, temperatures and steps checked. This is a mathematical consistency test for this phenomenological model, **not** a thermodynamic validation of the temperature-varying full model with entropy and heat generation; the thermal problem intentionally remains one-way coupled.

## 5. Numerical verification (executed)

All ten groups of new tests in `tests/edv_point.cpp` passed on GCC 14.2 and Clang 17; all **25/25 CTest** (7 Stage 3D-03, 8 Stage 3D-04, 10 Stage 3D-05) passed on GCC. Detailed logs: `results/EDV_material/CTEST_full.txt`, `CLANG_TEST.log`.

| Test | Independent verification / acceptance outcome |
|---|---|
| `G05_reference` | MPa-to-Pa exponent conversion, Arrhenius, equal reference moduli, hydrostatic/nonloaded/thermal limits and input validation — PASS |
| `G05_implicit` | tensor BE residuals, traceless internal variables, nonnegative q and scalar root including strong nonlinear cases — PASS; max relative scalar residual **1.14e-14** |
| `G05_tangent` | full 6×6 mechanical tangent compared with symmetric central FD over 24 conditions, energy-symmetric metric and positive diagonal terms — PASS; worst relative difference **1.23e-8** |
| `G05_temperature` | full local `d sigma/dT` vs central FD over 24 conditions (both E branches and both inelastic mechanisms) — PASS; worst relative difference **1.30e-9** |
| `G05_energy` | positive ED and EV dissipation plus discrete isothermal energy inequality — PASS |
| `G05_objectivity` | covariance of tensor values and energy under a fixed three-dimensional rotation — PASS (small-strain isotropy test, not finite-rotation objectivity) |
| `G05_stress_control` | separate exact constant-stress viscous rate, ED BE analytic limit and stress-to-strain inverse reference — PASS |
| `G05_limits` | EDV with viscosity disabled matches prior Stage 3D-04 ED stress, internal state, tangent and temperature derivative; both disabled recover E — PASS |
| `G05_restart` | serialize and restore the two history tensors, then produce identical next step — PASS |
| `G05_temporal` | refining BE from 8 to 512 steps at final time 600 s against 8192-step reference monotonically decreases stress error — PASS; reference is discrete, not analytical |

A separate **Python-stdlib** implementation of the scalar equation uses bisection (not the C++ safeguarded Newton method), reproducing:

- `G05_point_cooling.csv`: **482 records / 2 branches**, worst relative mismatch **8.46e-14**.
- `G05_E_ED_EDV_pairs.csv`: **1446 records / 6 model–E branches**, worst relative mismatch **8.46e-14**.

The comparison uses identical prescribed material-point inputs and sequentially propagates both history tensors. Independent script and machine-readable pass record: `scripts/check_stage05.py`, `results/EDV_material/G05_independent_readback.json`.

## 6. Illustrative point-only campaign (NOT a spatial pore prediction)

For **prescribed** `eps=[.0012,-.0007,.00032,.00068,-.00027,.00018]` and synthetic prescribed temperature history `T_C(t)=-20-3(1-exp(-t/300))` °C over 3600 s with `dt=15 s`, this point integrator gives the following **shear** stress `sigma_xy`:

| model | E_const at 3600 s (MPa) | E_var at 3600 s (MPa) |
|---|---:|---:|
| E | 4.785185 | 4.803971 |
| ED | 0.350137 | 0.350237 |
| EDV | 0.092247 | 0.092226 |

All cases start with `sigma_xy=4.785185 MPa` at the reference temperature and zero inelastic states. In the EDV branch at 3600 s, `e_v,xy` is about `4.99e-4`, whereas `e_d,xy` is about `1.68e-4`. The data demonstrate a separable local viscous response and correct state history, not measured ice properties or a predictive stress estimate near the spherical pore. Different prescribed strains/stress histories can change even the sign of the E_const/E_var difference. Numerical curves are supplied as raw CSV and three optional PNG figures.

## 7. Limitations and next stage

- Stage 3D-05 is a **material-point** integrator and standalone verification suite. There is **no FE equilibrium solve with internal EDV states**, no Candidate A stress fields for EDV, no solution or shape derivatives for `j6`, no GH3/GH5 EDV campaign. Earlier E-only FEM data are retained **unchanged**.
- The point tangent and local `d sigma/dT` are prerequisites, **not substitutes**, for differentiation of time-discrete state history and 3D global equilibrium.
- Sinha normalized `E_var` is the **instantaneous** modulus only. No additional time-dependent effective modulus was inserted.
- The time integrator is first-order backward Euler; acceptable `dt` for the subsequent local stress maxima and `j6` must be demonstrated separately.
- Full anisotropic natural ice, tensorial viscoplasticity, cavitation/fracture, material damage and thermodynamic feedback are outside the baseline.
- **Stage 3D-06** should attach a history pair `(e_d,e_v)` to **each volume quadrature point** of each Tet10, solve the nonlinear global quasistatic residual using the *same consistent local tangent*, enforce Candidate A with integral z-gauge, then compare E, ED, EDV × E_const, E_var for ξ=0 at matched thermal inputs before GH quadrature. The actual spatial j6 and local stress convergence are not yet established.

### How to reproduce

From project root:

```bash
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build -j2
ctest --test-dir build --output-on-failure
./build/stage3d05_edv_point --test all --out results/EDV_material
python scripts/check_stage05.py --results results/EDV_material
python scripts/plot_stage05.py --results results/EDV_material
```

Alternatively: `python scripts/reproduce_stage05.py --no-plot`. All C++ material-point tests depend on the **standard library only**; Gmsh and ParaView are not required to run them. Native Windows/MSVC runtime testing was not performed in this environment.
