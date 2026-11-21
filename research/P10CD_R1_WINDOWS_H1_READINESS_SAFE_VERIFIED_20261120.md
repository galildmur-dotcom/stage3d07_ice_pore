# P10CD R1 — H1 Windows mesh/EXE/Git read-only readiness проверена, FEM=0

**Дата:** 20.11.2026. **Результат:** `P10CD_H1_READINESS_OK_NO_FEM`, инженерный P10CD R1 **CLOSED_SAFE_ONLY**, научный H1 thermal-QP radial/polar experiment **PENDING_UNAUTHORIZED**. Не считать это физическим H1 и не менять статус старой P10AW/P10CA native physical завершённости.

## 1. Первичные байты и версия

Пользователь передал `P10CD_EVIDENCE.zip`: **912 B**, SHA-256 **`6b1def1a73072084d59a5be22d7affbeec5fa9375a2f2aff0e68d076750be607`**. ZIP CRC **PASS 1/1**, содержит только `P10CD_RESULT.txt`. Инструмент отчёта: `TOOL_REVISION=P10CD_R1_H1_MESH_AND_PINNED_EXE_READINESS_NO_FEM`; SHA-256 PS1 в Windows **`1e2bda6becfa03480c646bf9d1a4c34815f85ce7f615bc3730143fa257f64db9`** побайтово совпал с заранее опубликованным P10CD R1. Исходный One Click архив **`929098e2c20c1fa360087c9c923df1ef8210c45961d90a1743a14c762c02a2f3`** ранее имел CRC 4/4 PASS. Локальный Windows START 2026-11-20T17:43:24.1389043+05:00, FINISH 17:43:24.8870799+05:00, ~**0.749 s**. Эти timestamps — время только safe probe, **не H1 solver runtime**.

## 2. SHA и геометрия сетки

| Проверяемый объект | Фактически зафиксировано | Оценка |
|---|---|---|
| H1 Gmsh | `2.2_ASCII` | PASS |
| H1 mesh SHA-256 | `394ee339073fe6eacfd58c549ad0b0218a9bdadf8f36a2ca435a1ca3fad0598d` | Exact P10AV/P10AR match |
| Узлы / Tet10 | `27757 / 19412` | PASS |
| Tri6 total / pore / top | `2536 / 282 / 314` | PASS |
| Element records | `21948 = 19412 + 2536` | PASS |
| Existing P10CA Windows EXE SHA-256 | `17c31f426245317271245e340d68fa5de1e4eb144b7be986167505e14cbed924` | Exact earlier physical / P10CB R2 match |
| Runtime directory | `C:\mingw64\bin` exists | PASS existence only, not DLL list |
| QP volume/step | `1242368 = 19412 × 64` | PASS |
| QP volume/6 steps | `7454208` | PASS |
| Top Robin QP/step | `5024 = 314 × 16` | PASS |
| Future local bins/audit rows | `606 / 6` | Expected schema, **not new data** |

Original source Git HEAD before/after **`90fd2559c0224ac0a7d2dbe2fe081a6a319080e4`**; status **`0/7/4`**; status fingerprint before/after **`bb376579544e328291674fa91d20c7b8a4b9d4a306fd7a3af47c172cedb75258`**. `ORIGINAL_WORKTREE_PRESERVED=YES`. Сам read-only инструмент пересчитал SHA сетки/EXE и status до/после, не копировал .msh/EXE в ZIP. Процедура не выполняла даже `--help`/`--selftest` заново, использовала доказанный P10CB R2 инженерный контекст. `PHYSICAL_FEM_RUNS=0`.

**Независимая проверка здесь:** парсинг оригинального TXT в ZIP, 19/19 фиксированных полей точно совпали с предобъявленными значениями и опубликованным сценарием. Повторно вычислены семь инвариантов: head, status counts, status SHA before/after, 64×Tet10, ×6 temporal QP, 16×top Tri6, sum Tet10+Tri6; **все PASS**. Это вторая проверка *отчёта и арифметики*, не новое прямое чтение H1 .msh на нашем компьютере.

## 3. Строгий статус и следующий научный переход

**Подтверждено:** точная H1 mesh, ранее собранный exact Windows EXE и оригинальный dirty Git доступны на пользовательском ПК и не изменились в рамках safe probe. Предполагаемый future H1 thermal QP объём и формат известны. Инженерная предпосылка минимального H1 local thermal QP experiment выполнена без build/replacement.

**Не подтверждено:** P10CD **не запускал H1 thermal QP физику** и не выдавал 606/6 новых CSV; H1 local radial/polar distribution, per-step CSR/QP equality и native physical exit0 в будущей попытке UNKNOWN. Прежний P10AW H1 EXE SHA/native physical exit0 исторически UNKNOWN; P10CA H0 old native physical exit0 UNKNOWN. P10CB короткий exit0 не восполняет эти данные. Двухсеточная локальная проверка, даже при будущем успехе, не докажет spatial convergence; полная временная сходимость также открыта.

**Следующий шаг при новой воле исследователя:** оформить **одну** адресную physical H1 `R/EDV_VAR ξ=0, 6×150s, B6 5mm, ANALYTIC_TET10`, same H1 mesh внутри forward/adjoint, only thermal QP radial/polar for `jpeak`; reuse exact pinned P10CA EXE без новой сборки, в отдельном output. Не запускать P10AW повторно как целевой глобальный результат. По прошлым H1/H0 измерениям ориентир 8–15 минут, *предлагаемые* STOP limits ≤20min, observed process ≤8 GiB, new files ≤1.5 GiB, 4 threads; требовать ≥16 GiB свободной RAM и ≥4 GiB свободного диска. Эти limits надо явно утвердить; опросная защита не является строгой аппаратной гарантией. Применить доказанный P10CB .NET Process direct native ExitCode **до Dispose** и child-only `C:\mingw64\bin`. Включить одноразовый физический marker и внешнюю изолированную папку, не менять original G:. Пользователю показать точный One Click package/contract и запросить отдельную санкцию. **D-015 H0 уже израсходована; новый H1 solver пока запрещён.**

**Исходное evidence:** `research/evidence/P10CD_R1_WINDOWS_READINESS_VERIFIED_20261120/input/P10CD_EVIDENCE.zip`, оригинальный TXT рядом. **Derived:** `research/evidence/P10CD_R1_WINDOWS_READINESS_VERIFIED_20261120/derived/P10CD_R1_INDEPENDENT_AUDIT.txt`. Общий протокол: `research/P10CD_H1_THERMAL_QP_RADIAL_POLAR_TARGET_PROTOCOL_SAFE_PREPARED_20261120.md` (помечен новой Windows верификацией).
