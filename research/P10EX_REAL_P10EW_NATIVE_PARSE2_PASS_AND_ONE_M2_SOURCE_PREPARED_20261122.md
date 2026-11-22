# P10EX — реальная P10EW native parse2 PASS, подготовлена одна C¹ M2 mesh-only попытка (22.11.2026)

## 1. Новое независимое доказательство — реальная Windows Gmsh4.15.2

Исследователь передал приватный оригинальный `P10EW_EVIDENCE.zip`,
**7454 байта**, SHA256
`ca9a6dcd0127a6c7a3aeeef21e822b0674c58a2886c4671a9fe5d49351c79821`;
CRC10/10. Источник не публикуется в GitHub.
`scripts/p10ex_audit_p10ew_real_parse_pass.py` повторно прочитал
сам оригинал, проверил CRC/10 имён, исходники GEO, SHA manifest,
независимый исходниковый StrCat proof, оба native logs/result:

- `P10EW_NATIVE_PARSE2_PASS_NO_M2_NO_FEM`, режим `SAFE_NATIVE_GEO_PARSE_ONLY`.
- Оригинальный Field2 M1 GEO: `A_ORIGINAL_M1_FIELD2` — **PASS**.
- Новый Field6 C¹ StrCat GEO: `B_EXACT_INLINE_F6` — **PASS**;
  оба genuine Windows Gmsh4.15.2 `-parse_and_exit` с native logs,
  ни одной `Error`; старый lexer `String too long` устранён.
- Исходная M1 SHA256
  `ca6b6b6588dc72c5dd3ed2e92e24794560ee2407e350c8a44858e9c3c7d0360f`,
  CAD SHA8029a6ed..., Gmsh EXE SHA317c4339..., итоговый GEO SHA
  **`d68570270dfb5ca2232d8fc94486e5638223b3604c933312b4036d5bb8d19b72`**.
- В GEO семь [600,600,600,600,600,600,598] литералов,
  воссоздающих точно прежние 4198 символов единой MathEval формулы.
  Физическое C¹ поле κ/α/β, smooth joins и размерные соглашения прежние.
- `native_3d_attempts=0`, `FEM_attempts=0`, нет `M2_SHA256`;
  новый M2 **не существует**. Ранее явно согласованная одна Gmsh -3
  попытка не расходовалась.

Публичный source-only derived результат:
`research/evidence/P10EX_P10EW_REAL_PARSE_PASS_20261122/derived/P10EX_P10EW_REAL_WINDOWS_PARSE_AUDIT.json`,
`P10EX_REAL_P10EW_NATIVE_PARSE2_AUDIT_PASS`.

**Уровень вывода:** доказан реальный native GEO parser PASS для
исправленного источника. Это не означает прохождения native -3,
quality gate или объёмного D-025; прежние P10EK/P10EN реальные M2
остаются геометрическими D-025 STOP.

## 2. P10EX: новая защищённая редакция one-shot из прежнего разрешения

В P10EV пользователь уже разрешил ровно **одну новую** M2 native -3
для единого P10EU C¹ поля. P10EV остановился ещё на parse; P10EW
прошёл parse, не запускал -3. P10EX продолжает **ровно ту же**
разрешённую одну mesh-only попытку с математически идентичным полем,
но в новой защищённой неизменяемой редакции. Ни один старый
P10EV/P10EW/P10EN/P10EA one-shot marker не удаляется и не переименовывается.

Источники: `research/proposals/P10EX_STRCAT_M2_WINDOWS_20261122/`,
конструктор `scripts/p10ex_build_one_strcat_m2_bundle.py`. Точный
предыдущий P10EW R1 ZIP SHA
`a375bff007a6ce4c04e3590877359e870f9044e0bc385a8d26f3bebf1415b968`
вложен в `P10EW_PINNED_PARENT` (51 файл), включая точный
P10EV historical parent и все SHA/QA dependencies.

Новый выпуск:

