# P10DW R1 — геометрический preflight + один будущий 1D runtime точного M2 F6, SOURCE-ONLY

**21.11.2026. Фактически выполнено:** создан и изолированно проверен *инструмент* P10DW; **настоящий native Gmsh4.15.2 не запускался**, 1D/2D/3D meshing=0, M2 Tet10/curved27QP=0, physical forward/adjoint/FEM=0. Старые Windows markers P10DO/P10DQ/P10DR/P10DT и оригинальные M1/H0 не читались и не изменялись. История и source provenance сохранены в исследованиях P10DU/P10DV.

## 1. Уже установлено / осталось неизвестным / новый различающий опыт

**Доказано ранее:** P10DU проверил байтово оригинальный Windows `P10DT_EVIDENCE.zip` SHA256 `9c4602ac29a08dd8faa5e977990a3f138f73a39c242dcc3167b09f23bf46d414`: простой прямой F6 и пространственный inline F6 прошли `gmsh -1` за ~0.21с, вложенный F6→F3 MathEval остановлен за15.066с. Проверка source Gmsh4.15.2 `Field.cpp` обнаружила нерекурсивную секцию MathEval. P10DV выполнил буквальную полную подстановку F3/F4/F5 в F6, сохранив C¹ κ∈[0,1], `Vtarget_M2/Vtarget_M1=1−0.20κ`, `h2/h1=(1−0.20κ)^(1/3)`, original M1 SHA `ca6b6b6588dc72c5dd3ed2e92e24794560ee2407e350c8a44858e9c3c7d0360f` (9736 Tet10); 51 225 mathematical comparisons max normalized difference0.0. Кандидатная `P10DV_M2_INLINE_FIELD20.geo` SHA256 `32f8f959002cbd41539e355a80437c2ca3be12fdd3ba12de31eadf2c021b9561`, CAD SHA `8029a6ed22bcf312701cd6abc46bbe5575e52df16fd5218dd936b01d5cd6fcf0`; ZIP P10DV SHA256 `4c29c4a4d2fbe6ea537bc4103b1dc5f42112e68e85cc98a14dd7dce1cac2c571`.

**Неизвестно:** нативный разбор и оценка *полного 494-символьного* MathEval F6, поскольку P10DT C проверял только короткий spatial clamp; нет M2 3D mesh QA/27QP/фактических 9-зонных объёмов или новых производных формы.

**Новый единичный тест:** (A) read-only native Gmsh4.15.2 `-parse_and_exit` исходного `Background Field=2` и точного F6; (B) только после A-PASS и отдельного согласия исследователя — один `gmsh -1` на том же точном F6. Для A/B не требуется создавать или изменять M1. Exact SHA читается только из оригинальной `P10DG_M1_CANDIDATE.msh` на Windows. Поле M2 не заменяется константой или упрощённым диагностикумом: проверяется **именно текущая физическая цель**.

## 2. Изолированный Windows пакет P10DW R1

Файл: `research/packages/P10DW_R1_EXACT_INLINE_F6_ONE_1D_WINDOWS_20261121.zip`, **24 774 байта, SHA256 `04d619e6924bb5d8f0e3076c2bb371e67f78a174252658eacf8a0fdc14a95377`**, ZIP CRC13/13, SHA PIN12/12.

В пакете 13 файлов: **7 байтово исходных P10DV** source members, один ранее проверенный Gmsh Windows watchdog `P10DO_windows_guards.py` SHA256 `4755b76f01938688d1adaab5492b709b7d7ecbe5b02904db63df1fb3894aedac` из pinned P10DT ZIP SHA `f540adb8f7e9dc4a58fea8ebe5784c99fe4f2607cb6b82cf5ac65dd398b1eb08`, новый код `P10DW_one_click_1d.py`, две новые CMD, русский README и новый SHA manifest (`PIN12/12`). Сборщик `scripts/p10dw_build_package.py` проверяет два родительских ZIP, исходные CAD/F6 SHA, пересобирает одинаковый по датам и порядку файлов ZIP и исполняет **извлечённый** selftest. Предыдущие инструменты/маркеры не перепаковываются в разрешение повторить их.

