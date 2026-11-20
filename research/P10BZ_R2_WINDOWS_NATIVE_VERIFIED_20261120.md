# P10BZ R2 — независимая приёмка Windows native unit-only свидетельств

**Дата:** 20.11.2026. **Статус:** `P10BZ_WINDOWS_UNIT_ONLY_OK`, инженерный этап P10BZ **закрыт в пределах unit/source verification**. Физические FEM H0/H2 не запускались. Первичный вход — новый пользовательский `P10BZ_EVIDENCE(1).zip`, сохранён ниже в неизменном виде.

## 1. Первичные байты и provenance

`research/evidence/P10BZ_R2_WINDOWS_VERIFIED_20261120/input/P10BZ_EVIDENCE.zip`: **SHA-256 `b68069784a1af6e15e7d5b5d5f66956305e3b5159410bdbf9fa339fe6d4c080e`**, ZIP integrity PASS, **5 файлов**: `P10BZ_RESULT.txt` (1572 B), `cmake_configure.txt` (678 B), `cmake_build.txt` (26368 B), `temporal_native_unit.txt` (2359 B), `dependency_native_unit.txt` (429 B). Не требовать повторной передачи этих результатов.

Инструмент точно идентифицирован как **`P10BZ_R2_BUNDLED_44_SHA_WINDOWS_MEMORY_FIX_NO_FEM`**. Исходный распространённый архив R2 SHA-256 `1579ef091864c6f41d9e4964cc77beb4949bd67efe884505216785c67acaeb88`. Следы R1 STOP сохранены отдельно, R2 не подменяет исторический журнал R1.

| Проверка Windows R2 | Первичное наблюдение |
|---|---|
| Original project HEAD до/после | точный `90fd2559c0224ac0a7d2dbe2fe081a6a319080e4` |
| Git index/working/untracked до/после | **`0/7/4`**, fingerprint **`bb376579544e328291674fa91d20c7b8a4b9d4a306fd7a3af47c172cedb75258`** оба раза |
| Bundled SHA gate | **36 historical +8 components =44/44 PASS** |
| Compiler/build system | GNU **13.1.0**, CMake **4.4.3**, `MinGW Makefiles` Release, OpenMP CXX **4.5** |
| CMake configure | `CMAKE_CONFIGURE_EXIT=0`; `P10BZ_R2_WINDOWS_MEMORY_SOURCE_SHA256_OK` подтверждён |
| CMake build | **exit0**; `win_process_memory.cpp.obj` действительно скомпилирован и оба EXE слинкованы |
| Temporal unit | native **exit0**, обязательный маркер `P10BY_TEMPORAL_THERMAL_QP_NATIVE_UNIT_OK` |
| P10I dependency unit | native **exit0**, обязательный `P10I_PRODUCTION_ADJOINT_OK` |
| Файлы журнала сборки | **31 унаследованное предупреждение**, ни одного fatal `error:`/`undefined reference` |
| User original worktree | `ORIGINAL_STATE_PRESERVED=YES_BY_READ_ONLY_COMPARISON` |
| Итог | `TESTS_PASSED=2/2`, `RESULT=P10BZ_WINDOWS_UNIT_ONLY_OK`, `PHYSICAL_FEM_RUNS=0` |

Нативные Windows EXE SHA-256 (взяты из R2 result, **не** исторический P10BE EXE):

* `p10by_temporal_native_unit.exe`: **`1b62634ff526fde5b071b5143a46c493ece66aeeff9d293a04b5f9a37e8d9571`**;
* `p10by_optin_dependency_selftest.exe`: **`9630fd726c09ae7d1662956ee6b4656cd95350b38b166744f45c5885557bb355`**.

## 2. Численный контроль, без физической интерпретации

Windows temporal stdout содержит ровно **8** `P10BY_HISTORY_UNIT_OK` (режимы `R/top`, временные сетки `6×150`, `12×75`, `18×50`, `36×25 s`), **144** синтетических шага, **14 544** эквивалентных QP CSV-строк, max step **`|QP−CSR|=5.107025913276e−15`**, `P10BY_CORRUPTION_STOP_UNIT_OK matrix_mass=1 robin_load=1`. Для top Robin integral >0, для R top Robin=0. Это самопроверка synthetic operator, **не** реальный H0 thermal field или spatial/time convergence.

Сравнение с P10BY Linux stdout после нормализации CRLF обнаружило **не побайтовое равенство** между платформами: в temporal двух строках `top` для 12 и 18 шагов разница лишь в накопленной машинной погрешности `allstep_abs_error` порядка `5.6e−17`; все структуральные счётчики/финальный маркер совпали. У P10I 9 из 14 численных полей отличаются в последних разрядах, max абсолютная разность отображённых метрик **`2.881e−11`** (не критерий физической погрешности); Windows **собственный native selftest успешен**. Нельзя объявлять Windows↔Linux stdout byte-identical, но unit validity confirmed.

P10I контроль: **6 моделей ×3 функционала=18 cases**, `replayed_steps=216`, `max_window=4`, adjoint equilibrium relative `5.410927883335e−13`, прочие поля в первичном `dependency_native_unit.txt`. Это тест программной зависимости, не подтверждение выполнения нового P10BX hook в физической обратной тепловой задаче.

## 3. Что закрыто, что остаётся неизвестным

**Подтверждено:** source reproduction, real Windows compiler configuration, linking exact Win32 helper + `Psapi` (R1 linker STOP устранён), native execution двух unit, хеши новых EXE, исходный dirty worktree не изменился по read-only Git fingerprint. R1 и R2 не надо повторять.

**Не проверено:** реальный `P10BX_THERMAL_QP_STEP_BINS.csv` / `P10BX_THERMAL_STEP_AUDIT.csv`, выполнение полного `stage3d10w_analytic_adjoint` с opt-in hook на физической H0, действительная память/время такого run, `D_R jpeak` сходимость. `SPATIAL_CONVERGENCE_NOT_PROVEN`, temporal convergence полной `D_R jpeak` не доказана, historical P10BE_H2 EXE SHA **UNKNOWN**.

Следующий **проект** — одна ограниченная H0 `R/EDV_VAR ξ=0, steps=6, dt=150s` с полной тепловой QP/CSR проверкой и точной фиксацией исходников/mesh/EXE. Подготовленный без запуска протокол `research/P10CA_SINGLE_H0_THERMAL_QP_PHYSICAL_PROTOCOL_DRAFT_20261120.md`. **Нужна новая отдельная санкция исследователя** до любого physical solve или `--preflight`.

**Исходные материалы:** `research/evidence/P10BZ_R2_WINDOWS_VERIFIED_20261120/input/P10BZ_EVIDENCE.zip` и `derived/P10BZ_R2_AUDIT.txt`; пакет R2 и предыдущее объяснение R1 STOP остаются неизменными.
