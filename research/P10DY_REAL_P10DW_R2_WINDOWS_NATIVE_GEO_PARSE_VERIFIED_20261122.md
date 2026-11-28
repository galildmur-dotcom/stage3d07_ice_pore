# P10DY — реальный Windows P10DW R2 GEO preflight PASS; полный inline F6 распознан Gmsh4.15.2, но ещё не вычислялся в 1D

**Дата:** 22.11.2026. **Уровень свидетельства:** оригинальный native Windows `-parse_and_exit` с полным source/mesh SHA preflight и независимым аудитом журналов. **Native Gmsh parsing 2/2 PASS; Gmsh mesh1D=0, 2D/3D=0, M2 Tet10/curved27QP=0, physical FEM/forward/adjoint=0.** Никакой новый Gmsh на машине ассистента не запускался; старые P10DO/P10DQ/P10DR/P10DT, P10DW-01 R1 evidence, markers, original H0/M1/forward cache не изменялись.

## 1. Установленный первичный факт

Исследователь прислал **оригинальный** `P10DW_EVIDENCE(1).zip`, сохранённый без изменений под `research/evidence/P10DY_P10DW_R2_REAL_GEO_PARSE_PASS_20261122/input/P10DW_EVIDENCE_R2.zip`: **ZIP SHA256 `bce04f56d4a1610f6b86c8acc1d8436d8f0d12aa66dfc63ff7701cad63472d36`**, CRC **7/7**, семь строго ожидаемых членов (JSON manifest, TXT, оригинальные generated GEO A/B, CAD, два полных native parse `.log`). Источник программы — опубликованный P10DW **R2** ZIP SHA256 `1418d8ccf8374b275b7112137e23e6a5a94e65e549a50b44cbd66b4f6105d04f`, CRC13/13 SHA12/12 по source release. Manifest:

- `protocol=P10DW_R2_EXACT_INLINE_F6_ONE_1D_NO_3D_NO_FEM`, `mode=SOURCE_GEO_PREFLIGHT`, `status=P10DW_READ_ONLY_PREFLIGHT_PASS`, run_id из native log **`P10DW_20261122_040025_186707`**.
- `started_utc=2026-11-22T04:00:25.186830+00:00`, `finished_utc=2026-11-22T04:00:29.434809+00:00`, elapsed **4.247979с**.
- `source_sha_pins=12`, `math_points=17075`, оригинальная принятая `P10DG_M1_CANDIDATE.msh` SHA256 **`ca6b6b6588dc72c5dd3ed2e92e24794560ee2407e350c8a44858e9c3c7d0360f`** согласно Windows wrapper hash check, принятая original M1 = 9736 Tet10 по ранее опубликованной D-019 аттестации; не H0/U0. Gmsh Windows exe `C:\gmsh-4.15.2-Windows64\gmsh.exe` SHA256 по wrapper **`317c43391e5b1fab3a1dd80dc5245dad6e2d087910f4b8ebc234bd6d4b8f41a1`**, native version **4.15.2** подтверждена также нативным stdout. Free RAM58,907,725,824B (≥8GiB)/free disk8,020,675,272,704B (≥1GiB) по wrapper, безопасный ресурсный gate PASS.
- **`native_parse_attempts=2`**, `native_parse_passed=[A_ORIGINAL_M1_FIELD2,B_EXACT_INLINE_F6]`; **`native_1d_attempts=0`, `native_2d_3d_attempts=0`, `physical_FEM_attempts=0`**. Исходный `RESULT.txt` подтверждает `READ_ONLY_PREFLIGHT_PASS`, StopReason пуст.

Независимый аудит байтов GEO из оригинального Windows ZIP:

| Файл | SHA256 | Происхождение |
|---|---|---|
| `GEO/A_ORIGINAL_M1_FIELD2.geo` | `c6ec88a3fe91db0f3c369391a91aefbd1bc83f1d3033b38a985c3033c605ddd8` | exact source prefix P10DN, `Background Field=2` |
| `GEO/B_EXACT_INLINE_F6.geo` | `32f8f959002cbd41539e355a80437c2ca3be12fdd3ba12de31eadf2c021b9561` | **побайтно exact P10DV** 494-char F6 без F3/F4/F5 MathEval |
| `GEO/sphere_pore_B6_refined.geo` | `8029a6ed22bcf312701cd6abc46bbe5575e52df16fd5218dd936b01d5cd6fcf0` | exact original CAD and Field2 Threshold |

**Нативные Gmsh stdout журналы** (оригиналы в том же ZIP) содержат каждый **ровно одну** команду `gmsh.exe GEO/<имя>.geo -parse_and_exit`, `Gmsh 4.15.2`, прочитанный `sphere_pore_B6_refined.geo` с OCC Difference/Fragments, `Done reading` обоих GEO и `Stopped` без `Error :`. Wrapper добавил вариант в `native_parse_passed` только после `p.returncode == 0`, но **числовой exit0 не записан отдельным полем в manifest**: правильная атрибуция — native stdout плюс source control flow.