1. `01_P10DW_SAFE_GEO_PREFLIGHT_ONLY.cmd`: source gate PIN12/12 + исходная P10DV math/C¹ проверка на17 075 точках, оригинальная принятая M1 SHA, исходные Field1/Field2/near/far + CAD, Gmsh4.15.2 executable SHA `317c43391e5b1fab3a1dd80dc5245dad6e2d087910f4b8ebc234bd6d4b8f41a1`, свободные RAM≥8GiB/disk≥1GiB, Gmsh `-version` и два `-parse_and_exit` ≤20с каждый. Код0 только при обоих PASS; новый `P10DW_PREFLIGHT_PASS.json` действителен24ч, маркер расходования не создаётся. Программа создаёт только собственные новые run-папки.
2. `02_P10DW_ONE_INLINE_F6_1D_ONLY.cmd`: повторяет SHA/ресурсные, M1 и GEO preflight; требует свежий A-PASS, затем отдельную точную фразу `RUN ONE P10DW INLINE F6 1D`. Прямо до первого и единственного native `gmsh -1` записывает **новые P10DW** эксклюзивные маркеры в `%LOCALAPPDATA%` и локальный `P10DW_RUNS`. Код2/STOP/TIMEOUT **расходует** одну попытку и не разрешает повторы. 1D native ≤15с/2GiB private/20MiB MSH/1MiB full stdout+stderr log/2 threads. Никакого `-2/-3`, физики, априорного потолка числа будущих M2 узлов, изменения старых папок или forward cache.
3. После каждого вызова создаётся один `P10DW_EVIDENCE.zip`: `P10DW_RUN_MANIFEST.json`, `P10DW_RESULT.txt`, исходные две generated GEO + CAD, полный Gmsh stdout/stderr `.log` и tail, trace при STOP. 1D `.msh` оставляется у исследователя (не отправляется); атрибуты из native log не подменяют геометрическую QA. Отдельные лог-файлы не требуются.

**Оценка под i7-7700K/64GiB:** по предыдущим F2/inline коротким нативным журналам 1D около0.2с, но для длинного F6 время неизвестно и **ограничено15с**; preflight native parse суммарно≤40с, плюс SHA/математический тест, ориентир полного Windows сценария до2мин; ≥8GiB свободной RAM и ≥1GiB disk, контроль private периодический (не hardware-hard cap). Ожидаемая выходная папка маленькая, ZIP без raw `.msh`/больших бинарников. Это **прогноз**, не измеренный Windows runtime P10DW.

## 3. Действительно выполненные проверки кода, а не нативного Gmsh

- Детерминированная сборка, ZIP CRC13/13, SHA PIN12/12; точные P10DV F6/CAD, original source identity, intact Windows CMD CRLF без BOM; автономный извлечённый `--selftest`, P10DV independent math17 075 и позитивный source gate **PASS**.
- `scripts/p10dw_isolated_guard_negative.py`: **11** изолированных тестов, включая повреждённый F6/CAD, заменённый ожидаемый M1 SHA, подложный файл M1 с правильным basename, Linux STOP до Gmsh/маркеров, ошибочный CLI, **FAKE** 1D stdout/mesh PASS, **FAKE** бесконечное ожидание с принудительной остановкой watchdog, отсутствие фразы до маркера и моделирование one-shot marker/replay STOP. Это **не** реальный Windows Gmsh, Win32 private/cap монитор не измерялся на пользовательском ПК.
- Публикация ZIP/кода/протокола — разрешённая исходниковая стадия; **пока не разрешает** запуска Gmsh `-1` или 3D. Ранее использованные P10DO/P10DQ/P10DR/P10DT маркеры сохраняются.

## 4. GO / STOP и следующий научный барьер

**A GO:** SHA оригинальной M1 и всех входов + обе native GEO parses exit0 без Gmsh Error, no marker, 0 mesh. При любом несовпадении — STOP и один малый evidence ZIP. **B GO** только после отдельно санкционированной одной 1D попытки и реального `P10DW_EVIDENCE.zip`: exit0, не более15с, лог `nodes>0, elements>0`, нет native Error; после независимого аудита можно проектировать отдельный один 3D M2 mesh-only и curved27QP/9-zone QA. При B STOP/timeout — **не повторять**; читать оригинальный лог и исходники. Даже успешный B не доказывает реальной κ во всём 3D, уменьшения объёмов Tet10, пространственной сходимости или корректности physical FEM.

**Сейчас от исследователя:** после публикации ZIP допустимо согласовать только безопасный A preflight; **до отдельного прямого разрешения native B `gmsh -1` не запускать**. Новый M2 `-3`, physical forward/adjoint/FEM — отдельные будущие решения.
