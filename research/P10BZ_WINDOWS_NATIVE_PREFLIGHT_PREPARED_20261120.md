# P10BZ — автономный Windows native unit-only preflight, подготовка R1

**Дата:** 20.11.2026. **Основание:** отдельное согласие исследователя «разрешаю. сделаем следующий этап» относится к подготовке и безопасной native QA, **не** к физическому H0/H2. **Статус:** `PREPARED_LINUX_VERIFIED; WINDOWS_RUN_PENDING; FEM=0`. Это проверка исполняемости диагностического контракта, не новый физический результат.

## 1. Проверяемая постановка

P10BY синтетически сопоставил thermal QP/CSR для 8 историй (144 шага), но не имел CMake и Windows native test. Узкий вопрос P10BZ: можно ли собрать *точно опубликованные* исходники в новом независимом каталоге Windows с двумя безопасными тестовыми main, обнаруживать дрейф SHA, сохранять native exit/маркеры и удостовериться, что исходное рабочее дерево не изменилось? Ответ требует пользовательского Windows evidence; текущий этап доставляет проверяемый инструмент и контрольную Linux-проверку его исходников.

## 2. Пакет и происхождение

Архив: `tools/P10BZ_WINDOWS_NATIVE_PREFLIGHT_R1_20261120.zip` (корневой одноимённый каталог, **47 файлов**, **186199 байт**, **SHA-256 `4c1193e3ba9076427d11d42399e93e38fbb4ccafe6b84ce9e44753fc8f9311db`**). `unzip -t`: без ошибок. В ZIP нет `.exe`, `.msh`, `.vtu`, `.bin` и физической истории.

* `source/pinned`: **35/35** исторических P10BM `src/`/`tests/` из состояния исходного Windows проекта `90fd2559c0224ac0a7d2dbe2fe081a6a319080e4`, сверка по неизменённому P10BY SHA-манифесту `bce45c5757796ecc505ca6e0899de912c4ad4441fb05d007f1d2c41192d2f2ce`.
* `source/p10bw` и `source/p10bx`: **5/5** точных опубликованных P10BW/P10BX компонентов; `source/p10by`: **2/2** P10BY native entry/test `.cpp`, **1** исходный манифест, **1** комплектный CMake. Запускатель до конфигурации проверяет всего **35+8=43 source/component SHA** и SHA манифеста.
* Комплектный `source/p10by/CMakeLists.txt` отличается от уже опубликованного исходного P10BY **только** использованием `pinned_forward_path` в строке `STAGE3D10K_SOURCE_ROOT` для нормализации Windows-разделителей. ZIP-версия SHA-256 `e2106125e359af41215ec190726e22ccd7210f51aaf02d7d852546072390c98e`; опубликованный P10BY CMake SHA-256 `ad65850d715804e69ffdf0bb8a63bb0653142d26a4a3315c11a2527b06b6723d` не изменён. Физический/диагностический C++-оператор **не** менялся.

## 3. Протокол исполнителя в Windows (ещё не проведён)

Распаковать целиком **в новый каталог вне** `G:\ildar\Stage3D07`; двойной щелчок по `01_P10BZ_RUN_NATIVE_TESTS.cmd`, который запускает PowerShell 5.1 `P10BZ_Run_Native.ps1`. Он в режиме чтения использует `git rev-parse HEAD`, `git status --porcelain=v1` и `GIT_OPTIONAL_LOCKS=0`; ожидаемый исходный HEAD — точный исторический `90fd2559...`, а индекс и untracked фиксируются **по свежему статусу** до и после (историческое `0/7/4` не постулируется текущим). Сверяет 43 SHA, пути `C:\mingw64\bin\g++.exe` (GNU 13.1.0), `mingw32-make.exe`, `C:\Program Files\CMake\bin\cmake.exe`, Git. Без буквальной фразы `TEST P10BZ` файлы сборки не создаются.

