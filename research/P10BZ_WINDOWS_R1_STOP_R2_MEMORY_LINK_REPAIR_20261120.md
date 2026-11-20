# P10BZ — Windows R1 evidence, локализация STOP и автономный R2

**Дата:** 20.11.2026. **Статус:** R1 **WINDOWS_CONFIGURE_OK / NATIVE_LINK_STOP**; R2 **PREPARED_LINUX_VERIFIED / WINDOWS_R2_PENDING**. Исследователь передал первичный `P10BZ_EVIDENCE.zip`; разрешение относится только к native unit и подготовке исправления, **не** к физическому H0/H2.

## 1. Первичные измеренные факты Windows R1

Архив пользователя `P10BZ_EVIDENCE.zip`, SHA-256 `03764a251c9d296e8fc5271c0392ccf1b33b9a70ff1349aaff31902efe6632f5`, проверка ZIP **PASS**, ровно **3 текстовых файла**: `P10BZ_RESULT.txt` (1112 B), `cmake_configure.txt` (634 B), `cmake_build.txt` (26912 B); оба unit stdout **отсутствуют**, потому что build остановился до запусков.

| Проверка R1 | Фактическое свидетельство |
|---|---|
| Original Windows HEAD до/после | `90fd2559c0224ac0a7d2dbe2fe081a6a319080e4`, совпал |
| Git status до/после | `0/7/4` и SHA fingerprint `bb376579544e328291674fa91d20c7b8a4b9d4a306fd7a3af47c172cedb75258`, оба совпали |
| Bundled source SHA | `35+8=43/43` PASS |
| Компилятор/сборщик | MinGW GCC `13.1.0`, CMake `4.4.3`, `mingw32-make.exe`, OpenMP CXX `4.5` |
| CMake configure | exit `0`, `MinGW Makefiles`, source gate 35+5 PASS |
| `p10by_temporal_native_unit.exe` | **target built and linked**, но не исполнен |
| `p10by_optin_dependency_selftest.exe` | compile завершена, **link STOP** |
| `CMAKE_BUILD_EXIT` | **2** |
| Windows unit native exit / EXE SHA | не получены: ни один тест не запускался |
| Исходное дерево пользователя | `ORIGINAL_STATE_PRESERVED=YES_BY_READ_ONLY_COMPARISON` |

Одна фатальная строка компоновки:

```text
undefined reference to `stage3d06_peak_memory_kb_windows'
collect2.exe: error: ld returned 1 exit status
```

В журнале есть унаследованные предупреждения `-Wmisleading-indentation` / `-Wunused-function`, но **других `error:`/`undefined reference` не обнаружено**. Не смешивать «собран первый EXE» с «первый тест исполнялся»: ни одного unit stdout R1 нет. Это доказанный **ошибочный набор translation units R1**, а не обнаруженное нарушение QP/CSR и не отказ физического FEM.

## 2. Корневая причина и минимальный ремонт

Точный исходный `src/spatial_reology.cpp` содержит `#ifdef _WIN32` внешний `extern "C" long stage3d06_peak_memory_kb_windows();`, который используется `peakMemoryKB()`. В Linux эта ветка компиляции не активна, что объясняет, почему **R1 Linux unit компилировался**, а Windows link — нет.

В историческом Git tree Windows-код определён в **отдельном** `src/win_process_memory.cpp`: Git blob `26a4437ae81d41fe6918e9beea2cd2c49ec339ff`, SHA-256 `c299d890b0f3a04f86974fb664120a36681eef464ffbb617eabc8e57e07a5e09`, parent `90fd2559c0224ac0a7d2dbe2fe081a6a319080e4`. Файл не входил в 35-file P10BY manifest и по ошибке **не попал в R1 bundle**. Исторический `CMakeLists.txt` для настоящей `stage3d10p_partial_audit` на Windows явно добавлял этот файл и `Psapi`. R2 **восстанавливает это исторически проверенное правило**, не создаёт фальшивый stub для счётчика памяти.

Ремонт **только в новом автономном R2 архиве**:

