# P10Y: comparison of radial shell contributions on H4 and H4W2

**Status:** verified algebraic decomposition of discrete **mechanical** shape partials in the two FEM runs. **Not** a convergence proof.

## Model and calculation

- 3D spherical pore, radius `R=1 mm`, centre `(0,0,0.03)m`; nominal fixed B6 observation domain, EDV_VAR, mode `R`, `ANALYTIC_TET10`, six steps of 150 s (900 s total), cutoff 5 mm, 4 threads, deterministic (not GH3).
- H4: `nodes=221782`, `Tet10=164319`, pore `Tri6=1698`, pore median edge `0.133149 mm`; P10Y `wall_s=7215.48118650`, max shell partition residual `1.51359300895e-13`.
- H4W2: `nodes=261076`, `Tet10=190222`, pore `Tri6=6636`, pore median edge `0.0672052 mm`; P10Y `wall_s=11709.7812578`, max shell partition residual `2.80110132644e-13`.
- Number of QP radial bins: 10. Ranges in mm: `0–.02`, `.02–.05`, `.05–.1`, `.1–.25`, `.25–.5`, `.5–1`, `1–2`, `2–5`, `5–15`, `15+`. The last two contribute zero in these runs. Graphs show first eight.
- Thermal adjoint shape partial is **not** split into shells; global values are available in input P10W component CSV.

## Interpretation of columns

For each finite-width radial bin `k`, the `mechanical` quantity `C_{k,h}` is the **signed contribution to the mechanical shape derivative of the original functional on fixed B6**; its units are `per m`. It is not a derivative of a redefined truncated-volume functional, nor a local physical material sensitivity. `g_{k,h}=C_{k,h}/(r_upper-r_lower)` is a radial average **per mm** and therefore has units `per m / mm`. `G_h(r)` sums the contributions to the upper radial edge. `delta C = C_(H4W2) - C_(H4)`.

Radial grouping depends on the chosen volume extension of the boundary velocity and the QP/bin mapping. Meshes are not nested at quadrature level, and very thin shells on H4 may be poorly sampled. Thus `delta C` is a discrete shell-attribution difference; it is not a validated continuum error estimate or spatially unique derivative density. The exact element containing the maximum local error cannot be determined from these CSVs. Zero QP count is not distinguishable from a genuine zero contribution without further instrumentation.

### Overall result

| Functional | H4 full derivative, 1/m | H4W2 full derivative, 1/m | Relative change |
|---|---:|---:|---:|
| j6 | 0.026152112020047434 | 0.026160773271399956 | +0.033119% |
| jpeak | 2.3344633452520385 | 2.3628628788146244 | +1.216534% |
| jen | 0.016697075124663684 | 0.016699342206409604 | +0.013578% |

The change of the **mechanical part** of jpeak is +0.0285146422 (1/m). The sum of the absolute changes of its 10 radial-bin contributions is 1.1022790394 (1/m), i.e. the signed changes almost cancel (factor about 38.66). The largest absolute single-bin change, **+0.4378635765 1/m**, is in the `0–0.02 mm` radial shell. That is a property of the shell decomposition, **not** a proof that the maximum FEM error is localized there.

The same comparison for j6 gives a factor 20.07; jen 21.17. For jen the largest |delta C| is at `.02–.05 mm`.

### Contents

- `input/` original six CSV files, without modifications: shell, partition audit and global P10W components for H4 and H4W2.
- `data/P10Y_RADIAL_COMPARISON_ALL_MESHES.csv`: radial bins, mechanical component changes and derivatives, all three functionals.
- `data/P10Y_RADIAL_DIFFERENCE_SUMMARY.csv`: net and absolute shell differences, cancellation and max-change shell.
- `figures/`: 4 comparison figures as PNG and vector SVG.
- `tools/compare_shells.py`: reproducible figure/CSV generator. Takes further meshes through repeated `--shell NAME=PATH` arguments after checking comparable physics and bin boundaries.
- `VERIFICATION.txt`: numerical balance checks; `SHA256SUMS.txt`: file hashes.

## Rebuild

From this package directory with Python 3 and matplotlib installed:

```bash
python tools/compare_shells.py \
  --shell H4=input/P10Y_H4_SHELL_SUMMARY.csv \
  --shell H4W2=input/P10Y_H4W2_SHELL_SUMMARY.csv \
  --baseline H4 --compare H4W2 --output .
```

Do not replace an earlier published numerical study by later plots without tracking its source SHA and settings.