После подтверждения создаётся новый `P10BZ_RESULTS_*` рядом с инструментом. CMake `MinGW Makefiles`, Release, OpenMP по доступности, `--parallel 2`, **ровно две цели**:

1. `p10by_temporal_native_unit.exe`: `P10BY_TEMPORAL_THERMAL_QP_NATIVE_UNIT_OK series=8 steps=144 qp_csv_rows=14544 corruption_stops=2/2`;
2. `p10by_optin_dependency_selftest.exe`: `P10I_PRODUCTION_ADJOINT_OK models=6 functionals=3 cases=18`.

Отчёт требует native `exit 0` у обеих программ, маркеры, SHA обоих новых EXE, повторное считывание исходного Git, а для успеха `ORIGINAL_STATE_PRESERVED=YES_BY_READ_ONLY_COMPARISON`. Файлы `P10BZ_RESULT.txt`, configure/build/test logs упаковываются в **один** `P10BZ_EVIDENCE.zip` без EXE и сеток. STOP сохраняется как отдельный status, никаких восстановлений/изменений исходного дерева. Ни `--preflight`, ни mesh, ни `H::solve_forward`, ни `reverse_scan`, ни физические H0/H2 в сценарии не вызываются.

**Оценка ресурсов, не факт измерения:** 5–20 минут, 2–8 GiB RAM, до 1 GiB новых файлов, два параллельных задания. Не запускать старые P10BP/P10BQ повторно и не менять JOM/Qt Creator build.

## 4. Фактический контроль подготовленного пакета (Linux)

| Проверка | Установленный результат |
|---|---|
| Сверка bundled P10BM + P10BW/BX source | SHA-256 40/40 PASS |
| P10BY native entry и temporal unit, P10BY-манифест | точные опубликованные SHA PASS |
| Сверка ZIP-версии CMake | `e2106125...`, явное контролируемое отличие пути |
| `g++ -std=c++20 -O2 -Wall -Wextra -Wpedantic` из **пакетных исходников** | обе executable targets compile exit 0; наследованные warnings не скрыты |
| Исполнение двух пакетных Linux native unit | оба exit 0; stdout побайтово совпадает с ранее опубликованным P10BY |
| Архив ZIP | 47 файлов, `unzip -t` PASS, бинарных/mesh payload нет |
| Windows PowerShell 5.1 / MinGW / CMake configure | **NOT RUN / PENDING** — Windows недоступен, Linux `cmake` отсутствует |
| Физический FEM и Windows исходное дерево | **0 запусков / не тронуто**, актуальный status будет проверен на Windows |

Ни один Linux unit не решает тепловую или механическую FEM задачу; синтетические `theta_n, psi_n` не заменяют физическое поле.

## 5. Точка остановки и следующий этап

P10BZ R1 остаётся **ожиданием верификации** до получения от исследователя одного `P10BZ_EVIDENCE.zip`. Проверить его native exit, маркеры, реальные EXE SHA, CMake compiler/cache, source SHA и неизменность Git. При STOP расследовать только на основе коротких логов, без молчаливой замены компилятора или исходников. **Только затем** обсуждать отдельный проект H0 `R/EDV_VAR ξ=0`, `6×150 s`, с отдельным согласованием физического solve и ресурсного бюджета. H2 и многосеточная кампания не разрешены.

`SPATIAL_CONVERGENCE_NOT_PROVEN`; временная сходимость полной `D_R jpeak` не доказана; historical `P10BE_H2` EXE SHA **UNKNOWN**; реальный thermal reverse P10P hook пока не запускался.

**Первичные материалы:** архив и `README_RU.md` в `tools/P10BZ_WINDOWS_NATIVE_PREFLIGHT_R1_20261120/`; подготовительный результат `research/evidence/P10BZ_PREPARED_20261120/derived/P10BZ_PREPARATION_RESULT.txt`. Исторические исходники и журналы P10BY не изменены.
