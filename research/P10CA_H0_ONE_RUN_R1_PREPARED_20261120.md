# P10CA — автономный One Click R1 для одного H0 R/EDV_VAR ξ=0

**Дата:** 20.11.2026. **Разрешение:** исследователь ответил «разрешаю» на отдельный точный запрос **подготовки автономного пакета и одного физического H0** по `research/P10CA_SINGLE_H0_THERMAL_QP_PHYSICAL_PROTOCOL_DRAFT_20261120.md`, с оценочными ограничениями 10 мин/8 GiB/1 GiB. Это **не** разрешение H1/H2, многочасового FEM, изменения исходного Windows дерева, многократной кампании или автоматических повторов. **Текущий результат:** `P10CA_R1_PREPARED_LINUX_SOURCE_AND_SAFE_EXE_VERIFIED`, **Windows compile PENDING, physical FEM runs=0**.

## Один научный вопрос

При заданной физической тепловой/механической истории на **той же H0** и аналитической Tet10 скорости `R`, может ли диагностическая квадратура по 100 near-pore radial/polar ячейкам + отдельный top Robin воспроизвести неизменённую CSR составляющую `D_R jpeak` по 6 физическим временным шагам и в сумме? Получить реальные, а не manufactured, пространственно-угловые вклады без объявления сходимости.

## 1. Проверенный источник и дистрибутив

Публикуется `tools/P10CA_H0_ONE_RUN_R1_20261120.zip`: **49 файлов, 192489 байт, SHA-256 `cce5d3aec02062661abd3f30913e29c2c646748819a83530053b8b00a420a774`**, `unzip -t` PASS, нет `.exe`, `.msh`, `.bin`, `.vtu` либо физических результатов. Архив автономен, но физическую H0 сетку **не включает**; он её читает из оригинального Windows каталога.

В пакете неизменённые R2 source blobs: **35/35** исторических P10BM по исходному P10BY манифесту, плюс точный `src/win_process_memory.cpp` Git blob `26a4437ae81d41fe6918e9beea2cd2c49ec339ff` / SHA-256 `c299d890...`, плюс **8/8** P10BW/BX/BY/R2 компонентов. Всего source **44/44 SHA PASS** независимо от кода сценария. Новый **CMake только сборки**, SHA-256 `f37f912c2a68c701ee1cc954739c9fee23bf97b702cb9146f8793d40ffae6369`, pin-check **35+1+8**, target `p10ca_h0_analytic_qp` из `source/p10bx/src/stage3d10w_analytic_adjoint.cpp`, которое относительным include выбирает **ровно** diagnostic P10BX P10P. Компиляция C++20, OpenMP, `STAGE3D10BX_THERMAL_QP_DIAGNOSTIC=1`, `STAGE3D10W_ANALYTIC_SHAPE` задан в точном W source, Windows `win_process_memory.cpp` + `Psapi`; без FD `--delta-scan-um`. **CMake configure/build не запускает физику** и не содержит тестовой/ручной solve-цели.

## 2. Что фактически проверено без физического solve

Из точной копии source нового пакета на Linux собран полный target `g++ -std=c++20 -O2 -Wall -Wextra -Wpedantic -fopenmp`, с указанным P10BX opt-in macro: **compile/link exit0**. `--help` exit0, печатает правильный analytic P10W контракт; `--selftest` exit0 с `P10I_PRODUCTION_ADJOINT_OK models=6 functionals=3 cases=18` и `P10W_DEPENDENCY_SELFTEST_OK analytic_coupling_verified=0`. Отрицательный вызов `--delta-scan-um 1.25` закономерно отвергнут `P10W_ERROR ... finite-difference geometry options are forbidden`, exit2; **не было физического solve**. Унаследованные C++ warnings остаются. Локального `cmake`/Windows MinGW здесь нет — CMake Windows success **не аттестован**. `G:\ildar\Stage3D07` в этом этапе не использовался и не изменялся.

## 3. Windows процедура с двумя явными разрешающими фразами

После распаковки в **новый** каталог вне `G:\ildar\Stage3D07` запустить `01_P10CA_ONE_H0.cmd`. PowerShell 5.1 до любой записи читает actual original HEAD/status и требует exact `90fd2559c0224ac0a7d2dbe2fe081a6a319080e4`, фиксирует counts/fingerprint, проверяет 44+1 SHA, CMake4.4.3/MinGW GNU13.1.0, точный `G:\ildar\Stage3D07\meshes\H0.msh` (Gmsh2.2 ASCII, `nodes=10845,Tet10=7388,pore_Tri6=136,top_Tri6>0`) и H0 SHA, свободное место 2 GiB. Нет подстановки сетки, нет `--preflight`.