| Native parse | Wall по Gmsh логу | SHA256 полного оригинального `.log` | Вывод |
|---|---:|---|---|
| A / исходное Field2 | **0.020869с** | `1cfe892aeaca4b8216ca1b61cf235df122ed69db9c938a411166c47007d3b0cd` | PASS `-parse_and_exit` |
| B / точное inline F6 | **0.0226398с** | `33c9d02fe260b094d7c426f638b78ddeb11e8ac3fda520857df6bdebc6a21289` | PASS `-parse_and_exit` |

**Граница доказательства:** `-parse_and_exit` проверяет синтаксис GEO/поля и построение OCC CAD, но **не оценивает** длинное MathEval F6 при сеточной 1D итерации, **не** создаёт даже 1D сетку и не измеряет 3D локальное реальное уменьшение объёмов. Оригинальные M1 raw `.msh` и бинарный `gmsh.exe` у ассистента отсутствуют, поэтому их SHA считаются **Windows-wrapper-reported with source hash guard**, а не локальной независимой побайтовой аттестацией. Локальное наличие profile marker в Windows **не инспектировалось**; опубликованный source режима `--preflight-only` не вызывает `consume_one_shot`, а manifest native1D=0.

## 2. Независимая воспроизводимая проверка

`scripts/p10dy_audit_p10dw_r2_windows_geo_parse.py` фиксирует точный ZIP SHA и R2 release SHA, CRC7/7, структуру/содержимое манифеста/RESULT, все три original generated GEO и CAD SHA, точные native parse CLI в полных логах, `Gmsh4.15.2`, `Done reading/Stopped`, wall0.02с, отсутствие Error, единый run_id, наличие всех resource/source/M1 fields и 1D/3D/FEM=0. Derived: `research/evidence/P10DY_P10DW_R2_REAL_GEO_PARSE_PASS_20261122/derived/P10DY_P10DW_R2_NATIVE_GEO_PARSE_AUDIT.json` **SHA256 `edff375f141b2c74342924a6231e80854c4cc5f14c79dbfe17510954c445d673`**. **Семь** намеренных повреждений отклоняются: F6 coefficient, native `-1` вместо parse, false native1D counter, source PIN11 вместо12, неправильная M1, повреждённый CAD, native Error. Итог `P10DY_ORIGINAL_P10DW_R2_NATIVE_GEO_PARSE_AUDIT_PASS CRC7/7 PIN12/12 GEO3/3 native_parse2/2 negative7/7 native_1d=0 M2_3D=0 FEM=0`.

Дубликат R1 false STOP от 22.11.2026 и его исправление R2 P10DX остаются историческим первичным фактом, ни код/архив R1, ни markers не менялись; подтверждённый теперь R2 `-parse_and_exit` **снимает только вопрос синтаксиса и CRLF**, не решает проблему скорости native 1D.

## 3. Новый различающий научный барьер, ещё не разрешённый

P10DT C ранее прошёл быстрый **короткий** inline spatial clamp, P10DV math доказал точное κ C¹∈[0,1], `Vtarget_M2/Vtarget_M1=1−0.20κ` в [0.8,1]; P10DY впервые подтвердил native parse именно полного **494-char** inline F6. **Единственный минимальный следующий опыт** — отдельно согласовать **одну** нативную 1D-попытку Gmsh4.15.2 на **точном B F6**, используя **уже выпущенный и установленный R2** `02_P10DW_ONE_INLINE_F6_1D_ONLY.cmd`. Он повторит source/M1/Gmsh preflight и два parse, потребует вручную точную фразу **`RUN ONE P10DW INLINE F6 1D`**, создаст эксклюзивные **только P10DW** local+profile markers **непосредственно до** единственного `gmsh -1`; watchdog 15с wall, ≤2GiB periodic private, ≤20MiB `.msh`, ≤1MiB log, 2 threads; результаты один небольшой оригинальный `P10DW_EVIDENCE.zip`. Результат даже при TIMEOUT/код2 расходует one-shot, **не повторять и не удалять marker**. Предполагаемое native время простого inline P10DT C ~0.21с — **не прогноз для длинного F6**, лимит15с; RAM/disk preflight как выше, полный тест с проверками ориентировочно до2мин (оценка).

**Пока нет нового согласия исследователя на кнопку02. Не запускать её автоматически.** Без реального bounded 1D evidence нельзя запускать M2 `-3`/27QP/9-зонную QA, а physical forward/adjoint/FEM на M2 требует отдельной гораздо более поздней санкции. Вся исходная научная программа — согласованные forward/adjoint на одной сетке, приполюсный signed `(r,θ,φ,t)` анализ и пространственная сходимость — не изменена.