1. `source/pinned/src/win_process_memory.cpp` — точная копия Git blob, проверена SHA-256 и `git hash-object`.
2. В P10BZ R2 `source/p10by/CMakeLists.txt` добавлены SHA gate этого файла, `if(WIN32) target_sources(p10by_optin_dependency_selftest PRIVATE .../win_process_memory.cpp)` и `target_link_libraries(... PRIVATE Psapi)`, по образцу исходного production CMake. SHA-256 R2 CMake `bbf5f43f17f2c607edf4cb12550058d519fc1668354c7b28d57ef6cfee483239`.
3. R2 PowerShell проверяет **35 original manifest +1 historical Win32 helper +8 components =44** SHA до сборки; после CMake configure требует маркер `P10BZ_R2_WINDOWS_MEMORY_SOURCE_SHA256_OK`. Новый build/результат создаётся в отдельной папке после `TEST P10BZ`; первоначальный G: Git остаётся read-only.

Никакой production исходник, физический оператор, тестовый main, исторический P10BY proposal, исходный Qt/JOM build либо dirty Windows worktree не изменён.

## 3. Верификация нового дистрибутива R2 в Linux

Архив `tools/P10BZ_WINDOWS_NATIVE_PREFLIGHT_R2_20261120.zip`: **48 файлов, 187857 B, SHA-256 `1579ef091864c6f41d9e4964cc77beb4949bd67efe884505216785c67acaeb88`**. `unzip -t` PASS, EXE/mesh/physical output нет. Независимо сверены SHA **35/35** по P10BY manifest, **1/1** Win32 helper и **8/8** компонентов из сценария (**44/44 PASS**); Git blob Windows helper совпал с историческим.

Оба native unit из исходников **комплектного R2** отдельно скомпилированы Linux `g++ -std=c++20 -O2 -Wall -Wextra -Wpedantic` и выполнились с exit 0; temporal `series=8 steps=144 qp_csv_rows=14544 corruption_stops=2/2 max_step_abs_error=5.107025913276e-15`, dependency `models=6 functionals=3 cases=18`; два stdout **побайтово совпадают** с опубликованными P10BY. При первой ручной Linux команде для dependency была пропущена необходимая уже существующая макроконстанта `STAGE3D10K_SOURCE_ROOT` (compile STOP); при точном её задании compile exit 0, code unchanged. Это процедурная проверка корректности ручной команды, не физический отказ.

Ограничение: Linux не компилирует Win32 helper (`if(WIN32)`), в окружении нет Windows MinGW и CMake. **Исправление Windows link является обоснованной реконструкцией, но не измеренным успехом.** Только новый пользовательский `P10BZ_EVIDENCE.zip` R2 даст native Windows exit/EXE SHA/test markers.

## 4. Следующая граница исследования

Попросить **один повтор безопасного R2**, не запускать R1 вновь, извлечь R2 в новую папку вне `G:\ildar\Stage3D07`. Предварительная R1 проверка оригинального дерева уже сохранена; R2 заново измерит state before/after. Ожидаются Windows `CMAKE_CONFIGURE_EXIT=0`, `CMAKE_BUILD_EXIT=0`, оба native `TEST_EXIT=0`, необходимые P10BY/P10I маркеры, реальные EXE SHA, `ORIGINAL_STATE_PRESERVED=YES_BY_READ_ONLY_COMPARISON`. При новом STOP — остановиться на доказательстве, без нового FEM.

`SPATIAL_CONVERGENCE_NOT_PROVEN`; temporal convergence полной `D_R jpeak` не доказана; historical P10BE_H2 EXE SHA `UNKNOWN`; физический P10P thermal reverse hook не исполнялся; H0/H2 FEM runs **0**. Отдельное разрешение физического H0 спрашивать **после** успешного Windows R2, а не в рамках исправления линковки.

**Первичные материалы:** `research/evidence/P10BZ_R1_WINDOWS_STOP_20261120/input/P10BZ_EVIDENCE.zip` — неизменённый пользовательский ZIP; `research/evidence/P10BZ_R1_WINDOWS_STOP_20261120/derived/P10BZ_R1_AUDIT.txt` — короткая независимая расшифровка; R2 ZIP и `README_RU.md` в `tools/`.
