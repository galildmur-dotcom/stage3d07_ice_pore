# P10CB: Windows R1 safe STOP на отсутствующей DLL; R2 воспроизводит PATH физического P10CA без FEM

**20.11.2026.** Статус: `P10CB_R1_WINDOWS_NATIVE_SYNTHETIC_3x7_PASS_HELP_DLL_STOP`; новый `P10CB_R2_RUNTIME_PATH_REPAIR_PREPARED_WINDOWS_PENDING`. **Физических FEM вызовов нет ни в R1, ни в R2.** P10CA original physical EXIT remains UNKNOWN, а его real H0 QP/CSR numeric PASS неизменен.

## 1. Первичный Windows R1 evidence и независимое чтение

Получен пользовательский `P10CB_EVIDENCE.zip`: **822 B**, SHA-256 **`57b654c9eb194dcb0a1b161266d0e082848927c24bb175150c64eda21c83aee9`**, ZIP integrity **2/2 PASS**. Содержит исходные `P10CB_RESULT.txt` (1034 B) и `exe_dotnet_help_stdout.txt` (2 B, фактически без полезного вывода). R1 PS1 SHA из журнала `15ff29ac2322713ba01294d1e2fb7c88155099753947fc8b1cdbc103e3fcf7b8` **совпадает с опубликованным R1 ZIP**, `TOOL_REVISION=P10CB_R1_NATIVE_EXITCODE_SAFE_ONLY`.

Исходный Windows HEAD `90fd2559c0224ac0a7d2dbe2fe081a6a319080e4`, статус `0/7/4`, fingerprint `bb376579544e328291674fa91d20c7b8a4b9d4a306fd7a3af47c172cedb75258` **до/после идентичны**. Из существующего P10CA physical build в отдельной папке прочитан SHA EXE `17c31f426245317271245e340d68fa5de1e4eb144b7be986167505e14cbed924`, который совпал с физическим P10CA manifest (EXE не был скопирован и не изменился). `INPUT_GATE=PASS_READ_ONLY`.

**Результаты контролируемых коротких процессов:**

| Наблюдение | Реально сообщённый native exit | Статус |
|---|---:|---|
| `.NET Process` для `cmd.exe /d /c exit 7` | **7** | PASS |
| Прямой `cmd.exe` с немедленным `$LASTEXITCODE` | **7** | PASS |
| Исторический `Start-Process -Wait -PassThru` на том же `cmd.exe exit 7` | **7** | PASS в синтетическом примере |
| Exact P10CA physical EXE с `--help` под `.NET Process` | **−1073741515** = **`0xC0000135`** | **STOP**, Windows loader status `STATUS_DLL_NOT_FOUND` |
| Exact P10CA EXE `--selftest` | НЕ запускался | PENDING после STOP |

R1 сохранил `STOP_REASON=P10CB_STOP: safe --help failed`, `RESULT=P10CB_STOPPED_NO_FEM`, `PHYSICAL_FEM_RUNS=0`; дальнейшие тесты не исполнялись. **Физическая задача не стартовала.** Синтетический `Start-Process` сработал в этом коротком случае, следовательно, из данного опыта нельзя выводить универсальную неисправность `Start-Process`; конкретный исторический P10CA process ExitCode остаётся неизвестным.

## 2. Причина и минимальная изолированная правка R2

**Подтверждённое наблюдение:** код Windows `0xC0000135` у короткого P10CA `--help`, пустой stdout. **Диагноз:** не найдена одна из зависимых DLL при запуске под новым процессным окружением. Конкретное имя DLL отсутствует в evidence, поэтому оно **UNKNOWN**; ошибочно утверждать, что доказана неисправность конкретной библиотеки.

**Проверенное расхождение запуска:** исходный ранее физически работавший `P10CA_Run_One_H0.ps1` временно добавлял `C:\mingw64\bin` в **дочернее унаследованное** окружение процесса (`$env:PATH = 'C:\mingw64\bin;' + $env:PATH`) и затем восстанавливал `$env:PATH`. Безопасный P10CB R1 при использовании `System.Diagnostics.ProcessStartInfo` вообще не устанавливал этот префикс. Такой путь является наиболее вероятной причиной отсутствия DLL, но достаточность исправления должна быть проверена новым Windows свидетельством.

**R2 минимальный diff:** в новой отдельной версии `P10CB_Test_ExitCode.ps1` перед `Process.Start()` установить **только** для дочернего процесса `$psi.EnvironmentVariables['PATH'] = 'C:\mingw64\bin;' + $env:PATH`; до теста проверить точный каталог MinGW и `g++.exe` (без запуска компиляции). Исходная PowerShell-среда, системная переменная PATH, P10CA original dirty project и existing EXE **не изменяются**. Строгая проверка `$null` до преобразования `ExitCode` в число сохранена, как и таймаут 20s для `--help`, 60s для `--selftest`.

R2 исполняет **только** synthetic `cmd.exe exit 7`, diagnostic historical Start-Process на `cmd.exe exit 7`, `--help` и `--selftest` **точно того же** P10CA EXE SHA. Нет `--mesh`, `--out`, `--steps`, `--preflight`, нового H0/H1/H2 solve, CMake или Git mutation. Сценарий создаёт новый компактный results folder и один `P10CB_EVIDENCE.zip`; результат `P10CB_R2_NATIVE_EXITCODE_SELFTEST_OK_NO_FEM` допустим **лишь после** проверенного Windows native evidence, не сейчас.

## 3. Аттестация R2 до передачи исследователю

- Новый пакет **`tools/P10CB_EXITCODE_SELFTEST_R2_20261120.zip`**: **7534 B**, SHA-256 **`438a622f46b280c6900c115db0bb06daa77bac8eb1ac8ed28e2896d3b9250c2f`**, ZIP integrity **4/4 PASS**, новый отдельный каталог без перезаписи R1.
- `P10CB_Test_ExitCode.ps1` R2: SHA-256 **`dd628ceb52adb82ff3f8bb317c3a73943984a9cc5848e95d21192dff2838b563`**, ASCII/CRLF без BOM; контролируемая правка префикса для дочернего PATH, `TOOL_REVISION=P10CB_R2_NATIVE_EXITCODE_MIN_GW_CHILD_PATH_FIX_NO_FEM`. Старые R1 исходники не изменены.
- Linux/статическая проверка: только безопасные варианты `--help` и `--selftest`, два специальных synthetic exit7, нет нативного физического FEM; ZIP CRC PASS. Нет локального Windows PowerShell 5.1, поэтому синтаксическое/платформенное исполнение R2 и восстановление DLL **ещё PENDING**.

**Следующий один безопасный шаг:** исследователь распаковывает **R2 ZIP** в новый каталог вне `G:\ildar\Stage3D07`, дважды щёлкает `01_P10CB_SAFE_EXITCODE_TEST.cmd` и передаёт **один новый `P10CB_EVIDENCE.zip`**, либо STOP. Предварительная оценка времени 5–30 s, для самого selftest таймаут 60 s, существенные RAM/disk не потребуются. Ни одна физическая попытка D-015 не возобновляется.

**Неподтверждённое остаётся:** OS native exit0 исторического P10CA H0 неизвестен, spatial convergence не доказана, full `D_R jpeak` time convergence не доказана, исторический P10BE_H2 EXE SHA UNKNOWN.
