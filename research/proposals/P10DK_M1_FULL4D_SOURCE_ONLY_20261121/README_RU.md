# P10DK R1 — только исходники программы полной физической 4D-диагностики принятой M1

**ЭТАП ПОДГОТОВКИ. Ни одной физической попытки M1 не разрешено и не запускается.**

## Что включено

Это автономный ZIP C++20/MinGW/OpenMP со стабильными исходниками уже проверенной P10DD механической и тепловой формы, новым target `stage3d10dk_m1_full4d`, unit `p10dk_4d_synthetic_unit` и независимым `P10DK_audit_evidence.py`, который ожидает **9736 Tet10 M1**, а не прежние 7388 H0. Механическая форма — analytic Tet10, 27QP, signed explicit/equilibrium/history; тепловая — 64QP mass/diffusion и отдельная top-Robin boundary. Глобальное/временное/компонентное замыкание обязательно.

Принятая D-019 M1.msh живёт **только на компьютере исследователя**; никакая сетка или forward cache не включены в ZIP. SHA M1 по Windows manifest:
`ca6b6b6588dc72c5dd3ed2e92e24794560ee2407e350c8a44858e9c3c7d0360f`.

## Безопасный Windows этап

1. Распаковать ZIP в **новый** каталог вне `G:\ildar\Stage3D07` и вне старых P10DD/P10DG папок, например `G:\Downloads\P10DK_R1_M1_FULL4D_SOURCE_ONLY_20261121`.
2. Дважды щёлкнуть `01_P10DK_CHECK_SOURCE_ONLY.cmd`. Программа только проверяет контрольные суммы всех источников, исходные защитные блокировки и Python synthetic closure; ожидается `P10DK_SOURCE_ONLY_OK`. **Не запускает Gmsh, EXE и физическую задачу.**
3. Открыть `CMakeLists.txt` **этой** папки в Qt Creator, выбрать прежний `Desktop Qt MinGW 64-bit Release`. Собрать targets `p10dk_4d_synthetic_unit` и `stage3d10dk_m1_full4d`.
4. В Qt Creator безопасно запустить **только** `p10dk_4d_synthetic_unit.exe` и `stage3d10dk_m1_full4d.exe --selftest` (в его Run Configuration/Command line arguments). Также доступен `--help`. Запуск без `--selftest`/`--help` намеренно заканчивается `P10DK_SOURCE_ONLY_STOP_NO_FEM` с кодом 2. Даже переключение CMake `P10DK_ENABLE_PHYSICAL=ON` в этом R1 вызывает немедленный configure STOP.

**В этом R1 НЕТ кнопки физического расчёта**, и сам собранный EXE отказывается его начинать. Пользователю не нужно вводить SHA, подменять старые кэши или запускать PowerShell/Git.

## Что будет на следующем этапе только после согласования

Отдельно, **без повторного Gmsh**, подготовить bounded Windows R2 runner: проверить точный SHA указанного выше `P10DG_M1_CANDIDATE.msh`, EXE, source fingerprint, свободные RAM/диск, one-shot marker и время; создать новый `M1 forward_history.bin`, затем adjoint на **той же M1**, и сохранить 7206 4D CSV строк + глобальное/пошаговое замыкание. **Нельзя использовать H0 forward_history.bin**. Проверяемый `--reuse-forward` должен запрещаться в первом физическом M1, чтобы не смешивать истории разных сеток. Компьютер i7-7700K/64 GiB, M1 9736 Tet10 (+31.8% от H0); ориентир для планирования нового forward+adjoint **3–15 минут и ~1–4 GiB**, **не измерение**. Для будущей разрешённой попытки предлагаемый жёсткий STOP — **1800 с wall, 8 GiB private, 1 GiB выход, ≥4 GiB диск**, окончательно устанавливать после дополнительных тестов.

Действуют D-017, D-018D и D-019: M0=точная H0, M1=SHA ca6b6b... без индикаторов, полное signed локальное разложение `(r,theta,phi,t)`; адаптация M2 только после физических M0 и M1. Все старые H0/P10DD H0 forward cache/данные и P10DG marker сохраняются нетронутыми.
