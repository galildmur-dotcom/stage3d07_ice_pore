# P10DK R1 — исходники полного M1 forward + analytic adjoint + signed 4D: SOURCE-ONLY

**21.11.2026. Linux C++ link/synthetic + независимый Python 4D тест + ZIP source integrity PASS. Windows MinGW и настоящий M1 FEM НЕ запускались.** После D-019 научный порядок строго: историческая **M0=H0** с уже выполненным физическим P10DD signed4D → принятая геометрически **M1=P10DG** → новая прямая и сопряжённая на **одной M1**, полный локальный mechanical+thermal `(r,θ,φ,t)` → парное сравнение H0/M1 → только затем адаптивная M2. Запрет на индикаторы M1 не изменён.

## 1. Что выяснено в действующем production code

По прямому read-only исследованию `src/stage3d10p_partial_audit.cpp`, метод `p10n::run()` в точной P10W/P10DD analytical ветке поддерживает две разные траектории:

- `--reuse-forward BIN`: `load_forward()` проверяет layout/mesh signature/nodes/Tet10/QP/6×150с/cutoff с контрольной суммой и затем выполняет adjoints. **H0 cache нельзя использовать для M1**, даже если путь существует.
- **Без** `--reuse-forward`: `p10k::forward(base,c,true)` действительно создаёт **новую** полную прямую историю на переданной сетке и сохраняет `forward_history.bin` методом `save_forward()` с mesh signature, последовательно выполняет adjoint и контроль тождественности thermal fields. Условие `--preflight` в исходном solver **не является отсутствием физического вычисления**: ещё до его проверки вызывается `H::solve_forward`. Поэтому нельзя использовать этот solver-флаг для «бесплатного» source check.

Проверено, что существующее P10DD signed разложение не использует специальную формулу именно H0: оно обходит все элементы и мех27/теп64 Gauss QP данной mesh, интегрирует mechanical explicit/equilibrium/EDV history и thermal mass/diffusion/top-Robin, проверяет step/global closure. Мы **не переписывали физические формулы**, использовали тот же production src под отдельной макрокомандой, лишь специально обозначив M1/название HELP в двух guarded source branches.

**Объём первого этапа:** одна форма изменения R, EDV_VAR, ξ=0, jpeak, 6×150с=900с физического модельного времени, B6 cutoff5мм. Это точная физическая сопоставимость с ранее принятой P10DD H0. Отдельные `tz/y20` и остальные functional/law расширения не названы уже подготовленными в P10DK.

## 2. Новая изолированная сборка и блокировка расчёта

В отличие от H0 P10DD отдельный source-only target `stage3d10dk_m1_full4d` в `research/proposals/P10DK_M1_FULL4D_SOURCE_ONLY_20261121/` включает `STAGE3D10DD_FULL4D` и новый `STAGE3D10DK_M1_FULL4D`. **Любая обычная попытка выполнить физическую CLI-команду немедленно завершается `P10DK_SOURCE_ONLY_STOP_NO_FEM` с exit2 ДО чтения mesh/FEM**. `--help` и `--selftest` доступны. CMake `P10DK_ENABLE_PHYSICAL=ON` для этого R1 **явно блокируется** — требуется последующая отдельно разрешённая ревизия R2 с новым Windows resource gate; ни снятие предохранителя, ни физический запуск D-019 не разрешены.

Standalone Windows ZIP: `research/packages/P10DK_R1_M1_FULL4D_SOURCE_ONLY_WINDOWS_20261121.zip`, **364997 байт**, SHA256 **`162b14585e76fd8d9b856f0ba16cae0a937508f84332a05159cc46a1eb12f2f9`**, ZIP CRC **95/95**, список SHA **94/94**. Внутри: `src/`, `tests/`, локальные CMake/CPP, неизменные P10DD physical partition и synthetic unit, новый независимый Python auditor, отдельная кнопка `01_P10DK_CHECK_SOURCE_ONLY.cmd`, русский README и список SHA. Нет MSH/Gmsh, Windows EXE, кэшей, физических результатов, Git истории или marker. Исходный P10DG M1.msh у исследователя (Windows SHA по manifest `ca6b6b6588dc72c5dd3ed2e92e24794560ee2407e350c8a44858e9c3c7d0360f`), H0 original SHA e28d6049... неизменны.

## 3. Новый M1 независимый проверяющий код

