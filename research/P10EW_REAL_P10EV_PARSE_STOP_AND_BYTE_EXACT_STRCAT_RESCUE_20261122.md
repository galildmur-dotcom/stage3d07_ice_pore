# P10EW — подтверждённый P10EV lexer STOP, точное исправление StrCat, parse-only Windows пакет (22.11.2026)

## 1. Оригинальный Windows P10EV — наблюдение, не гипотеза

Исследователь передал приватный `P10EV_EVIDENCE.zip`: 7889 Б,
SHA-256 `eaa181421a55d4cf23a3393466fff045baf8e1d66dd7eda19d2dd62c211fe752`,
CRC10/10. Оригинал остаётся приватным и **не отправляется в GitHub**.
Независимый исходниковый скрипт `scripts/p10ew_audit_p10ev_real_stop.py`
сверяет точные 10 имён файлов, digest, исходный GEO, manifest, два
нативных parse logs, Gmsh EXE pin, M1 и нулевой счётчик mesh/FEM.
Проверка `P10EW_P10EV_INDEPENDENT_EVIDENCE_STOP_AUDIT_PASS`.

Первичный `P10EA_RUN_MANIFEST.json`:

- revision `P10EV_R1_ONE_AUTHORIZED_C1_JOINT_3D_M2_MESH_ONLY`,
  режим `SAFE_PREFLIGHT` и статус `P10EV_STOP_NO_FEM`;
- прежняя **принятая M1** SHA256
  `ca6b6b6588dc72c5dd3ed2e92e24794560ee2407e350c8a44858e9c3c7d0360f`;
- `native_parse_attempts=2`, `native_parse_passed=[A_ORIGINAL_M1_FIELD2]`;
  A действительно прошёл native Gmsh parse, B нет;
- `native_1d_2d_attempts=0`, `native_3d_attempts=0`,
  `physical_FEM_attempts=0`, raw M2 нет;
- `B_EXACT_INLINE_F6_PARSE.log`: `Error : String too long`,
  синтаксическая ошибка на строке 8, `End of file in string`.

Это **ошибка записи нашего исходника**, а не научный D-025 STOP
фактической сетки. Новый M2 не существует; ранее явно разрешённая
одна native -3 попытка не расходовалась. Старый `P10EV` и его
кнопку `02` **не использовать** и не переписывать, никаких
изменений исторических markers, H0, forward/adjoint/FEM.

## 2. Непосредственная техническая первопричина

