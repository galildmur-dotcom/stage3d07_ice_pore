# P10EG — авторизованный защищённый P10EF R2 one-shot Gmsh 2D: исходники подготовлены; native запуск ещё не наблюдался

**22.11.2026. Состояние: SOURCE-ONLY BUILT/PASS, WINDOWS NATIVE MESH PENDING; Gmsh -2 attempts by assistant = 0; new -3 = 0; physical FEM = 0.** Запись исследователя «разрешаю» относится только к заранее предложенному **одному** новому native Gmsh 4.15.2 `-2` для B 2D Delaunay(5), с preflight и ручной фразой. Не санкционирована ещё одна 3D M2, FEM или восстановление старой P10EA -3 попытки.

## Цель научного эксперимента

Разделить механизмы 2D поверхности и 3D объёма, не изменяя постановки F6/κ/CAD: измерить, улучшает ли алгоритм Delaunay2D(5) локальную Tri6/QP-эффективную площадь полярных шапок по сравнению с уже выполненным Frontal-Delaunay(6), для которого историческая P10EA M2 дала M2/M1 север1.076960/юг1.038407/оба1.057067 вместо целевого 0.8^(2/3)=0.861773876. Это тест алгоритма, **не новой физической M2** и не доказательство игнорирования F6. Числовой GO-критерий к последующей 3D ветке не утверждён; после evidence будет отдельная научная оценка.

Источник 2D контроль A — SHA `32f8f959002cbd41539e355a80437c2ca3be12fdd3ba12de31eadf2c021b9561`, кандидат B — SHA `2765018d8ddd2e83f28bd60af7c87b65172ac5da8389ede187d8bb9eea9d74c5`; отличается одна строка `Mesh.Algorithm = 5;`. CAD SHA `8029a6ed22bcf312701cd6abc46bbe5575e52df16fd5218dd936b01d5cd6fcf0`. Original M1 SHA `ca6b6b6588dc72c5dd3ed2e92e24794560ee2407e350c8a44858e9c3c7d0360f`; historical M2 SHA `ba1f1a0553a568c1b399acadd52bce1c1dc32e8d1c6b3ab1ce6759c547e5dee5`. Gmsh4.15.2 EXE SHA `317c43391e5b1fab3a1dd80dc5245dad6e2d087910f4b8ebc234bd6d4b8f41a1`.

## Отдельный воспроизводимый Windows пакет

`research/packages/P10EF_R2_ONE_2D_SURFACE_GMSH_ONLY_WINDOWS_20261122.zip`, **19253 байта, SHA256 `414a288d7ef61f015bc9a1419ac75b5160c02db09951d8ca38b358d5f9fb0c7d`**, 10 отдельных файлов, CRC10/10, exact SHA PIN9/9. Не заменяет R1 source-only ZIP 8982Б и не включает raw M1/M2. Точные байты original P10EF R1 ZIP SHA `7f4910c4...` и P10EA parent ZIP SHA `8b1650ae...` проверены builder'ом. Внутри только две видимые Windows кнопки:

- `01_P10EF_R2_SAFE_PREFLIGHT_ONLY.cmd`: SHA source9, original M1/M2, EXE, geometry, native `-parse_and_exit` A и B (это **не построение 2D/3D сетки**), ≥4 GiB свободной RAM и ≥1 GiB диска, proof на24ч.
- `02_P10EF_R2_ONE_2D_SURFACE_ONLY.cmd`: обязательный PASS01≤24ч, повторный источник/GEO preflight, точное ручное `RUN ONE P10EF 2D SURFACE`, *две собственные P10EF R2 эксклюзивные постоянные метки сразу перед native -2*, затем ровно один `gmsh B.geo -2 -nt 2 -format msh2 -o ...`.

Защита: стеночное время `≤120s`, опрашиваемый Windows private `≤2 GiB` (не hard OS quota), MSH `≤25 MiB`, полный Gmsh log `≤4 MiB`, 2 threads; последующий Python stdlib read-only curved Tri6 15×15 QP comparison wall≤60s, polled private≤2GiB. Permanent local marker `P10EF_R2_RUNS/P10EF_R2_ONE_2D_USED.json` и profile marker `%LOCALAPPDATA%/Stage3D07/P10EF_R2_ONE_2D_<M1_SHA>.json` никогда не очищать. Даже ошибка 2, native timeout или QA STOP расходуют попытку. Старые P10EA/P10DO/P10DW markers не читаются для обхода и **не изменяются**.

Исходная M1 и историческая M2 только read+SHA, не пересоздаются. 2D output содержит только 1D/2D элементы, **Tet10=0**; read-only QA проверяет physical PORE_WALL=8, curved Tri6, невырожденные Jacobian, 1мм CAD-сферу, полный curved area closure, пространственные зоны север/юг/оба/неполярная через дробное QP количество Tri6. Сравниваются B/M1 и historical M2/M1 с одним и тем же фиксированным `|μ|≥0.8` и target0.861774 без автоматического 3D-GO.

При любом исходе ZIP `P10EF_R2_EVIDENCE.zip` содержит result, manifest, native GEO parse log, Gmsh full/tail, QA/STOP и **оригинальную новую 2D MSH** для независимой верификации. Только приватно передать исходный ZIP; **не публиковать raw 2D** в открытой ветке. Original raw M1/M2 отдельно остаются у исследователя. Не запускать Gmsh A/контроль, `-3`, FEM/forward/adjoint/H0 cache.

## Что реально проверено при публикации

- Репо HEAD перед записью: remote research `cffcee3098b77f0c3dedcb02d64f7c8144b318e6`, remote master `06146080b05c0cfe3dfeca4a9da11b6b13d5c959` — `identical` с проверенными текущими ref на момент preflight публикации.
- Детерминированная source-only сборка `P10EF_R2_build_bundle.py`: ZIP CRC10/10, PIN9/9, isolated Python `--selftest` PASS, изменённая candidate GEO rejected (negative STOP), возвращение оригинальной GEO PASS, на Linux безопасный `--preflight-only` STOP без native, `--one-2d` без proof STOP; исходные R1 P10EF и P10EA release pinned SHA.
- Независимая stdlib Tri6/QP (15²) проверка **имеющихся двух exact raw M1/M2** дала север1.07696010537668, юг1.03840706976670, оба1.05706730782392, воспроизводя отдельно опубликованный numpy P10EE; оригинальные M1/M2 raw не попали в Git.
- Сборка **не выполняла** Gmsh parse, native `-2` или `-3` на Windows; в данной среде Windows EXE/G: недоступны. Native preflight и 2D опыт остаются на ПК исследователя.

**Следующий минимальный шаг:** исследователь скачивает этот R2 ZIP, распаковывает новый каталог, запускает кнопку01, затем после PASS кнопку02 ровно один раз с точной фразой, отправляет **один оригинальный `P10EF_R2_EVIDENCE.zip`** из последнего run. Если STOP до маркеров, сообщить текст/архив — действия согласуем отдельно; если маркеры уже созданы, никогда не повторять 02. После анализа surface B/M1 — только новое независимое решение о целесообразности и разрешении будущей 3D M2 mesh-only; физические запуски по-прежнему запрещены.
