# P10CB R1 — автономная безрасчётная проверка захвата нативного ExitCode на Windows

**20.11.2026. Статус:** `P10CB_R1_SAFE_EXITCODE_KIT_PREPARED_LINUX_STATIC_ONLY`, Windows native test **PENDING**. Никакого FEM в этом этапе не запускалось; D-015 уже исчерпано предыдущим P10CA H0.

## Зачем нужен этот этап

В единственной физической попытке P10CA R1 были записаны корректные реальные H0 CSV, `P10W_ANALYTIC_ADJOINT_OK` и `P10BX_THERMAL_QP_INTEGRATED_OK`. Независимые числовые проверки прошли. Однако PowerShell 5.1 R1 вызывает физический процесс через `Start-Process -PassThru` и после `WaitForExit()` обнаружил **`$proc.ExitCode=$null`**. Исходный `RESULT=P10CA_STOPPED` и `physical_verified=false` сохраняются; нельзя ретроспективно утверждать native exit0 и нельзя ради этого повторять FEM.

**Один узкий технический вопрос:** может ли на имеющемся Windows получить формальный код выхода **короткого** нативного процесса ограниченный `.NET System.Diagnostics.Process` с `WaitForExit(timeout)`, отдельным чтением обоих каналов и `ExitCode` до `Dispose()`, сверенный с доверенным прямым вызовом `$LASTEXITCODE`? Никакого переноса этого свойства на старый уже завершившийся H0 автоматически нет.

## Автономный One Click и происхождение

- `tools/P10CB_EXITCODE_SELFTEST_R1_20261120.zip`: **6986 байт, SHA-256 `b23c1d2e3da5d00b2e901d094248b0f5cff35d7de1a358424c7f82b27252ca9d`**, 3 исходных файла плюс папка, ZIP integrity PASS 4/4 entries.
- `P10CB_Test_ExitCode.ps1`: CRLF, ASCII без BOM, SHA-256 `15ff29ac2322713ba01294d1e2fb7c88155099753947fc8b1cdbc103e3fcf7b8`; `01_P10CB_SAFE_EXITCODE_TEST.cmd`: CRLF, без BOM, `README_RU.md`: русский порядок. Сценарий добавляет фактический хеш своего PS1 в выходной `P10CB_RESULT.txt` для последующей независимой сверки.
- Привязка **к существующему** Windows P10CA EXE из единственной физической попытки: `G:\Downloads\P10CA_H0_ONE_RUN_R1_20261120\P10CA_RESULTS_20261120_151200_8420\build\p10ca_h0_analytic_qp.exe`, exact SHA-256 `17c31f426245317271245e340d68fa5de1e4eb144b7be986167505e14cbed924`. EXE не копируется/не собирается, при отсутствии или расхождении SHA — STOP.
- Read-only исходный Windows `G:\ildar\Stage3D07` HEAD `90fd2559c0224ac0a7d2dbe2fe081a6a319080e4`; status counts/fingerprint читаются до и после, никогда не изменяются программой.

## Точный перечень разрешённых нативных процессов

1. `.NET Process` → `cmd.exe /d /c exit 7`; обязательный native code **7**, таймаут 10s.
2. Прямой `& cmd.exe /d /c exit 7`, немедленный `$LASTEXITCODE`; обязательный **7**.
3. Исторический `Start-Process -Wait -PassThru` → **только** тот же синтетический `cmd.exe exit 7`; записать наблюдённый код либо `NULL`, его значение **не** используется в качестве критерия успеха новой схемы.
4. Пинованный P10CA EXE `.NET Process` → **только** `--help`, exit0, таймаут 20s и точный контракт W без FD.
5. Тот же EXE `.NET Process` → **только** `--selftest`, exit0, таймаут 60s; маркеры `P10I_PRODUCTION_ADJOINT_OK models=6 functionals=3 cases=18`, `P10W_DEPENDENCY_SELFTEST_OK analytic_coupling_verified=0`.

**Запрещено в коде:** `--mesh`, `--out`, `--preflight`, `--steps`, H0/H1/H2 solve, запуск Qt/CMake, Git checkout/reset/clean/push, изменение прежнего физического исходного каталога. Отсутствуют FEM input mesh/EXE в новом ZIP. В новой папке создаются только короткие файлы отчётов и один `P10CB_EVIDENCE.zip` с result и несколькими stdout/stderr. Два метода exit7 проверяются независимо; отсутствующий код у исторического `Start-Process` помечается как диагностическое наблюдение, не исправляется задним числом.

## Проверка перед публикацией и её пределы

Независимый Linux static audit: скрипт ASCII, полные пары скобок `{}`, `[]`, `()`, нет physical CLI options в исполняемых путях; ZIP 4/4 integrity PASS; CRLF CMD/PS1; exact P10CA source-sha contract встроен. Имеющийся Linux P10CA бинарник выполнил **только** `--selftest` exit0 с P10I/P10W маркерами. **Здесь нет PowerShell 5.1 и Windows API:** PS syntax/Windows native exit capture реально **не аттестованы**, это задача одной короткой кнопки на ПК исследователя.

**Следующее действие исследователя:** распаковать ZIP в новый каталог вне исходного G: дерева, запустить `01_P10CB_SAFE_EXITCODE_TEST.cmd`, вернуть **ровно один `P10CB_EVIDENCE.zip`** или сообщить STOP. Оценка 5–30s (низкая уверенность), Windows `.NET` selftest timeout 60s, очень небольшие RAM/disk; никакого FEM, а значит не требуется новая физическая санкция. Если EXE перенесён — не пересобирать: прислать STOP, уточнить путь отдельно.

**Научные ограничения:** результат даже `P10CB_NATIVE_EXITCODE_SELFTEST_OK_NO_FEM` только докажет исправное считывание кода **нового короткого теста**. P10CA прежний native exit0 остаётся UNKNOWN, QP/CSR numeric PASS остаётся действительным. `SPATIAL_CONVERGENCE_NOT_PROVEN`, временная сходимость полной `D_R jpeak` не доказана, P10BE historical EXE SHA UNKNOWN. Для нового H0/H1/H2 требуется отдельное согласованное решение.
