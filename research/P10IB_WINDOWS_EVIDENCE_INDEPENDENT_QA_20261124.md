# P10IB — независимый аудит реального Windows 2D evidence, 24.11.2026

## Происхождение и целостность
Входной пользовательский архив `P10IB_2D_ONLY_EVIDENCE.zip` получен 24.11.2026. CRC ZIP 5/5 PASS. `P10IB_GUARD_RESULT.json`: status `WORKER_FINISHED`, code 0, wall 1.583s, peak private 542060544 bytes (≈517MiB), no 3D/FEM; one-shot consumed. `P10IB_WORKER_RESULT.json`: Gmsh Python 4.15.2, original CAD SHA `f1227074616375c28706e1e55cddde370b9a9fca069aab88513b4313c8239f51`, M1 SHA `47460969be26c2bd0a15e0b1425806fa350aa09aa2b4ac9f80605b433fc65ca7`, α=.40, 10/10 points embedded, pore 200 Tri6, 0 ghost callback, pore radius max abs error 1.735e-18m, no 3D/FEM. Independent SHA256 of Windows MSH **`4fea2c12cd515dd778795730e2848a712631b57dffe6e5ec23b77a80c318db02`** matches worker manifest.

## Независимый CAD wall vs pinned M1 анализ
Re-ran `p10ib_independent_surface_qa.py` against exact pinned M1 MSH, Windows MSH and original κ CSV, not worker metrics. 7968 identical physical sphere directions, 0 uncovered in both meshes.

| Metric | M1 | Windows P10IB |
|---|---:|---:|
| Pore Tri6 | 176 | 200 |
| Pore corner nodes | 90 | 102 |
| Median surface triangle h (mm) | 0.400327 | 0.376339 |
| Neighbor characteristic h ratio p95 | 1.238711 | **1.339916** |
| Neighbor characteristic h ratio max | 1.377828 | **1.634136** |
| Neighbor pairs ratio>1.25 | 4.545% | **11.333%** |

Paired physical h2/h1 highκ≥.8 (n365): median **.9203799452**, p05 **.720785**, p95 **.984566**, refined fraction **97.2603%**. North polar median .907966; south polar median .943873; lowκ<.2 median .960338.

This exact numerical match with Linux preliminary P10IB is independent confirmation of repeatability between platforms, even though Windows MSH byte SHA differs from Linux MSH. **α=.40 local 2D geometric adaptation PASS**, **discrete smoothness deterioration CONFIRMED**, and original D-029 target 25–50% actual highκ Tet10 characteristic volume reduction **UNVERIFIED** (surface h proxy is not volume).

## Science decision / P10IC
No M2 production or FEM GO. One-shot P10IB exhausted; do not re-run. Next P10IC should design a source-only smoother/size field or adjusted seed strategy and quantify paired highκ h and adjacent-size gradients before another bounded native 2D pilot, if needed. Smoothing is mandatory; uniformity is not. Avoid inventing an absolute threshold retroactively: compare smoothness to M1 and explicitly negotiate any new absolute gate.
