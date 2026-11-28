# P10DT R1 — оригинальные P10DR логи опубликованы, три контролируемых 1D-контраста подготовлены

**21.11.2026.** Статус: архивирование первичного Windows P10DR, независимый P10DS аудит и разработка **source-only** P10DT. В этом этапе **0 native Gmsh, 0 реальных 1D/2D/3D, 0 FEM**. Новая M2 сетка и геометрическая сходимость не установлены. Предыдущие P10DO/P10DQ/P10DR одноразовые пуски потреблены и повторению не подлежат.

## 1. Происхождение наблюдений

- **Первичный оригинал:** `research/evidence/P10DS_P10DR_LOG_DIAGNOSTIC_20261121/input/P10DR_EVIDENCE.zip`, неизменённый файл исследователя, SHA256 `72e06f67338ab5f2b5f25080ac89e41c9026011b3aaedc0e2f155f0fb7eb1b7f`, CRC24/24. Содержит реальные `.log`, `.geo`, manifest и tails. Публикация оригинала явно разрешена исследователем; в ZIP остаются исходные локальные Windows пути.
- **Независимая репликация аудита P10DS:** `scripts/p10ds_audit_p10dr_logs_and_fields.py`, производный JSON `research/evidence/P10DS_P10DR_LOG_DIAGNOSTIC_20261121/derived/P10DS_P10DR_LOG_AUDIT.json` SHA256 `3be0ec72e0dbf2831bef0b86b2102a97166943b8992c1826d15a4b0f3f63e8a3`, PASS. Проверено 7/7 исходных SHA, 7/7 GEO с учётом Windows CRLF, 7/7 Gmsh native parse, полные логи↔tail, 24/24 CRC и 2D=3D=FEM=0.
- **Реальные результаты:** A (Field2) exit0, wall0.2124705s, native log 244 nodes/135 elements; B (только F3) и C (только F4) оба TIMEOUT_15S, также D–G TIMEOUT_15S. Все шесть STOP на 1D окружностях14/17 без Gmsh `Error`, сумма90.6187595s, polled private peak245944320B. Экспорт A в 280B MSH2 сам по себе не удостоверяет физические 1D группы. Это *свидетельство о задержке*, не доказательство конкретной ошибки MathEval или бесконечного цикла.
- **Эталон оригинальной принятой M1:** SHA256 `ca6b6b6588dc72c5dd3ed2e92e24794560ee2407e350c8a44858e9c3c7d0360f`, 9736 Tet10 — только SHA из Windows manifest. Исходные H0/U0 не заменяют M1. Правильная будущая M2 постановка — κ C¹∈[0,1], целевое `V2/V1=1−0.20κ`, без физического FEM до 3D QA.

## 2. Проверяемая гипотеза, а не диагноз

В P10DR остановка воспроизводится отдельно с F3 и F4, без F5/smoothstep/exp/log. Её объяснение пока **UNKNOWN**: вложенное обращение к `MathEval`, пространственный clamp `min/max` или итерационная процедура mesh1D на геометрии. P10DT различает эти гипотезы минимально:

| Вариант | Источник Q | Ограничение / вопрос |
|---|---|---|
| A `A_DIRECT_CONSTANT_F6` | константа `0.5` прямо в F6 | Контроль самого `F6` и 2%-ной поправки без F3. |
| B `B_NESTED_CONSTANT_F3` | объявлен `F3=MathEval("0.5")`; F6 ссылается на F3 | Проверка вложенного `MathEval` без координат. |
| C `C_DIRECT_SPATIAL_CLAMP_F6` | оригинальная F3 `min/max/sqrt(x,y,z)` прямо в F6 | Проверка пространственного clamp без ссылки F3. |

Во всех случаях `h6/h2 = 1−0.02 Q∈[0.98,1]`, диагностический целевой объём∈[`0.98³=0.941192`,1]. Это **не реализация** M2 целевого −20% объёма. Исходный `P10DN_M2_FIELD20.geo` и CAD byte-pinned. Нельзя интерпретировать PASS/STOP единственного контроля как прямое измерение значения исходного F3 на кривых или как определение причины: взаимодействия возможны. `parse_and_exit` проверяет допустимость синтаксиса, **не** runtime стоимость поля.

## 3. Неизменяемый исследовательский выпуск

**ZIP:** `research/packages/P10DT_R1_THREE_1D_CONTRAST_WINDOWS_20261121.zip`, **18695B**, SHA256 **`f540adb8f7e9dc4a58fea8ebe5784c99fe4f2607cb6b82cf5ac65dd398b1eb08`**, CRC9/9, SHA pin8/8. Включает точные 4 файла из P10DR release SHA256 `4ed2a21c64480996b88d7c1f465fc884b3a175f659e424d2039c413ca420a011` и четыре новые инструкции/driver/CMD + pinned JSON. Сборщик `scripts/p10dt_build_package.py` требует одновременно байтовый SHA оригинального Windows P10DR evidence и старого source ZIP.

**Безопасная кнопка** `01_P10DT_PREFLIGHT_ONLY.cmd`: SHA8/8, исходный GEO/F3-F6, точная Gmsh4.15.2 binary SHA `317c43391e5b1fab3a1dd80dc5245dad6e2d087910f4b8ebc234bd6d4b8f41a1`, ≥8GiB available RAM/≥1GiB free disk и 3 native `-parse_and_exit` без one-shot marker. Результат PASS: `P10DT_READ_ONLY_PREFLIGHT_OK`. Не использует native meshing.

**Отдельная однократная кнопка** `02_P10DT_ONE_1D_DIAGNOSTIC.cmd`, только после первого PASS; пользователь вручную вводит **`RUN ONE P10DT 1D DIAGNOSTIC`**. Непосредственно перед первым Gmsh `-1` создаются два **новых P10DT** exclusive маркера в распакованном каталоге и `%LOCALAPPDATA%/Stage3D07`. После любого STOP **не удалять маркеры и не повторять кнопку**. Каждая из **трёх** разных 1D попыток: ≤15s wall, ≤2GiB private, ≤20MiB mesh, ≤1MiB Gmsh stdout `.log`, `-nt 2`; независимое продолжение B→C после отдельного TIMEOUT. Общее native mesh wall до ≈45s, отдельно parse/preflight/упаковка. `-2/-3`, physical forward/adjoint/FEM, H0 cache и старые маркеры/результаты не вызываются.

**Исходный Linux/source QA (НЕ Windows native):** `scripts/p10dt_synthetic_1d_unit.py` запускает исходный zip-экстракт с source selftest, fake Gmsh1D PASS/error/timeout, проверяет порядок всех трёх вариантов после STOP, точную ручную фразу, новые маркеры, безопасный Linux stop и отрицательную мутацию pinned GEO. Все PASS. `scripts/p10ds_audit_p10dr_logs_and_fields.py` повторно PASS. Это проверка релизной логики, не гарантия скорости на реальном Gmsh.

## 4. Единственный следующий источник данных

На Windows распаковать **новый P10DT ZIP отдельно** от `G:\ildar\Stage3D07`, запустить кнопку01; только после `P10DT_READ_ONLY_PREFLIGHT_OK` кнопку02 и точную фразу. Прислать **один `P10DT_EVIDENCE.zip`** из новой папки `P10DT_RUNS` с настоящими логами, JSON и всеми GEO. Код2 при остановке одного теста означает bounded STOP, не приглашение к повтору. До независимого научного анализа A/B/C **не назначать новое M2 -3 и никакой FEM**.