- `research/packages/P10EX_R1_ONE_C1_STRCAT_M2_3D_WINDOWS_20261122.zip`;
- **129786 байт**, **SHA-256
  `84a0570cfc61a4fcd3084e5eed3d5926ad6cce88e2dad81a769d8ee92039ba70`**;
- ZIP CRC58/58, шестёрка новых root files с отдельным SHA-pin, один
  независимый `P10EX_R1_SOURCE_SHA256.json`.
- Распакованный isolated `--selftest` PASS: все унаследованные SHA,
  оригинальная M1, curved27QP unit, собственные P10EX new markers,
  повторная попытка маркера STOP без изменения первого.
- Распакованный Linux `--preflight-only` STOP до нативного Gmsh,
  `--one-m2` без fresh proof STOP до native, подмена нового GEO даёт
  `missing or modified pinned source` STOP.
- **Native Gmsh3D=0, M2=0, FEM=0 на подготовке**.

## 3. Две новые корневые кнопки и guard

Только в новой папке **вне `G:\ildar\Stage3D07`**:

1. `01_P10EX_SAFE_PREFLIGHT_ONLY.cmd` — source SHA/оригинальная M1 SHA,
   Gmsh4.15.2 EXE SHA, 17075 исходных sample и curved QP unit,
   реальный native парсер исходного Field2 и исправленного StrCat Field6,
   M1-label; 24h proof только при полном PASS, без -3/marker/FEM.
2. `02_P10EX_ONE_M2_3D_ONLY.cmd` — только при полном 01 PASS,
   fresh proof ≤24 ч, повторном source/native/M1 preflight, точной
   ручной фразе **`RUN ONE P10EX M2 3D MESH`**. Затем **ровно один**
   native Gmsh `-3 -nt 2 -format msh2`. Новые уникальные P10EX
   local и Windows-profile markers создаются навсегда **перед** native.
   STOP, crash, timeout после markers также расходуют разрешённую
   попытку. Никогда не повторять 02 и не удалять markers.

Пределы: wall900s на native mesh, private polled8GiB, MSH750MiB,
Gmsh log16MiB, самостоятельный geometry QA300s; все лимиты
предоставлены из уже проверенного P10EA/P10EV code, не увеличение.
На Windows i7-7700K при ~10k Tet10 ожидаются минуты, гарантируется
только watchdog ≤15 минут 3D+≤5 минут QA, память не более
опрашиваемого private 8GiB. Qt Creator/CMake/FEM не используются.

Geometry pass старого curved27QP M1/M2 без folded/issues даёт
**`P10EX_M2_GEOMETRY_PASS_D025_PENDING_NO_FEM`**, не D-025 GO.
Старые девять P10EA зон с α0.20 **не применимы** к C¹ StrCat target.
При новом raw M2 ≤32 МиБ `P10EX_EVIDENCE.zip` включает
`RAW/P10EA_M2_CANDIDATE.msh` с SHA и native/QA/log; иначе raw
остаётся приватным на Windows и о необходимости его передачи
решается отдельно. В Git не публиковать raw, H0, forward/adjoint.

## 4. Научный следующий контроль перед FEM

Отдельно независимо оценить криволинейные Tet10 27QP/343→729QP,
проверить M1/M2 геометрический интегральный объём и **реальные**
fixed3D north/south характерные
\(V_{\mathrm{eff}}(M2)/V_{\mathrm{eff}}(M1)\in[0.75,0.85]\)
на обеих полярных шапках при κ1; при κ0 локальные размеры
стремимся сохранить; плавность обязательна, без искусственной
φ-равномерности и общего N+25% cap. Площадь Tri6 диагностическая.
При D-025 STOP нельзя запускать FEM, старую -3 не повторять.
Даже D-025 GO потребует отдельного согласия на полный физический
forward+adjoint одной принятой M2.

**Следующий один шаг исследователя:** распаковать P10EX в новую папку,
01 PASS, затем один 02 с точной ручной фразой; при PASS/STOP
передать один оригинальный `P10EX_EVIDENCE.zip`.
