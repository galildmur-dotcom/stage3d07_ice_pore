# P10CX R1 — исходный Windows STOP и новая R2 без повтора R1

21.11.2026. D-018A: геометрический mesh-only этап. Объёмный Tet10 и FEM по-прежнему не разрешены.

## 1. Оригинал R1 и уровень доказательства

- Пользователь передал оригинальный `P10CX_EVIDENCE.zip`, SHA-256 `bf3148f065cff01af6e602955e41fad94b90d52021fdbc05ff1cc9f61931bb1d`, ZIP CRC **1/1 PASS**. Единственный член `P10CX_RESULT.txt`, 711 байт, с UTF-8 BOM, CRLF; оригинал сохранён *без модификаций* в `research/evidence/P10CX_R1_WINDOWS_VERSION_STOP_20261121/input/`.
- Точный tool revision `P10CX_R1_GMSH4152_SURFACE_ONLY_ONE_SHOT`; source SHA gates 3/3 PASS: GEO `85ee63351ff8e7c1b7720f8ba360aac1d4e6c381f776e3fa66f130e73f17aca7`, OCC include `8029a6ed22bcf312701cd6abc46bbe5575e52df16fd5218dd936b01d5cd6fcf0`, Python QA `165d59ff1b05f45478008c6498a0b5ddfde19ca4538816439a3a530f70cc0f50`.
- `GMSH_EXE_SHA256=317c43391e5b1fab3a1dd80dc5245dad6e2d087910f4b8ebc234bd6d4b8f41a1`, но фактическое содержимое stdout/stderr `gmsh.exe -version` в R1 **не сохранено**. Следующая строка `STOP_REASON=STOP: Gmsh -version native exit ` содержит пустое значение после `exit`.
- В R1 `$versionText = @(& $gmsh -version 2>&1) -join ...` и затем `$LASTEXITCODE`. Пустое значение указывает на **неаттестованную передачу native exit в данном контексте PowerShell**, но не доказывает сбой/несовместимость Gmsh.exe. Прямого измерения причины нет.
- `GMSH_STARTED=YES`, `PYTHON_UNIT_EXIT`, `RAM_DISK_PREFLIGHT` и MSH SHA в оригинале отсутствуют: **реальная 2D-сетка НЕ была создана, никаких 120-cell результатов Gmsh4.15.2 нет**, Gmsh не вызывался для `-2`. Историческая 4.13.1 P10CW qmin0.074748 остаётся единственным реальным результатом поверхности.

## 2. Отличие R2: проверяемая новая гипотеза

**Новый минимальный различающий тест:** является ли R1 STOP следствием способа извлечения `$LASTEXITCODE` при рабочей версии `gmsh.exe -version` или действительно Gmsh.exe не запускается/имеет другую версию?

- R2 вызывает `gmsh.exe -version` через `System.Diagnostics.Process` с `UseShellExecute=false`, `RedirectStandardOutput/RedirectStandardError`, `ReadToEndAsync`, `WaitForExit(15000)` и **типизированным** `ExitCode`. Оба потока сохраняются в отдельные файлы при штатном завершении. При тайм-ауте — STOP, не переходить к сетке.
- **Тот же** SHA EXE, проверенный в R1, жёстко закреплён; исходники GEO/include/QA все три SHA закреплены. Новые `TOOL_REVISION`, `P10CX_R2_RUNS`, новая уникальная кнопка. Старый R1 ZIP/источник не перезаписывать.
- Если R2 version native exit0 и версия4.15.2 подтверждена, выполнить **один** 2D-only `-2 -nt 2` с прежними лимитами 180с/2ГиБ private/150МиБ ASCII MSH2 и stdlib QA: угол120 bins, PORE_WALL Tri6, худший sliver. Никакого FEM, 3D, Qt/Git действий.
- Если версия или дальнейший контроль STOP — сохранить оригинальные `P10CX_R2_VERSION_STDOUT/STDERR.txt`, `P10CX_RESULT.txt` и компактный ZIP; не повторять R2 вслепую.

## 3. Проверка подготовки R2

- `research/packages/P10CX_R2_VERSION_GATE_SURFACE_GMSH4152_WINDOWS_20261121.zip` SHA-256 `8098a39ed1fb98dceb205afdba810ab78935258540b1586a08d95913a63a46e3`, ZIP CRC **6/6 PASS**, `01_RUN_P10CX_R2_SURFACE_ONLY.cmd` CRLF в пакете.
- Анализатор **из R2 ZIP** `--selftest` exit0; разбор прежней реальной P10CW MSH2 Linux4.13.1 также воспроизвёл 74592 Tri6, qmin0.0747478437 и 120 угловых ячеек (это replay, не новое Windows измерение). Сценарий PowerShell 5.1 и Gmsh4.15.2 в среде ассистента **не запускались**.

## 4. Следующее действие

**R1 = STOP_BEFORE_MESH; R2 = PREPARED_WINDOWS_PENDING, NOT GEOMETRY_PASSED.** Исследователь распаковывает R2 в новую папку вне Git-проекта, однократно запускает новый CMD и передаёт **только `P10CX_R2_EVIDENCE.zip` или STOP**. Большая `.msh` остаётся на Windows. Исходный полярный механический вопрос пока UNKNOWN; новый 3D Tet10/FEM не разрешён.
