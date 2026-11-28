# P10DA — грубая равномерная U0: первая физическая попытка после D-018B

> **Исправление после запуска M0 пользователем (D-018C / P10DB):** уже работающий P10DA EXE **не выдаёт** требуемого D-017 полного signed `(r,θ,φ,t)` механического и теплового QP-экспорта. Это ошибка при выборе ассистентом EXE; ниже P10DA исходный протокол сохранён исторически. **Не прерывать текущий M0, не удалять `forward_history.bin`.** Вторая сетка M1 должна быть **тоже равномерной**, с примерным сокращением объёма каждого типичного элемента на 20%, h1≈1.856635533445мм; адаптивность только M2 и далее, **не** автоматическая M1. До нового M1 FEM требуется реально внедрённый и аттестованный 4D exporter. Подробно `research/P10DB_M0_M1_UNIFORM_20PCT_AND_4D_EXPORT_CORRECTION_20261121.md`.

**21.11.2026. Статус: WIN_PHYSICAL_PENDING; Linux source/static/CSV regression PASS; физический FEM U0 = 0.**

## 1. Коррекция методики и новизна

**Прямое новое решение исследователя D-018B** отменяет операционную последовательность D-018A: до локального сгущения **обязательно выполнить физический расчёт на уже построенной грубой квазиравномерной U0**. Сетка U0 **не заменяется U1_geo**. Априорные h=20мкм, полюсное сгущение, число элементов M1 или будущие ресурсные ограничения не определяют первый шаг.

**Уже есть:** геометрический P10CT R2 на настоящей U0; 131380 nodes/90725 Tet10/11636 physical Tri6/20 pore-wall Tri6, 2449575 curved sample-QP с положительным detJ, R2 SHA `92c7a902...`, реальная `.msh` SHA `1a4690d1c57c8b520d596f9a864f754a8d84151bfd1fdd36f56631488779c6a3`. Есть физические H0 P10CA и H1 P10CD, но **нет физического U0**. Переоценка кандидата U1_geo в P10CZ — отдельная, пока отложенная аналитика.

**Новое:** сравнить первый фактический R/EDV_VAR ξ=0 signed физический глобальный `D_R jpeak` и временно-радиально-полярную тепловую компенсацию на именно **независимой грубой U0**, включая точный QP/CSR closure. H0 и H1 имеют другую геометрию/разрешение; разности не равны истинной ошибке. Дополнительно проверить достаточность данных для выбора адаптивного индикатора. Это новый независимый физический эксперимент, не переобработка P10CJ–P10CR.

**Критерий GO:** закреплённый MSH SHA + EXE SHA, read-only original Git, Windows native EXE exit0, geometry method ANALYTIC_TET10, 6 шагов R/EDV_VAR, `P10BX_THERMAL_QP_INTEGRATED_OK`, 606/6 CSV, 5806400 thermal volume QP/step, per-step QP/CSR/partition balance и global mechanical+thermal closure, no rerun. **STOP:** SHA/ресурсы/Windows path mismatch, nonzero native exit, no CSV/closure, memory/time/file limits, inability to monitor memory, changed Git/input. STOP сохраняет evidence, запрещает повтор без пересмотра протокола.

## 2. Материалы и точный запуск

