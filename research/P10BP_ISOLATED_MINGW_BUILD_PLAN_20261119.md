# P10BP — следующая чистая сборка с установленным MinGW GNU 13.1.0

Дата 19.11.2026. **Текущий статус: Windows P10BP исполнен; чистая конфигурация и сборка четырёх целей прошли, тесты не завершены из-за пустого `Start-Process.ExitCode`.** Исходный текст ниже описывает план *до* запуска. Результаты и первичные файлы: `research/evidence/P10BP_WINDOWS_BUILD_20261119/README_RU.md`.

## Исходные факты

P10BM: исходники опубликованы на отдельной GitHub ветке `research/p10bi-local-seven-sources-20261119`, точный SHA `90fd2559c0224ac0a7d2dbe2fe081a6a319080e4` доступен; семь исходников совпали с P10BG-кандидатом. P10BH: четыре unit/selftest старых Windows EXE прошли, но build provenance EXE неизвестен. P10BN R1 и R2 остановились **до** clone/build: R1 — Int32-форматирование, R2 — защищённый отказ из-за JOM.

P10BO — первичный Windows `P10BO_TOOLCHAIN_REPORT.txt` (SHA-256 `7887b95b6910880e02ac350a7442aa14a8c58e5762ff852ecf28c4eb3d9f300b`): compiler `C:/mingw64/bin/g++.exe`, ID GNU, version 13.1.0, platform MinGW, Release, OpenMP ON. Старый CMake generator `NMake Makefiles JOM` и `CMAKE_MAKE_PROGRAM=jom`; `jom.exe`, `mingw32-make.exe`, `g++.exe` не обнаружены в обычном PATH. **Факт отсутствия make в PATH не равен отсутствию файла `C:\mingw64\bin\mingw32-make.exe`**.

## Исполняемое решение

