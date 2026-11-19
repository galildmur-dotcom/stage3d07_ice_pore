# P10BQ R1 Windows STOP — ошибка проверки первичного отчёта, тесты не запускались

Получено 19.11.2026: пользователь предоставил **два первичных файла**:

| Файл | Размер | SHA-256 |
|---|---:|---|
| `input/P10BQ_RESULT.txt` | 995 байт | `1a36b9ed0259e5c35ac75443035935b828ccd8b5d69e97210378f12104396261` |
| `input/P10BQ_EVIDENCE.zip` | 645 байт | `dcdba1cdc5faac42e180505e79e5e877dedd8c716175170403ea851865f9f07c` |

Оригинальный ZIP проходит `unzip -t`, содержит **ровно один** файл `P10BQ_RESULT.txt` (995 байт), который побайтно совпадает с отдельно предоставленным текстовым файлом (`cmp`). Копии сохранены без редактирования.

## Проверенные факты

- `TOOL_REVISION=P10BQ_R1_DIRECT_NATIVE_LASTEXITCODE`.
- `DATE_LOCAL=2026-11-19T20:09:23.9767472+05:00`.
- `OUTPUT_ROOT=G:\ildar\P10BQ_TESTS_20261119_200923_15552`.
- `EXPECTED_SHA=ORIGINAL_HEAD_BEFORE=ORIGINAL_HEAD_AFTER=90fd2559c0224ac0a7d2dbe2fe081a6a319080e4`.
- `ORIGINAL_STATUS_BEFORE=ORIGINAL_STATUS_AFTER=0/7/4`, `ORIGINAL_STATE_PRESERVED=YES_BY_READ_ONLY_CHECK`.
- Изолированная P10BP исходная копия до тестов `HEAD=90fd2559...`, `ISOLATED_SOURCE_BEFORE_TESTS_CLEAN=YES`.
- `RESULT=P10BQ_STOPPED: P10BP report does not confirm: EXPECTED_SHA=... SOURCE_BEFORE_BUILD_CLEAN=YES CONFIGURE_EXIT=0 BUILD_EXIT=0 RESULT=P10BP_STOPPED...`.

**Диагноз с проверкой исходного кода R1:** в `foreach ($required in @('EXPECTED_SHA=' + $expectedHead, 'SOURCE_BEFORE_BUILD_CLEAN=YES', ...))` PowerShell 5.1 образовал **одну** строку из пяти ожидаемых фрагментов (в журнале они напечатаны в одной ошибке), поэтому `Contains()` не нашёл её в первичном P10BP отчёте. Отдельные пять строк, в том числе `CONFIGURE_EXIT=0` и `BUILD_EXIT=0`, в оригинальном `P10BP_RESULT.txt` действительно присутствуют. Таким образом остановка вызвана **ошибкой формирования верификационного списка**, а не недостающей сборкой или численным тестом.

**Граница:** P10BQ R1 остановился **до** проверки CMakeCache, SHA-256 четырёх EXE, ручного `TEST P10BQ` и выполнения **любого** теста. Не утверждать новые тестовые результаты. Не повторять P10BP или P10BQ R1.

## Исправление P10BQ R2

В исходном `.ps1` список создаётся как 5 самостоятельных заключённых в круглые скобки выражений в `@(...)`, отдельно проверяется `.Count -eq 5` и точное присутствие каждой строки в `ReadAllLines()`. После этого прежняя read-only проверка CMakeCache/EXE SHA и прямой запуск четырёх unit/selftest с `$LASTEXITCODE` остаются без изменения. **R2 на Windows ещё не испытан.**

Пакет `tools/P10BQ_FOUR_TEST_RECOVERY_ONECLICK_R2_20261119.zip`, инструкция `tools/P10BQ_FOUR_TEST_RECOVERY_20261119/README_RU.md`. Следующий первичный пользовательский файл — только **`P10BQ_EVIDENCE.zip`** из новой `P10BQ_TESTS_*` папки после R2 (даже при STOP). Никакого FEM, повторного clone/build, изменения рабочего Git или очистки исходной папки.
