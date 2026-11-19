# P10BQ R2 Windows — 2/4 теста выполнены с кодом 0, сценарий остановился на суффиксе маркера

Дата запуска 19.11.2026, 20:18:38 +05:00. **Уровень доказательства: успешная прямая проверка двух новых Windows EXE; третья и четвёртая программы не запускались в P10BQ R2.**

## Оригинальные пользовательские файлы

| Исходное имя вложения | Сохранено в Git | Размер, байт | SHA-256 |
|---|---|---:|---|
| `P10BQ_EVIDENCE(1).zip` | `input/P10BQ_R2_EVIDENCE.zip` | 1754 | `492bc6dfc8a18849023f479bd03102736218760d72dd9345ac2108c1c03f8ed0` |
| `P10BQ_RESULT(1).txt` | `input/P10BQ_R2_RESULT.txt` | 1938 | `bf686c3f31ba24a7b88cf6499400785ebce38b06e43ee7320e670d1f24ebc8ea` |
| `stage3d10v_analytic_shape_unit_combined.txt` | `input/stage3d10v_analytic_shape_unit_combined.txt` | 190 | `2ffd91d356cf521e8d779143ed34a000a0d49878699fe5b7cc2eb7ea71ed403d` |
| `stage3d10y_analytic_shell_unit_combined.txt` | `input/stage3d10y_analytic_shell_unit_combined.txt` | 249 | `d82253879caaccc47037f2bf6760d43432f8b090564a6570211d5a9720406adc` |

ZIP проходит `unzip -t` (3/3 членов, 2377 байт в распакованном виде). Все три извлечённых из ZIP файла **побайтно совпадают** с отдельно приложенными TXT. Копии оригиналов не переписывались; изменены только имена двух файлов при регистрации, что отмечено выше.

## Факты и аттестация

- `TOOL_REVISION=P10BQ_R2_EXACT_REPORT_LINES_FIX`; `P10BP_REQUIRED_REPORT_LINES_VERIFIED=5/5` — исправление первой ошибки R1 **сработало**.
- Исходная Git версия и isolated P10BP source: `90fd2559c0224ac0a7d2dbe2fe081a6a319080e4`, isolated source clean. Исходный Windows HEAD совпадает до/после; status `0/7/4` до/после; `ORIGINAL_STATE_PRESERVED=YES_BY_READ_ONLY_CHECK`.
- `REUSED_P10BP_RESULT_SHA256=74ecdccec83e04c89e47ca8451380a2eb5923b1125c9721365b32b168219450a` совпадает с ранее зарегистрированным первичным P10BP отчётом.
- `P10BP_CACHE_VERIFIED=MinGW Makefiles;Release;GNU13.1.0_EXPECTED_PATH;OPENMP_ON`.
- `PREFLIGHT=OK_FOUR_EXISTING_BINARIES_AND_ISOLATED_SOURCE`; исследователь ввёл `TEST P10BQ`.

Все **четыре новых EXE SHA-256** впервые документально доступны в одной первичной Windows аттестации:

| Программа | SHA-256 EXE |
|---|---|
| `stage3d10v_analytic_shape_unit` | `02f14785ebc5dbe841dbec8b836b163858ff0bcbe311a53eec3dc24bb1da4721` |
| `stage3d10y_analytic_shell_unit` | `15abab353994b0353c0783d8d53dc812e0bc970b3042e04e8e2ed40848afda54` |
| `stage3d10be_temporal_unit` | `4b7513affe02bc2b402edb7343923d5b10add4026b89aaa25ee84d4cd1340e72` |
| `stage3d10be_temporal_polar_audit` | `18593652a27bcce7b8286053460421ce6594506f8254cfffb8b52db48e25f363` |

| Тест | Нативный exit | Реальный stdout | Трактовка |
|---|---:|---|---|
| P10V shape unit | 0 | `P10V_ANALYTIC_SHAPE_UNIT_OK` | **Прошёл** |
| P10Y shell unit | 0 | `P10Y_ANALYTIC_SHELL_UNIT_OK models=6 functionals=4 bins=2` | **Прошёл; R2 ложно назвал отсутствие «точного маркера»** |
| P10BE temporal unit | Не запускался | Нет лога | Не аттестован |
| P10BE production polar `--selftest` | Не запускался | Нет лога | Не аттестован |

P10V stdout также содержит `residual_rel=5.4808975582e-09`, `history_rel=3.0865923249e-07`, `functional_rel=3.3692518365e-06`, 6 models, 4 functionals, 27 quadrature points; совпадает с P10BP по SHA-256 P10V stdout. P10Y запускает P10V внутри себя и затем печатает дополнительную строку `...OK models=6... bins=2`.

## Диагноз R2 и исправление R3

R2 проверял точное равенство строки `$_.Trim() -ceq $markers[$i]`, что подходит для P10V, но **не подходит к штатному выводу P10Y/P10BE с диагностическими полями**. Таким образом `RESULT=P10BQ_STOPPED: Expected one exact marker not found: P10Y_ANALYTIC_SHELL_UNIT_OK` — **ложная остановка в оболочке**, не отказ P10Y. Exit `0` и маркер с суффиксом подтверждены из независимого приложенного лога.

В **P10BQ R3** допускается маркер в начале строки, после которого только конец строки или пробельный разделитель (`^<marker>(?:\s|$)`); контрольный токен по-прежнему не засчитывается как подстрока и требует ровно одного совпадения. Все остальные охранные проверки и прямое чтение `$LASTEXITCODE` сохраняются. **R3 ещё не запускался на Windows.**

**Действующий следующий один-клик архив:** `tools/P10BQ_FOUR_TEST_RECOVERY_ONECLICK_R3_20261119.zip`. Не перезапускать R1/R2 или сборку P10BP, не удалять старые папки и не выполнять FEM. Следующий пользовательский файл — один `P10BQ_EVIDENCE.zip` из новой папки R3. Принятые 2/4 теста не являются доказательством полной геометрической пространственно-временной сходимости и не устанавливают исторический build SHA P10BE_H2.