Оригинальный P10EU GEO SHA
`4c4a4aeb4f97bfec350e1e057a57e275d436c09d63a02438a8acfe4ad386253a`
записывал 4198 символов в один литерал `Field[6].F = "...";`.
Исходный lexer **Gmsh 4.15.2** (`src/parser/Gmsh.l`, `parsestring`)
использует буфер `char tmp[1024]` и проверку
`i >= sizeof(tmp)-1`, вызывающую `Msg::Error("String too long")`.
Лимит одного литерала **1023 символа** — точное объяснение STOP.
Источник: [Gmsh 4.15.2 исходный лексер](https://fossies.org/linux/privat/gmsh-4.15.2-source.tgz/gmsh-4.15.2-source/src/parser/Gmsh.l?M=178).

Официальный [Gmsh 4.15.2 Reference Manual, String expressions](https://gmsh.info/doc/texinfo/gmsh.html)
определяет `StrCat(string-expression,...)` для конкатенации и
допускает `string-expression` в `Field[i].F`. Это обосновывает
*исходниковое* исправление, но пока не доказывает, что Windows
Gmsh 4.15.2 скомпилирует/вычислит итоговую MathEval.

## 3. P10EW R1 — только способ представления, а не математическая модель

Генератор `scripts/p10ew_strcat_parser_rescue_source_only.py`
из **SHA-pinned оригинального** P10EU извлекает те же 4198 ASCII
символов без пробелов и перестановки. Разбивает на 7 литералов:
`[600,600,600,600,600,600,598]`; итоговая `StrCat` строка в
точности идентична исходной. Реконструкция независимо сверяется
из созданного GEO. Новое поле остаётся одним `Field[6]=MathEval`,
без вложенных MathEval / F2-reference, physical tags/CAD, legacy Field2,
mesh sizing precedence, Alg2D5/3D10 и Tet10 не меняются.

**Научные следствия тождества** (не новый сеточный опыт):
поля P10ET/P10EU \(C^1\) и ограниченная β, κ, αN0.23,
αS≈0.229661, wall-normal fade остаются идентичными; исходниковые
7620 probes max relative error 2.7246553e−16, κ1 номинальное
\(h^3\) относительно Field2=0.800000…0.844772, относительно
bounded M1=0.770339…0.807861; κ0 max ≈1.171% только
на сглаженных C⁰-изломах. **Реальный** 3D D-025 по
северу/югу 0.75–0.85 отдельно **UNKNOWN**, FEM=0.

Новый GEO: `gmsh/P10EW_M2_C1_JOINT_STRCAT_SOURCE_ONLY.geo`.
Исходниковый аудит:
`research/evidence/P10EW_STRCAT_RESCUE_20261122/derived/P10EW_STRCAT_SOURCE_AUDIT.json`.
Публичный производный аудит оригинального приватного STOP:
`P10EW_P10EV_REAL_PARSE_STOP_AUDIT.json` в том же каталоге.

## 4. Изолированный P10EW Windows preflight (без 02 и Gmsh -3)

Исходники `research/proposals/P10EW_STRCAT_SAFE_PARSE_WINDOWS_20261122/`;
builder `scripts/p10ew_build_safe_parse_bundle.py`. Точный P10EV R1
оригинальный ZIP SHA
`20a7a322b672b24d44f26b7cc2b723b39165a2d67b4187f589884ce931655010`
входит вложенно для исторической SHA-проверки; старые кнопки внутри
`P10EV_PINNED_PARENT` запрещено запускать.

Новый пакет:

- `research/packages/P10EW_R1_STRCAT_SAFE_PARSE_ONLY_WINDOWS_20261122.zip`,
  **116822 Б, SHA-256
  `a375bff007a6ce4c04e3590877359e870f9044e0bc385a8d26f3bebf1415b968`**;
- CRC51/51, pin 5 новых файлов, exact parent P10EV CRC45/45;
- extracted Python source selftest PASS, inherited SHA/M1/curved27QP
  selftest PASS, Linux `--safe-parse` ожидаемо STOP без Gmsh;
- корневая **только одна** кнопка `01_P10EW_SAFE_PARSE_ONLY.cmd`;
  автоматический source SHA, M1 SHA, Gmsh4.15.2 EXE SHA,
  *ровно два* native `-parse_and_exit` и M1 label при PASS;
- выход при любом STOP/PASS — один `P10EW_EVIDENCE.zip`, собственная
  директория `P10EW_R1_PARSE_RUNS`. Никакого new M2/3D/FEM, 02 и
  расходования one-shot marker в этом пакете.

Отрицательный Linux guard тоже проверен. **Нативный Windows parse P10EW
пока не выполнялся**: вероятное устранение lexer STOP не означает
подтверждённого `P10EW_NATIVE_PARSE2_PASS_NO_M2_NO_FEM`.

## 5. Единственный следующий шаг

Исследователь распаковывает **новый** P10EW ZIP в отдельный каталог,
запускает **только** `01_P10EW_SAFE_PARSE_ONLY.cmd` и присылает
**один `P10EW_EVIDENCE.zip`**, при PASS или STOP.
Не запускать старый P10EV 02 или внутренние старые CMD.
Только после независимой проверки реального Windows pass будет
возможна отдельная новая версия guarded one-shot mesh-only M2.
Перед физикой — реальный 343→729QP D-025 ГО на обоих полюсах и
отдельное решение исследователя. **Нет новой M2 и нет FEM.**
