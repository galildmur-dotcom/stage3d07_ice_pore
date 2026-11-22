# P10DX — реальный P10DW R1 preflight STOP по CRLF, независимо проверен; R2 подготовлен без Gmsh

**Дата:** 22.11.2026. **Фактически:** получен **оригинальный Windows** `P10DW_EVIDENCE.zip`, проведён побайтовый и отрицательный аудит, подготовлен R2 с минимальной правкой. **Новый native Gmsh при аудите/сборке=0, M2 1D/3D/FEM=0.** Ни однократная P10DW 1D попытка, ни прежние P10DO/P10DQ/P10DR/P10DT кнопки не были вызваны; старые markers/H0/M1/cache не изменяли.

## 1. Оригинальное первичное свидетельство, не пересказ окна

Байтово неизменённый файл `research/evidence/P10DX_P10DW_R1_WINDOWS_NEWLINE_STOP_20261122/input/P10DW_EVIDENCE.zip`, **3649 B, SHA256 `d173de50c73167e3badbfe42c3fabb87b2ad345ac47f44623585a7da16655acc`**, ZIP CRC **6/6**. Внутри оригинальный `P10DW_RUN_MANIFEST.json`, `P10DW_RESULT.txt`, `P10DW_STOP_TRACE.txt`, два generated GEO и точный include CAD. Не присвоен искусственный native run_id; timestamp **2026-11-22T03:51:15.802918+00:00** из manifest, ошибка за ~5.24с.

- `protocol=P10DW_R1_EXACT_INLINE_F6_ONE_1D_NO_3D_NO_FEM`, `mode=SOURCE_GEO_PREFLIGHT`, `status=P10DW_STOP_NO_FEM`, `stop_reason=P10DW_STOP: generated inline candidate altered`.
- **`native_parse_attempts=0`**, `native_1d_attempts=0`, `native_2d_3d_attempts=0`, `physical_FEM_attempts=0`. Следовательно, оригинальный Windows STOP случился **до** `gmsh -parse_and_exit`; отсутствие Gmsh log объясняется незапуском, не потерей файла. Никакой сетки M2/1D в данном запуске нет.
- Stack: `do_run→preflight→generated_sources` в опубликованном неизменённом R1 коде, остановка точно на `sha256(exact_path) == INLINE_SHA` (строки 293,163,137 в original Windows traceback). В R1 `.write_text(exact, encoding="utf-8")` вызывает платформенный перевод `\n→\r\n` на Windows по умолчанию, а SHA проверяется **по байтам** как в исходном LF-файле.
- Windows-generated `GEO/B_EXACT_INLINE_F6.geo` **SHA256 `af8411f8deccd14b1905809b5a2e6ca04b9671789101acbc8b8233d89d10654a`**. После удаления **только CR из пар CRLF** SHA **`32f8f959002cbd41539e355a80437c2ca3be12fdd3ba12de31eadf2c021b9561`**, и нормализованный файл **побайтно равен** оригинальному pinned P10DV inline GEO. `GEO/A_ORIGINAL_M1_FIELD2.geo` столь же семантически точно повторяет pinned baseline после CRLF→LF; включённый `sphere_pore_B6_refined.geo` SHA **`8029a6ed22bcf312701cd6abc46bbe5575e52df16fd5218dd936b01d5cd6fcf0`**, без изменений.
- Исходный manifest содержит ожидаемую original M1 SHA `ca6b6b6588dc72c5dd3ed2e92e24794560ee2407e350c8a44858e9c3c7d0360f`, но **не содержит вычисленный SHA M1 и Gmsh EXE**: R1 обновлял поля манифеста **после** `generated_sources`, не достиг этого места. Достижение `generated_sources` согласно точному коду предполагает, что source/math, проверка M1, версии/хеша EXE и ресурсов не остановили программу; **это вывод по control flow, а не независимая байтовая повторная аттестация M1/EXE на нашем компьютере**.

Воспроизводимый `scripts/p10dx_audit_p10dw_windows_preflight_stop.py` строго проверяет оригинальный ZIP SHA, CRC6/6, шесть имён и contents, статус и счётчики, точный traceback, обе GEO и CAD, исходный опубликованный код, обоснование перевода CRLF. **4/4 негативные подмены STOP** (изменение коэффициента F6, CAD, trace и ложная native parse). Derived JSON `research/evidence/P10DX_P10DW_R1_WINDOWS_NEWLINE_STOP_20261122/derived/P10DX_P10DW_R1_STOP_AUDIT.json` SHA256 **`73178bcc16fd95184644ade7e9b9ab86e3e461b3843032c3ca003ef3dfd6786d`**. Вердикт **`P10DX_REAL_P10DW_R1_WINDOWS_CRLF_FALSE_STOP_AUDIT_PASS`**; это **ошибка упаковки/записи GEO, не научное опровержение κ или дефект Gmsh**.

## 2. Исправление R2 — точно ограниченное