`P10DK_audit_evidence.py` на основе уже проверенной P10DD методики переходит на **точную принятую M1: 9736 Tet10**, mesh stem `P10DG_M1_CANDIDATE`; в каждой из шести временных ступеней ожидает **262872 mechanical QP** и **623104 thermal QP** плюс отдельную Robin верхнюю границу. CSV `P10DD_SIGNED_R_THETA_PHI_T.csv` (историческое имя production exporter сохранено) содержит 6×(1200 volume+1 Robin)=**7206** строк; independent script заново суммирует *знаковые* 6 компонент и сверяет все 6 шагов/мех глобальный/тепл глобальный/итоговый P10W gradient. Никаких весов по модулю, замены unknown polar bins и приписывания Robin объёму.

Python synthetic 7206 rows+step/global closure PASS, в негативных тестах обнаружены: порча общей суммы, порча индивидуальной 4D строки, подстановка **7388×27 H0 QP**, неправильная метка **H0**. Тест не является верификацией реальной 4D производной M1, для которой пока нет физических CSV.

## 4. Реально выполненные здесь тесты (ФEM=0)

1. Linux GCC14 C++20/OpenMP **syntax-only** нового M1 translation unit — PASS; full native **link** `stage3d10dk_m1_full4d` — PASS.
2. Native `--selftest` — PASS: `P10I_PRODUCTION_ADJOINT_OK` (18 синтетических cases), `P10W_DEPENDENCY_SELFTEST_OK`, `P10DD_FULL4D_BINS_SELFTEST_OK bins=1200`, `P10DK_M1_SOURCE_SELFTEST_OK physical_FEM=0`. Эти тесты **не** доказывают physical M1 integration.
3. Native synthetic unit (унаследованный P10DD) — PASS: 7206 synthetic rows, 1200 bins/step, signed/global closure, folded negative.
4. Native `--help` — exit0 с явной меткой M1; обычная фальшивая команда `--mesh NEVER_RUN.msh --out NEVER_OUTPUT` — **exit2 P10DK_SOURCE_ONLY_STOP_NO_FEM**, никакой прямой задачи.
5. Linux старой исходной P10DD target с новым guarded source кодом `-fsyntax-only` — PASS, обычные P10DD/H0 пути не изменены.
6. Отдельно распакованный bundle source checker — PASS `P10DK_SOURCE_ONLY_OK`, ZIP CRC95/95; при замене единственного исходного CPP внутри тестовой распаковки — ожидаемый SHA STOP. Изолированный standalone ZIP C++20 `-fsyntax-only` — PASS.

**Не проверены:** настоящий M1 mesh/FEM на нашем Linux (файла M1.msh здесь нет), реальный C++/thermal/adjoint run на Windows, MinGW/Qt Creator компиляция, 27/64QP closure на M1, native Windows EXE/forward SHA, память и wall M1. Здесь `cmake` как отдельная программа отсутствует, поэтому тест CMake/Qt Creator проводится только у исследователя.

## 5. Ресурсная оценка и следующий этап

На том же Windows i7-7700K/64ГиБ P10DD H0 adjoint-only с архивной H0 history занял реально **74.08с и 0.894GiB private**; M1 имеет на31.78% больше Tet10, но **добавляет новую прямую нелинейную историю**, поэтому простая пропорция **не является верхней границей**. Рабочий **прогноз, не измерение**: около **3–15 минут** на full fresh-forward+adjoint, RAM **1–4GiB**; при будущем отдельном разрешении предлагаемый STOP **1800с/8GiB private/1GiB новых файлов**, ≥4GiB свободного диска; лимиты окончательно уточнить после Windows source tests.

Исследователю сейчас безопасно: загрузить ZIP, отдельно распаковать; двойной щелчок `01_P10DK_CHECK_SOURCE_ONLY.cmd`, затем в Qt Creator собрать `stage3d10dk_m1_full4d` и `p10dk_4d_synthetic_unit`, выполнить **только** безопасные unit/`--selftest`; сообщить лог, без физического M1 запуска. Подробно в `README_RU.md`. Для будущего **ОДНОГО** физического запуска нужен новый R2 bounded one-click (exact M1 SHA, same M1 forward/adjoint, fresh cache only, MinGW DLL PATH, signed4D audit, marker до native Popen, collection of small evidence ZIP), отдельно одобренный исследователем. M2 adaptive не разрешена до реальных M0/M1.
