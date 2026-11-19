# P10BQ R3 Windows — четыре новых unit/selftest из exact Git SHA успешно прошли

19.11.2026, 20:32:12 +05:00. **Итог: `RESULT=P10BQ_FOUR_FRESH_WINDOWS_TESTS_OK`, `TESTS_PASSED=4/4`; получено подтверждение новой чистой Windows сборки и всех четырёх коротких тестов из exact исходного коммита `90fd2559c0224ac0a7d2dbe2fe081a6a319080e4`.** Это инженерная, не научная аттестация пространственной сходимости.

## Первичные файлы

- Исследователь предоставил **оригинал** `P10BQ_EVIDENCE(2).zip`, зарегистрирован побайтно с именем `input/P10BQ_R3_EVIDENCE.zip`: **2990 байт**, SHA-256 `86adb577b2b4694a540538e8ed156f62c34683411b527f7a7d98a1df633e5175`.
- Отдельно приложенный **оригинал** `P10BQ_RESULT(2).txt`, зарегистрирован побайтно как `input/P10BQ_R3_RESULT.txt`: **2690 байт**, SHA-256 `d359c3c1be8022bea67a318fefc880339c89ea81b0beb865bd4aaedb4ccba5c6`.
- `unzip -t`: **5/5 членов OK**. ZIP содержит ровно `P10BQ_RESULT.txt` и четыре `*_combined.txt` с общей несжатой длиной **4418 байт**. Извлечённый `P10BQ_RESULT.txt` **побайтно совпал** с отдельно присланным. SHA-256 каждого из четырёх журналов независимым чтением ZIP совпадает со значением `TEST_LOG_SHA256_...` из отчёта.

## Конфигурация, состояние дерева и связь с сборкой

- `TOOL_REVISION=P10BQ_R3_MARKER_PREFIX_WITH_FIELDS_FIX`, `CONFIRMATION=TEST P10BQ`, `P10BP_REQUIRED_REPORT_LINES_VERIFIED=5/5`.
- `REUSED_P10BP_ROOT=G:\ildar\P10BP_ATTEST_20261119_173658_19404`, оригинальный P10BP отчёт SHA-256 `74ecdccec83e04c89e47ca8451380a2eb5923b1125c9721365b32b168219450a` (совпадает с архивом P10BP).
- `P10BP_CACHE_VERIFIED=MinGW Makefiles;Release;GNU13.1.0_EXPECTED_PATH;OPENMP_ON`; изолированный `source` clean **до и после** тестов, SHA `90fd2559c0224ac0a7d2dbe2fe081a6a319080e4`.
- Пользовательское исходное `G:\ildar\Stage3D07`: HEAD `90fd2559...`, Git-статус `0/7/4` **до и после**; `ORIGINAL_STATE_PRESERVED=YES_BY_READ_ONLY_CHECK`. Изменения рабочего дерева не очищались, оригинальная JOM/Qt Creator сборка не заменялась.
- Новая сборка P10BP `CONFIGURE_EXIT=0`, `BUILD_EXIT=0` и четыре финальные строки `Built target` подтверждены отдельно первичными журналами P10BP. P10BQ только повторно использует её EXE, без clone/build/FEM.

| Windows цель из новой сборки | SHA-256 EXE | Нативный exit | Маркер в первичном журнале |
|---|---|---:|---|
| `stage3d10v_analytic_shape_unit.exe` | `02f14785ebc5dbe841dbec8b836b163858ff0bcbe311a53eec3dc24bb1da4721` | 0 | `P10V_ANALYTIC_SHAPE_UNIT_OK` |
| `stage3d10y_analytic_shell_unit.exe` | `15abab353994b0353c0783d8d53dc812e0bc970b3042e04e8e2ed40848afda54` | 0 | `P10Y_ANALYTIC_SHELL_UNIT_OK models=6 functionals=4 bins=2` |
| `stage3d10be_temporal_unit.exe` | `4b7513affe02bc2b402edb7343923d5b10add4026b89aaa25ee84d4cd1340e72` | 0 | `P10BE_TEMPORAL_UNIT_OK schedules=4 dt25_steps=36 polar_rows=7200 audit_rows=72 ...` |
| `stage3d10be_temporal_polar_audit.exe --selftest` | `18593652a27bcce7b8286053460421ce6594506f8254cfffb8b52db48e25f363` | 0 | `P10BE_TEMPORAL_BINS_SELFTEST_OK allowed_dt=25 steps=36 horizon_s=900` |

SHA-256 первичных logs:

| Target prefix | SHA-256 `*_combined.txt` |
|---|---|
| `stage3d10v_analytic_shape_unit` | `2ffd91d356cf521e8d779143ed34a000a0d49878699fe5b7cc2eb7ea71ed403d` |
| `stage3d10y_analytic_shell_unit` | `d82253879caaccc47037f2bf6760d43432f8b090564a6570211d5a9720406adc` |
| `stage3d10be_temporal_unit` | `9a59f23282ba9d8f0024ef5b4fd409a435529fc18f1e63479e9c48ecca10825b` |
| `stage3d10be_temporal_polar_audit` | `c8014c2c6b15666d201133e2ef1583457842b705cceaa746cf5b496901ec47cd` |

**Существенные диагностические строки:** P10V `residual_rel=5.4808975582e-09`, `history_rel=3.0865923249e-07`, `functional_rel=3.3692518365e-06`; P10BE unit `dt25_steps=36`, `polar_rows=7200`, `audit_rows=72`; production `P10I_PRODUCTION_ADJOINT_OK` с 18 cases, 216 replayed steps и FD-контролем (точные числа в ZIP). `P10W_DEPENDENCY_SELFTEST_OK analytic_coupling_verified=0` сохраняет самостоятельное ограничение проверки зависимости — не подменять этим полный аналитический gradient proof.

## Что именно доказано, а что не доказано

**Подтверждено:** опубликованный точный исторический коммит исходников P10BI → чистый отдельный GitHub clone P10BP → GNU13.1 `MinGW Makefiles` Release build четырёх целей с кодом 0 → SHA-256 новых EXE → исполнение четырёх коротких unit/selftest с exit 0 и маркерами. P10BN/P10BO/P10BP/P10BQ R1/R2/R3 **не требуется повторять**.

**Не доказано:** что исторический тяжёлый `P10BE_H2_LOGS_20261118_182525` был исполнен именно этими EXE (его оригинальный SHA/Build source остаются задокументированными отдельно); что пространственная/временная сходимость полной `D_R jpeak` установлена; что старые 103 предупреждения компилятора качественно аудированы; что реология или физический критерий прочности валидированы. Unit `OK` не является сеточной сходимостью. Следующий этап — научный P10BR: независимое нормированное сравнение радиально-полярных распределений **разных видов** локальных изменений из уже опубликованных первичных P10BB/P10BE CSV без нового FEM, с оговоркой об их различной физической природе.