Источник исправления **только** original R1 package `research/packages/P10DW_R1_EXACT_INLINE_F6_ONE_1D_WINDOWS_20261121.zip` SHA256 `04d619e6924bb5d8f0e3076c2bb371e67f78a174252658eacf8a0fdc14a95377` + оригинальный Windows ZIP с вышеуказанной SHA. Сборщик **`scripts/p10dx_build_p10dw_r2_package.py`** проверяет оба хеша, CRC и sourcePIN12/12 R1, делает детерминированную *текстовую подстановку ровно двух вызовов записи*:

```python
# R1, зависит от переводов строк Windows:
baseline_path.write_text(baseline, encoding="utf-8")
exact_path.write_text(exact, encoding="utf-8")

# R2, побайтно одинаково в Linux/Windows:
baseline_path.write_bytes(baseline.encode("utf-8"))
exact_path.write_bytes(exact.encode("utf-8"))
```

Единственная другая правка собственно Python runner — идентификатор ревизии `P10DW_R1→P10DW_R2`; метки CMD и русский README приведены к R2. **Не менялись** formula 494 char F6, CAD, Field1/Field2, исходные near/far, κ C¹∈[0,1], target `Vtarget_M2/Vtarget_M1=1−0.20κ`, original accepted M1 SHA, Gmsh exact exe SHA/version, `-parse_and_exit`, единственное возможное будущее `-1`, 15s/2GiB/20MiB/1MiB, ручная фраза, пути и имена P10DW global/local one-shot markers. R1 архив и первичный STOP **сохранены** как воспроизводимая история, R2 распаковывается исключительно **в новую папку**.

**R2 выпуск:** `research/packages/P10DW_R2_EXACT_INLINE_F6_ONE_1D_WINDOWS_20261122.zip`, **24 392 B**, SHA256 **`1418d8ccf8374b275b7112137e23e6a5a94e65e549a50b44cbd66b4f6105d04f`**, ZIP CRC13/13 PIN12/12, CMD CRLF без BOM; полный русский README `research/proposals/P10DW_R2_WINDOWS_EOL_20261122/README_P10DW_R2_RU.md`. В ZIP — самодостаточные исходники/guard/P10DV math/CAD, только две кнопки (01 safe native parse и 02 отдельный ещё не разрешённый one-shot 1D).

## 3. Новая проверка, различающая R1 и R2, без настоящего Gmsh

`scripts/p10dx_r2_newline_regression.py` извлекает **оба** release ZIP и на Linux специально моделирует поведение `Path.write_text(newline=None)` для Windows `\n→\r\n`:

1. R1 детерминированно воспроизводит **точно тот же** `generated inline candidate altered` STOP и неправильный Windows SHA, который появился в присланном ZIP.
2. R2 при **том же самом** искусственном Windows-переводе формирует оба GEO с исходными LF. B-GEO сохраняет **точный** SHA `32f8...`, CAD неизменна, baseline имеет `Background Field=2`.
3. Извлечённый R2 `--selftest` математического поля/строгого исходного SHA **PASS**; PIN12/12, ZIP CRC13/13; дополнительная подмена R2 runner **STOP**.
4. Linux `--preflight-only` **STOP до любого native**, не создаёт one-shot marker. Повторно исполнены все **11/11** ранее разработанных исходниковых/FAKE-native/one-shot negative checks уже против **R2**. Фальшивые Gmsh PASS/timeout не являются реальным Gmsh.

**Вердикт теста:** `P10DX_R2_WINDOWS_EOL_REGRESSION_PASS R1_reproduced_STOP=YES R2_GEO_exact_SHA=YES R2_negative_11_11=PASS native_Gmsh=0 FEM=0`.

## 4. Фактические и допустимые последующие этапы

**Сейчас подтверждено:** исходная κ математически P10DV равна до и после R2; первичный Windows P10DW-01 STOP произошёл **до native parse и без расходования one-shot**, R2 source-level исправляет наблюдаемый CRLF STOP. **Ничего не доказано о реальном Gmsh4.15.2 parsing/evaluation длинной F6, 1D runtime, 3D M2 mesh/curved27QP/9-zone объёмах, physical forward/adjoint/FEM или пространственной сходимости производных.**

**Следующий минимальный Windows шаг (самостоятельный новый R2 preflight, без маркера и новой сетки):** исходный P10DW-01 исследователь уже разрешил 22.11.2026; предложить только новое `01_P10DW_SAFE_GEO_PREFLIGHT_ONLY.cmd` из **R2 ZIP**, полный original P10DG M1 SHA, Gmsh4.15.2 `-parse_and_exit` два варианта≤20с каждый, RAM свободно≥8GiB/disk≥1GiB, ожидаемое время≤2мин (оценка), затем **один новый R2 `P10DW_EVIDENCE.zip`** даже при STOP. Не трогать R1 run-папку/маркеры. **Кнопку02/единственный native Gmsh `-1` не запускать** до отдельного явного разрешения **после независимого аудита R2 preflight**. Новый 3D M2 mesh-only и физический FEM — отдельные, не разрешённые этим отчётом этапы.