**Первая фраза `PREPARE P10CA`** создаёт новый build рядом с инструментом, собирает **только физический target** (без его запуска), сохраняет CMake logs/EXE SHA, выполняет короткие `--help` и `--selftest` (NO FEM). **Вторая, отдельная фраза `RUN ONE H0 P10CA`** после повторной Git/mesh/EXE SHA сверки делает **единственный физический вызов**:

```text
p10ca_h0_analytic_qp.exe --mesh "G:\ildar\Stage3D07\meshes\H0.msh" --out "<NEW_ISOLATED_RESULTS>\H0_PHYSICAL_RUN" --steps 6 --dt 150 --mode R --cutoff-mm 5 --threads 4
```

Это template, а не запущенная здесь команда; исполнитель сам подставляет только новый каталог. Перед CreateProcess создаётся **невозвратный для данной распаковки** `P10CA_PHYSICAL_ATTEMPTED.txt`, чтобы остановить повторную физическую попытку тем же пакетом. Никакого Git checkout/reset/clean/stash/push или изменения исходных `meshes`, `build`, `LOCAL_RUNS`.

## 4. Ресурсы и STOP — без обещания аппаратной жёсткости

Оценка по архиву H0/P10W ≈109.77 с в другом режиме: **2–6 мин**, низкая достоверность; пользовательский бюджет ≤**8 GiB RAM**, ≤**1 GiB** новых файлов, ≤**10 min** резервного времени. Сценарий опрашивает дочерний физический процесс каждые **0.5 s**, данные каталога каждые **2 s** и останавливает при **9 min**, текущем process working/private memory **≥6 GiB**, либо каталоге **≥0.75 GiB**, оставляя запас до обозначенных пределов. Это **best-effort soft watchdog**, НЕ Windows Job Object/hard memory quota; скачки между опросами теоретически возможны. При ошибке исключений/нормативов/сетки/сорванном native exit — `P10CA_STOPPED`, архив свидетельств, **без автоматического повторного запуска**.

## 5. Ожидаемые доказательства, а не факт H0

Ожидание (проверка в самом scenario): один `R/EDV_VAR ξ=0`, 6×150 s, исходная одна H0 для прямого и сопряжённого решения, `ANALYTIC_TET10 central_fd_evaluations=0`, `P10W_ANALYTIC_ADJOINT_OK`, `P10BX_THERMAL_QP_INTEGRATED_OK ... steps=6 ... exported_rows=606 original_gradient_unchanged=1`, native exit0. `P10BX_THERMAL_QP_STEP_BINS.csv` должен содержать **606 data rows**, `P10BX_THERMAL_STEP_AUDIT.csv` **6**, на шаге ожидается **472 832** volume QP, за 6 шагов **2 836 992**; top Tri6 считывается фактически, 96×N_top top QP. Шаговый QP/CSR tolerance исходного кода `1e−10+1e−8×scale`, поэтапные суммы повторно проверяются независимым CSV контролем сценария. Полный all-step tolerance проверяет исходный P10BX hook. Действительная память/время/CSV ещё **UNKNOWN**.

На выходе **один** `P10CA_EVIDENCE.zip`: `P10CA_RESULT.txt`, локальный `P10CA_RUN_MANIFEST.json` (не официальная M01/M02 запись), configure/build/help/selftest/physical stdout/stderr и пять компактных CSV. Большие `.msh`, `.bin`, `.vtu`, EXE/checkpoints в ZIP не включаются. При STOP — остановиться и прислать один evidence (если ZIP не создан — result TXT). Никаких автоматических M01/M02 регистраций и ретроспективного присваивания EXE SHA старому P10BE.

`SPATIAL_CONVERGENCE_NOT_PROVEN`; сходимость полной `D_R jpeak` по времени также не доказана, historical P10BE_H2 EXE SHA **UNKNOWN**. Даже успешный один H0 — только локальный thermal QP/CSR факт на H0, не утверждение статьи о сеточной сходимости.

**Материалы:** исходный проект P10CA `research/P10CA_SINGLE_H0_THERMAL_QP_PHYSICAL_PROTOCOL_DRAFT_20261120.md`, ZIP и `README_RU.md` в `tools/`, подготовительный результат `research/evidence/P10CA_H0_R1_PREPARED_20261120/derived/P10CA_PREPARATION_RESULT.txt`. Следующий необходимый вход — **ровно один Windows `P10CA_EVIDENCE.zip`** после запускателя, либо его STOP report. Старые P10BZ R1/R2 повторять не надо.
