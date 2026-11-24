# P10IB — guarded original-CAD 2D wall embedding source and native Linux trial, 24.11.2026

## Evidence and exact preservation

P10IA source-only high-κ geometry led to **one prepared Windows one-click bounded 2D-only** Gmsh4.15.2 package:

- ZIP `research/proposals/P10IB_ORIGINAL_CAD_2D_20261124/P10IB_R1_ORIGINAL_CAD_2D_ONLY_WINDOWS_20261124.zip`;
- SHA256 **`a31b4d7da8b768a5af5ab2c50b5f93265c5cc1790045f276bd086967d4f6825f`**, bytes **855689**, CRC17/17 PASS; Git blob **`2b9ac29928be5d383a4a2c85bf546c067898f7a4`** remotely verified;
- Original `P10GT_HXT10.geo` SHA256 `f1227074616375c28706e1e55cddde370b9a9fca069aab88513b4313c8239f51` and pinned `P10GT_HXT10.msh` SHA256 `47460969be26c2bd0a15e0b1425806fa350aa09aa2b4ac9f80605b433fc65ca7`. Original `M0_ROTATED.geo`/sphere CAD byte-exact from P10HV source package, signed 4D C2 κ P10HA exact CSV SHA256 `98bc99af9783e14f7800f08ecd04fc6bee8093d0490b359e3a024f4c6c4566a3`, QA SHA256 `361d8812af277505abc59b480042d5b049fb23ae6d664ad781868b985eeafae3`;
- ZIP includes 17 fixed files and a single `01_P10IB_ONE_ORIGINAL_CAD_2D_NO_FEM.cmd`, Python source/wall/test dependencies; it **does not include** P10HV 3D worker or existing FEM executables.

## CAD discovery and independent native trial on Linux

Native locally installed Python gmsh **4.15.2** read the exact original GEO. Two volume entities were observed, pore wall physical 2D group8 comprises **one OCC Sphere entity tag8**, with two degenerate rotated CAD pole boundary curves tags 16 and18 at y≈±.001m, z≈.03m. This has been read from real CAD, not inferred from mesh triangles. Gmsh official `model.mesh.embed(0,tags,2,8)` is used only after checking all ten points project onto/on this actual original sphere and `isInside` is true; protective >.12mm distance to CAD pole curves, >.06mm to any original M1 Tri6 node, α=.40 and exact mechanical C2 κ.

**One local native 2D-only Gmsh attempt completed exit0** (not Windows evidence): `gmsh.model.mesh.generate(2)`, never `generate(3)`, no FEM. Native mesh second-order completed (CPU meshing wall about .28s for `generate(2)`), 3082 global 2D nodes, 1683 elements, `P10IB_2D_ONLY_UNVERIFIED.msh` SHA256 **`327cf41435cfaa0dd31c79c78ae8869dbf5c1bf1adee3ee1dd1be2a7838df744`**. Gmsh log reported surface worst gamma .354453, high-order optimization success. Worker: **10/10 embedded points are real mesh nodes**, 5992 callback calls, 0 internal ghost probes, **200 pore Tri6** versus 176 M1, 3D mesh elements0, max exact pore CAD radial deviation ~1.7e−18m. This confirms **one Linux original-CAD 2D technical feasibility**, not reproducible Windows completion or accepted M2.

## Independent physical-point wall sizing and surface smoothness QA

On the same pinned **7968** physical CAD directions as P10HZ, including **365 κ≥.8**, after the 2D-only candidate:

| metric | Original M1 wall | P10IB Linux 2D candidate α=.40 |
|---|---:|---:|
| Pore Tri6 | 176 | **200** |
| Corner wall nodes | 90 | **102** |
| Median characteristic Tri6 arc edge h, mm | .40033 | **.37634** |
| Neighbouring Tri6 h-ratio p95 | **1.23871** | **1.33992** |
| Neighbouring Tri6 h-ratio max | **1.37783** | **1.63414** |
| Fraction neighbouring Tri6 q_h>1.25 | **4.55%** | **11.33%** |

Paired h_proxy(M2)/h_proxy(M1) on *identical 7968 directions*:
- highκ≥.8, n365: **median .92038**, p05 .72079, p95 .98457, **97.26%** physical directions improved;
- north physical polar |μ|≥.8: median .90797 and 94.95% improved;
- south physical polar: median .94387 and 92.23% improved;
- lowκ<.2, n5571: median .96034, i.e. some incidental nonpriority refinement also occurs.

**Significant positive finding:** at matched highκ locations, the discrete surface sizing response is now in the correct direction, unlike P10HV α=.25 (`h_ratio≈1.03062`). **Significant negative finding:** the extra wall seeds raised p95 of neighbour-size ratios from 1.239 to 1.340, maximum from 1.378 to 1.634. This is a measurable loss of *discrete* smoothness; it does not establish a new hard gate or justify production GO. The numerical window above is a local Linux preflight only. `h_proxy³` cannot be substituted for actual curved Tet10 Veff and D-029 highκ **25–50% actual volume decrease remains unverified**.

## Windows release and safeguards

Windows package contains:
- exact checksum preflight for original CAD/M1/C2 CSV+QA and exact gmsh Python 4.15.2 version;
- one controlled α=.40 /10 point geometry case, no interactive typed consent;
- one permanent exclusive `P10IB_ONE_2D_ATTEMPT_CONSUMED.marker` created after preflight and before native 2D attempt; never rerun an already consumed attempt;
- external watcher **180s**, **2 GiB private memory** (Windows API), ≤500000 κ callback calls, ≤6 MiB log, ≤12 MiB MSH; 2D only, no Tet10/3D/FEM;
- compact output `P10IB_2D_ONLY_EVIDENCE.zip` with guard, worker report, log and raw surface MSH; if STOP send logs/error and do not rerun.

**Expected i7-7700K wall:** usually about 10–60s including Python/CAD startup, hard cap 180s; observed local Linux `generate(2)` .2766s not a guarantee for Windows.

## Verdict and next action

**P10IB source and isolated Linux 2D geometry PASS, independent highκ sizing improvement observed; Windows trial still PENDING, 3D/FEM=0.** One-click package released for user's single Windows run. Ask only for **`P10IB_2D_ONLY_EVIDENCE.zip`** (or guard/log/error on STOP), not M1 or P10HV archives again. After evidence, perform independent QA of curvature, surface quality/polar seam and actual h; likely need P10IC **smoothing correction** before any 3D, given measured p95/max deterioration. Do not automatically generate M2 3D/FEM or claim D-029 GO.