- Existing mesh: `G:\Downloads\P10CT_R1_U0_MESH_ONLY_WINDOWS_20261121\P10CT_RUNS\P10CT_20261121_051002_957\P10CT_U0_h2mm.msh`; 16218389 B, SHA-256 выше. **Никаких** новых Gmsh-вызовов.
- Existing executable: `G:\Downloads\P10CA_H0_ONE_RUN_R1_20261120\P10CA_RESULTS_20261120_151200_8420\build\p10ca_h0_analytic_qp.exe`, SHA-256 `17c31f426245317271245e340d68fa5de1e4eb144b7be986167505e14cbed924`; pinned P10W/P10BX source, native Windows H0/H1 history, но **не проверен на U0**.
- Qt/CMake target, если нужно идентифицировать происхождение EXE: `p10ca_h0_analytic_qp`, **сборка не выполняется**; basename H0 исторический, реальный C++ CLI не ограничивает mesh.
- Runtime args: `--mesh <exact U0> --out <new isolated U0_PHYSICAL_RUN> --steps 6 --dt 150 --mode R --cutoff-mm 5 --threads 4`. Mode R shape derivative, EDV_VAR ξ0, `jpeak`; same U0 forward and adjoint; 1 nonlinear forward, 18 adjoint combinations согласно P10W. Horizon900 s, thermal 64-volume-QP/Tet10 per step (в отличие от R2 mesh-only 27-QP).
- One-click: `research/packages/P10DA_R1_ONE_UNIFORM_U0_PHYSICAL_WINDOWS_20261121.zip`, **11 105 байт, SHA-256 `71c27164a528f93e8617e523c13106117f0bfcb5f40ff26e6368fd36c1378d29`, ZIP CRC3/3 PASS**; `01_RUN_P10DA_ONE_U0.cmd` → `P10DA_run_one_u0.py`. Только вне dirty original/source mesh. Пакет состоит из Python stdlib watchdog, Windows CMD с CRLF и README. Положительный prompt **`RUN ONE U0 P10DA`**, Enter отменяет; необратимый marker до CreateProcess; без авто-повтора. Один `P10DA_EVIDENCE.zip` с маленькими CSV и stdout/stderr.

## 3. Расчёт ресурса и лимиты

P10CD R2 real H1: `19412 Tet10`, `407.813 s`, polled-private `2,560,204,800 B`, output `409,189,248 B`. U0=90725 Tet10, отношение **4.67366**. Линейное перенесение **только условный ориентир**: `1905.98s≈31.8min`, `≈11.97e9B=11.14GiB` поллинг memory, `≈1.912e9B=1.781GiB` output. Nonlinear scaling, solver factorization/coupling and filesystem may grow faster; no validated U0 upper bound.

Одна потенциальная физическая попытка: начальные free RAM≥20GiB, free disk≥8GiB; watchdog wall≤3600s, process `PrivateUsage`<32GiB, observed output<4GiB; OpenMP4. Windows 64-bit Python3 `ctypes` uses `GlobalMemoryStatusEx`/`GetProcessMemoryInfo`, failure of memory guard causes STOP. One-second polling is not instantaneous hard cap; if OS pages or source files are changed meanwhile, report STOP. Большая история остаётся локально.

## 4. Верификация без FEM

В Linux (без `.msh`, Windows EXE и FEM) проверены:

1. `python -m py_compile` для runner и test: PASS.
2. `P10DA_SYNTHETIC_SELFTEST_OK FEM=0 GMSH=0`: PASS, thermal QP count=5,806,400/step.
3. Offline regression по пяти **реальным архивным H0 CSV** P10CA: H0 synthetic 472832 QP/step, global `D_R jpeak=3.1676918514138728 1/m`, thermal `0.066379552082746485 1/m`, numerical QP/CSR closure PASS. **Это архивный H0, не U0 FEM.**
4. Negative unit: намеренно искажённый `thermal_qp_count` → `VOLUME_QP_COUNT_MISMATCH`, STOP; PASS.

**Не проверены:** конкретная Windows версия Python/API path guard, крупная U0 runtime/RAM/сходимость solver, U0 physical numerical values, полноценное 3D angular signed разложение. При STOP научная проблема остаётся открытой; нет разрешения на повторный solver в том же пакете.

## 5. Что делать по первому физическому U0

После получения реального evidence, **до любого mesh refinement** провести независимый аудит числовых CSV: сверить global mechanical (explicit/equilibrium/history), thermal mass/diffusion/Robin, 6 шагов/QP sums, невязки, знаковую компенсацию, полярные области, t-dependence, зоны B6. Уточнить в коде недостающий φ-экспорт и независимый error/goal indicator; сравнить coarse U0 с предыдущими H0/H1 лишь как diagnostic, не Richardson/error convergence. Отдельно решить M1 (размер/место/ресурс) по данным, не заранее; возможность слишком дорогой M1/M2 — более поздняя развилка.

**На самой U0 нельзя заключить:** resolved stress/shape density в d≤100мкм; поле в непрерывной CAD sphere; пространственную/временную сходимость; истинную локальную ошибку или причину ранее наблюдавшихся pole effects. Наличие 20 pore Tri6 и 0 nearwall corner-centroids не исключает физический coarse exploratory solve, но запрещает такие точные выводы.
