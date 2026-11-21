# P10CB R2 — Windows: надёжный захват ExitCode подтверждён на безопасном EXE selftest

**20.11.2026. Итог:** `P10CB_NATIVE_EXITCODE_SELFTEST_OK_NO_FEM`; инженерный P10CB **CLOSED_SAFE_ONLY**. Это не повтор физического H0 и не новое научное измерение чувствительности формы.

## 1. Первичные Windows файлы и контроль версий

Исследователь передал `P10CB_EVIDENCE(1).zip`: **1661 байт**, SHA-256 **`132a3852bacfd9d9cbdedf33f56f3d025edcd1a228f2a0121bbaf356afc172ec`**, архив целостен **4/4**. В нём `P10CB_RESULT.txt` (1077 B), `exe_dotnet_help_stdout.txt` (284 B), `exe_dotnet_selftest_stdout.txt` (489 B), `exe_dotnet_selftest_stderr.txt` (2 B — пустой содержательный stderr). Архив не содержит EXE, mesh, BIN, checkpoint или FEM CSV.

Точная редакция сценария: `TOOL_REVISION=P10CB_R2_NATIVE_EXITCODE_MIN_GW_CHILD_PATH_FIX_NO_FEM`, записанный скриптом SHA-256 **`dd628ceb52adb82ff3f8bb317c3a73943984a9cc5848e95d21192dff2838b563`** совпал с заранее опубликованным R2 PS1. Значит, событие относится к исправленной версии, а не к R1.

Оригинальный Windows Git до и после: HEAD **`90fd2559c0224ac0a7d2dbe2fe081a6a319080e4`**, dirty counts **`0/7/4`**, fingerprint **`bb376579544e328291674fa91d20c7b8a4b9d4a306fd7a3af47c172cedb75258`**, совпали побайтово. Source tree и existing physical output не изменялись. Read-only SHA **того же** ранее физически собранного P10CA Windows EXE — **`17c31f426245317271245e340d68fa5de1e4eb144b7be986167505e14cbed924`**. Именно этот объект использовался для safe --help и --selftest; EXE в evidence не включён.

## 2. Непосредственно наблюдаемые native exit и stdout

| Случай | Native exit | Результат |
|---|---:|---|
| `.NET Process` + синтетический `cmd.exe /d /c exit 7` | **7** | PASS |
| Прямой `cmd.exe` + немедленный `$LASTEXITCODE` | **7** | PASS |
| Исторический `Start-Process -Wait -PassThru` + `cmd.exe exit 7` | **7** | PASS только для синтетического короткого процесса |
| Тот же P10CA EXE с `--help`, ограниченный `.NET Process` | **0** | PASS, правильный analytic Tet10 CLI |
| Тот же P10CA EXE с `--selftest`, ограниченный `.NET Process` | **0** | PASS, точные P10I/P10W markers |

`--selftest` stdout содержит `P10I_PRODUCTION_ADJOINT_OK models=6 functionals=3 cases=18 ... adjoint_equilibrium_rel=5.410927883335e-13` и `P10W_DEPENDENCY_SELFTEST_OK analytic_coupling_verified=0`. `--help` подтверждает аналитическую геометрическую производную без `--delta-scan-um`. **Важное ограничение:** `analytic_coupling_verified=0` в этом selftest означает, что он проверяет зависимый adjoint/unit контур, а не новую независимую физическую производную; реальный P10CA H0 был проанализирован отдельно по своим CSV.

Значение `CHILD_PATH_PREFIX=C:\mingw64\bin`, `INPUT_GATE=PASS_READ_ONLY`. В отличие от R1, Windows загрузчик смог запустить безопасный код P10CA и вернуть настоящий **0**, что поддерживает диагноз о ранее отсутствовавшей DLL в окружении дочернего процесса. Название конкретной DLL по-прежнему **UNKNOWN**, диагностический тест её не перечисляет. Интервал между START и FINISH: около **4.25 s**. Итог `RESULT=P10CB_NATIVE_EXITCODE_SELFTEST_OK_NO_FEM`, `PHYSICAL_FEM_RUNS=0`.

## 3. Что исправлено, а что не следует ретроспективно исправлять

Для **нового** дочернего процесса обоснован следующий технический контракт: прямой `.NET Process` с `UseShellExecute=false`, асинхронным чтением stdout/stderr, ограниченным `WaitForExit(timeout)`, явной проверкой `ExitCode` на null до преобразования в int и чтением ExitCode **до** Dispose. Для MinGW EXE — child-only `PATH` с префиксом `C:\mingw64\bin`; global/host PATH не меняется. Синтетический ненулевой код 7 и реальный короткий exit0 теперь подтверждены на Windows.

Но **старый** `P10CA_RESULT.txt` правильно остаётся `P10CA_STOPPED` из-за пустого `Start-Process.ExitCode` после прошлого long-running H0. Тест P10CB R2 не может получить значение возврата уже завершившегося процесса; **P10CA H0 historical native exit0 остаётся UNKNOWN**. При этом independently verified P10CA H0 numeric thermal QP/CSR parity и его реальные производные остаются без изменений. Не смешивать инженерную исправность будущего capture и историю прежней физики.

**Никакой повторной физической попытки P10CA, нового H0/H1/H2, `--preflight` или истории не выполнялось.** D-015 (один H0) уже израсходовано, новая физика требует отдельного решения. `SPATIAL_CONVERGENCE_NOT_PROVEN`, полная временная сходимость `D_R jpeak` не доказана, исторический P10BE_H2 EXE SHA UNKNOWN.

## 4. Научное продолжение после закрытия P10CB

Текущий инженерный блокер захвата нативного кода выхода для **новых** тестов снят. Следующий шаг без физического запуска: определить минимальный проект сопоставления **полной** аналитической производной `D_R jpeak` на H0 и ближайшей согласованной H1 с одинаковыми `EDV_VAR, ξ=0, R, steps=6, dt=150s, B6 cutoff=5mm`, используя одну и ту же сетку внутри каждого прямого/сопряжённого расчёта (P10AO), сохраняя thermal radial/polar CSV. До отдельного разрешения H1 **не запускать**. Прежде получить ресурсную оценку, критерии пространственных/временных ошибок и сравнения полного mechanical+thermal, не выдавать QP/CSR parity за сходимость.

**Исходный evidence:** `research/evidence/P10CB_R2_WINDOWS_VERIFIED_20261120/input/P10CB_EVIDENCE.zip` плюс исходные текстовые журналы. **Derived:** `research/evidence/P10CB_R2_WINDOWS_VERIFIED_20261120/derived/P10CB_R2_AUDIT.txt`.