Поскольку [официальный CMake MinGW Makefiles](https://cmake.org/cmake/help/latest/generator/MinGW%20Makefiles.html) требует `mingw32-make` под Windows/MinGW, P10BP проверяет **конкретный** `C:\mingw64\bin\mingw32-make.exe` перед любыми clone/configure/build. При его наличии использует **новую** отдельную `MinGW Makefiles` конфигурацию с точно проверенным GNU13.1.0 компилятором, не изменяя старую JOM конфигурацию. Если make отсутствует, только первичный STOP+ZIP; никаких скачиваний/установок или неконтролируемых замен.

После preflight и явного ввода `BUILD P10BP` создаётся отдельная папка `G:\ildar\P10BP_ATTEST_*` с клоном публичной GitHub ветки, checkout exact SHA и новым CMake build. Логируемые команды по смыслу:

```text
cmake -S <new_clone> -B <new_build> -G "MinGW Makefiles" -DCMAKE_BUILD_TYPE=Release -DCMAKE_CXX_COMPILER=C:/mingw64/bin/g++.exe -DCMAKE_MAKE_PROGRAM=C:/mingw64/bin/mingw32-make.exe -DSTAGE3D06P_OPENMP=ON
cmake --build <new_build> --config Release --target stage3d10v_analytic_shape_unit stage3d10y_analytic_shell_unit stage3d10be_temporal_unit stage3d10be_temporal_polar_audit --parallel 4
```

Запуски: три `*_unit.exe` без аргументов и `stage3d10be_temporal_polar_audit.exe --selftest`. Все четыре коротких теста требуют exit 0 и контрольные маркеры. Сохраняются configure/build logs, SHA-256 новых EXE, stdout/stderr тестов, исходный SHA и Git status до/после. ZIP отчёта `P10BP_EVIDENCE.zip` **не включает** EXE, огромные FEM данные и полный CMakeCache. Старый `G:\ildar\Stage3D07` не изменяется.

## Приёмка и ограничения

- Результат `P10BP_NEW_WINDOWS_BUILD_AND_FOUR_TESTS_OK` **не объявлять** без независимой проверки содержимого `P10BP_EVIDENCE.zip` и контрольных маркеров.
- Новый генератор отличается от старого JOM: успешный P10BP аттестует **новые** EXE из exact SHA, но не доказывает происхождение или битовую идентичность исторических P10BE EXE.
- Оценка времени 5–20 мин, ОЗУ 2–8 GiB (не измерения); свободное место на G: желательно ≥3 GiB. Никаких больших FEM запусков.
- После инженерного подтверждения следующий научный приоритет — пространственно-временная сходимость полной `D_RJ` и приполюсная компенсация компонентов P10BB/P10BE/P10AZ; прямую/сопряжённую задачи каждого опыта решать на одной сетке по P10AO. Сходимость пока **не доказана**.

Инструмент: `tools/P10BP_MINGW_CLEAN_BUILD_ONECLICK_20261119.zip`, русская инструкция `tools/P10BP_MINGW_CLEAN_BUILD_20261119/README_RU.md`. Следующий пользовательский файл — **один `P10BP_EVIDENCE.zip`**. При STOP не повторять без анализа.

## Фактическое исполнение P10BP (19.11.2026)

Предоставлен подлинный `P10BP_EVIDENCE.zip` (SHA-256 `6e3ff8880aa3abd2b4ff40263068c0ff20125f57d5485a6ce499d9cbc6e528e3`). Проверено: clone exact SHA, `SOURCE_BEFORE_BUILD_CLEAN=YES`, `CONFIGURE_EXIT=0`, `BUILD_EXIT=0`; четыре финальные строки CMake `Built target` есть. GNU13.1 `MinGW Makefiles` фактически использован, исходное Git-состояние `0/7/4` осталось неизменным. **P10V stdout содержит маркер OK, но `TEST_EXIT=пусто`; остальные три selftest не запускались.** Поэтому итог `P10BP_NEW_WINDOWS_BUILD_AND_FOUR_TESTS_OK` **не достигнут**. В build log есть 103 предупреждения, их причина не исследована полностью. План P10BP не повторять: сборка уже готова.

**Действующий следующий шаг:** выполнить только `tools/P10BQ_FOUR_TEST_RECOVERY_ONECLICK_20261119.zip` с точным предварительно проверенным P10BP output root; 4 коротких EXE, контроль `$LASTEXITCODE`, SHA-256 и маркеров, без повторного build/FEM. Ожидать только `P10BQ_EVIDENCE.zip`. Историческая P10BE_H2 исполняемая программа не аттестована задним числом.

**Актуализация после P10BQ R1 Windows STOP:** первичные R1 отчёты и диагноз ошибки PowerShell массива — `research/evidence/P10BQ_R1_WINDOWS_STOP_20261119/README_RU.md`; старый архив P10BQ R1 теперь **архивный и не должен запускаться**. Исправленный единственный следующий инструмент — `tools/P10BQ_FOUR_TEST_RECOVERY_ONECLICK_R2_20261119.zip` с меткой `P10BQ_R2_EXACT_REPORT_LINES_FIX`. Исходная успешная сборка P10BP остаётся без изменения; 4 теста ещё не аттестованы.

**Актуализация после P10BQ R2 Windows STOP:** R2 подтвердил **все четыре EXE SHA**, CMakeCache, 5/5 строк отчёта, P10V и P10Y тесты с exit 0; строгое полное сравнение текстового маркера P10Y без учёта штатных полей `models=6 functionals=4 bins=2` ошибочно прервало сценарий. Остальные два P10BE теста в R2 не запускались. Первичные данные — `research/evidence/P10BQ_R2_WINDOWS_STOP_20261119/README_RU.md`. Действующий следующий инструмент — **только** `tools/P10BQ_FOUR_TEST_RECOVERY_ONECLICK_R3_20261119.zip`, маркер в начале строки, после него конец строки или пробельный разделитель; без повторной сборки или FEM.

**ИТОГ цепочки P10BP→P10BQ R3, 19.11.2026:** R3 первичные `P10BQ_EVIDENCE(2).zip` и TXT зарегистрированы в `research/evidence/P10BQ_R3_WINDOWS_OK_20261119/README_RU.md`; все четыре новых unit/selftest получили нативные exit 0 и контрольные маркеры, `TESTS_PASSED=4/4`. Это закрывает инженерный preflight исходный exact Git SHA → чистая новая GNU Release сборка → EXE SHA-256 → четыре успешных unit/selftest. Никакие инструменты P10BN/P10BO/P10BP/P10BQ больше **не запускать**. Следующий научный read-only P10BR уже выполнен на имеющихся CSV, протокол в `research/P10BR_CROSS_AXIS_LOCALIZATION_20261119.md`. Исторический P10BE_H2 EXE SHA от нового коммита не назначен, физическая/пространственно-временная сходимость не доказана.
