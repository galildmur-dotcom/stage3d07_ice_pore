> **Актуальная точка входа в научный проект Stage3D07 для нового чата ChatGPT (18.11.2026): [START_NEW_CHAT.md](START_NEW_CHAT.md).** Рабочая исследовательская ветка и последние результаты P10BE перечислены там. Этот README ниже сохраняет историческое описание Stage3D06.

---

# Stage 3D-06-P — оптимизированная сборка

**Новая точка входа:** [README_QTCREATOR_RU.md](README_QTCREATOR_RU.md), результаты: [P06_VERIFICATION/RESULTS_SUMMARY_RU.md](P06_VERIFICATION/RESULTS_SUMMARY_RU.md). Исходные физические этапы сохранены ниже без изменения.

---

**Для текущего этапа проверки временной сходимости и QP-максимумов см. `START_HERE_STAGE06_CHECKS_RU.md`.**

# Stage 3D-06 — E/ED/EDV spatial solver with Tet10

**Research:** single 3D spherical air cavity in freshwater ice. Canonical `reference/3D_BASELINE_SPEC_v4.md`. No 2D comparison or unpublished article cited.

Added **`src/spatial_reology.cpp`**: fully 3D quasi-static thermal elasticity + ED + nonlinear EDV history at 27 quadrature points per Tet10, Newton/BCSR-PCG, E_CONST versus normalized Sinha relative E_VAR, Candidate A, gauge ∫uz=0, instantaneous Phi6/PhiOmega and time-integrated j6/jOmega.

**Status:** H0 72/72 steps, six branches at Δt=300 s, ξ=0 completed; H1 one EDV_VAR t=900 pilot; H2 attempt interrupted before convergence. See `docs/STAGE3D06_REPORT.md` for actual numbers and limitations. No shape derivatives/adjoints/GH or mechanical mesh convergence claimed.

## Qt Creator and Windows (historical PowerShell option; for current one-click instructions, see START_HERE_QT_CREATOR_RU.md)

Open root `CMakeLists.txt` with C++20 kit (MinGW-GCC, Clang or MSVC), configure Release, and build `stage3d06_spatial` and `stage3d02_thermal`.

Windows PowerShell from the project root:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/run_stage06_windows.ps1 -Mesh H2 -Law EDV
```

Default configuration uses **CPU serial** (no working OpenMP/GPU acceleration yet). The script first recomputes the ξ=0 heat field at 300s increments with `--every-step`, then launches mechanics and checkpoints each completed step. The second run with `-ReuseTemperature` reuses temperature files. Check whether the build is running in Release to avoid slow Debug FEM loops.

## Linux

```sh
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build --parallel 4
ctest --test-dir build --output-on-failure
./build/stage3d02_thermal --mesh meshes/H0.msh --out results/local_heat --dt 300 --tend 3600 --every-step
./build/stage3d06_spatial --mesh meshes/H0.msh --temp-dir results/local_heat --out results/local_mechanics --law EDV --modulus ALL --times 300,600,900,1200,1500,1800,2100,2400,2700,3000,3300,3600 --quad 3 --resume
python3 scripts/check_stage06.py --campaign results/G06_H0_dt300 --reference results
```

Common CLI: `--mesh`, `--temp-dir`, `--out`, `--law E|ED|EDV|ALL`, `--modulus CONST|VAR|ALL`, `--times t1,t2,...`, `--quad 3|4`, `--resume`, `--newton-tol`, `--cg-tol`.

View time-dependent fields in ParaView: `results/G06_H0_dt300/EDV_VAR/mechanics_time_series.pvd` and inspect `Principal_max_MPa` or `Displacement_m`. Element principal stresses are **volume averages of quadrature-point principal eigenvalues**, not the exact maxima: CSV `max_principal_MPa` is maximum across quadrature points.

All old G03/G04/G05 test programs, meshes, documentation and their reference source are retained for independent regression tests.

## Запуск полностью через Qt Creator — обновление 09.10.2026

**Для Windows в первую очередь читайте [`START_HERE_QT_CREATOR_RU.md`](START_HERE_QT_CREATOR_RU.md).**

Добавлены два самостоятельных CMake executable target:

- `stage3d06_qt_check` — H0/E_CONST, 300 с; короткая сквозная проверка теплового и механического решателей;
- `stage3d06_qt_run` — H2/EDV_VAR, 3600 с; запуск полного эксперимента одной зелёной кнопкой Run.

C++-запускатель использует нативный запуск дочерних процессов и абсолютные пути. Для него не требуются PowerShell, ручной вызов CMake, Python или установленный в PATH Gmsh. Стандартные результаты выводятся в `LOCAL_RUNS` внутри проекта, исходные `results/` из архива не изменяются. Подробности и ограничения — в руководстве.
