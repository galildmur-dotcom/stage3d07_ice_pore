# P10BP Windows: новая MinGW сборка успешна, selftest прерван ошибкой оболочки

Дата первичного запуска: **19.11.2026, 17:36:58 +05:00**. Статус: **configure/build четырёх целей подтверждён; четыре unit/selftest ещё не подтверждены**.

## Первичные файлы и проверка целостности

- `input/P10BP_EVIDENCE.zip` — **оригинальный** файл пользователя, 6334 байта, SHA-256 `6e3ff8880aa3abd2b4ff40263068c0ff20125f57d5485a6ce499d9cbc6e528e3`.
- `input/P10BP_RESULT.txt` — точная распаковка соответствующего члена ZIP, 2084 байта, SHA-256 `74ecdccec83e04c89e47ca8451380a2eb5923b1125c9721365b32b168219450a`.
- `unzip -t` для исходного ZIP: 5/5 членов OK, длина распакованных файлов 81 100 байт. Сохранены оригинальные сжатые configure/build и первичные stdout/stderr P10V; отдельные логи не переписывались.
- SHA-256 логов, указанные в первичном отчёте, независимо пересчитаны из ZIP и совпали.

## Факты, в пределах предоставленного доказательства

| Контроль | Факт |
|---|---|
| Git remote/source | Отдельный GitHub clone `research/p10bi-local-seven-sources-20261119`; exact `90fd2559c0224ac0a7d2dbe2fe081a6a319080e4`; `SOURCE_BEFORE_BUILD_CLEAN=YES` |
| Исходный Windows проект | `ORIGINAL_HEAD_BEFORE=ORIGINAL_HEAD_AFTER=90fd2559...`; Git status `0/7/4` до/после; `ORIGINAL_STATE_PRESERVED=YES_BY_READ_ONLY_CHECK` |
| Изолированная папка | `G:\ildar\P10BP_ATTEST_20261119_173658_19404` |
| Конфигурация | `MinGW Makefiles`, `Release`, `C:/mingw64/bin/g++.exe`, GCC `13.1.0` / `x86_64-w64-mingw32`, OpenMP ON; `CONFIGURE_EXIT=0` |
| Сборка | `BUILD_EXIT=0`, в журнале все четыре строки `[100%] Built target ...` |
| Предупреждения компилятора | В build log **103** строки с `warning:` (в том числе `-Wmisleading-indentation`, неиспользуемые функции). Это не errors, но отдельный аудит качества кода ими **не закрыт**. |

| Цель | Сборка | Запуск P10BP | Подтверждение exit 0 |
|---|---|---|---|
| `stage3d10v_analytic_shape_unit` | OK | stdout: `P10V_ANALYTIC_SHAPE_UNIT_OK`; stderr пуст | **Нет**: `TEST_EXIT_...=` пуст |
| `stage3d10y_analytic_shell_unit` | OK | Не запускался | Нет |
| `stage3d10be_temporal_unit` | OK | Не запускался | Нет |
| `stage3d10be_temporal_polar_audit` | OK | Не запускался | Нет |

В P10V stdout также: `residual_rel=5.4808975582e-09`, `history_rel=3.0865923249e-07`, `functional_rel=3.3692518365e-06`, `models=6`, `functionals=4`, `quadrature_points=27`. **SHA-256 фактически созданного P10V EXE** из первичного Windows отчёта: `02f14785ebc5dbe841dbec8b836b163858ff0bcbe311a53eec3dc24bb1da4721`. Для остальных EXE P10BP не успел зафиксировать SHA.

## Диагноз и разрешённое продолжение

Исходный скрипт P10BP в `Run-Selftest` вызывает `Start-Process -PassThru`, ждёт `WaitForExit(120000)`, затем читает `$process.ExitCode`. В присланном отчёте `$process.ExitCode` сериализовался как **пустая строка**, а проверка интерпретировала это как провал (`RESULT=P10BP_STOPPED: Selftest failed: stage3d10v_analytic_shape_unit`). Вывод P10V свидетельствует о достижении проверочного маркера, **но не доказывает нормальный код выхода**. Это согласуется с ошибкой получения кода возврата оболочкой; альтернативные причины реального ненулевого выхода пока не исключены.

Следующий минимальный этап — **P10BQ**: из того же готового P10BP `build` непосредственно запустить четыре коротких EXE, используя `$LASTEXITCODE` после каждого процесса. Перед запуском удостовериться в точном Git SHA, чистоте isolated source, CMakeCache, всех четырёх EXE и совпадении P10V EXE SHA. Не выполнять clone, CMake build, Git reset/clean, полный FEM; не менять рабочий `G:\ildar\Stage3D07`. Инструмент: `tools/P10BQ_FOUR_TEST_RECOVERY_ONECLICK_20261119.zip`; инструкция: `tools/P10BQ_FOUR_TEST_RECOVERY_20261119/README_RU.md`. Новый пользовательский файл: **один `P10BQ_EVIDENCE.zip`**.

**Научные ограничения:** нельзя использовать новый SHA EXE для ретроспективной аттестации исторического расчёта `P10BE_H2_LOGS_20261118_182525`, а успешная сборка и любые четыре unit/selftest сами по себе не подтверждают пространственную/временную сходимость полного `D_RJ`.

**Дополнение 19.11.2026 после P10BQ R1:** первичный R1 `P10BQ_EVIDENCE.zip` показал другую ошибку оболочки — пять строк отчёта P10BP были объединены в одну при построении массива PowerShell, поэтому тесты **не запускались**. Эти первичные файлы — `research/evidence/P10BQ_R1_WINDOWS_STOP_20261119/README_RU.md`. Предыдущая ссылка на пакет P10BQ без суффикса R2 теперь **историческая**; действующий пакет только `tools/P10BQ_FOUR_TEST_RECOVERY_ONECLICK_R2_20261119.zip`, с явной меткой версии R2. Точный чистый SHA P10BP и `BUILD_EXIT=0` не оспорены; исполнять R2 только по инструкции, без новой сборки/FEM.

**Дополнение после P10BQ R2:** `research/evidence/P10BQ_R2_WINDOWS_STOP_20261119/README_RU.md` содержит оригиналы двух успешных P10V/Y тестов (`exit=0`), SHA всех четырёх EXE и диагноз ложного STOP на диагностическом суффиксе маркера P10Y. R2 также архивный; **текущий R3** — `tools/P10BQ_FOUR_TEST_RECOVERY_ONECLICK_R3_20261119.zip`. Два P10BE unit/selftest пока не запускались в этой новой сборке; исторический P10BE_H2 EXE SHA неизвестен.
