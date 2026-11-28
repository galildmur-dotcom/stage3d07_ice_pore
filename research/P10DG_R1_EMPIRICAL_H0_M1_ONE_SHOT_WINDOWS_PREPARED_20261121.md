# P10DG R1 — одна новая H0-based M1 mesh-only попытка: Windows one-click подготовлен

**21.11.2026. Источник и отрицательные тесты PASS; реальная Windows M1.msh PENDING; FEM=0.** Исследователь ответил **«согласен. построим M1»** после source-only P10DF. Это разрешение на **одну** новую ограниченную попытку Gmsh mesh-only на своём ПК; **не** на физический M1 FEM, автоматические повторные Gmsh или M2 индикаторы. Старый P10DE R1 завершился геометрическим STOP из-за H3-подобного поля, его marker и результат должны оставаться сохранёнными; P10DG — новая независимая редакция/папка/маркер.

## 1. Проверяемая научная гипотеза

M0 — историческая **H0**, 10845 узлов, 7388 Tet10, 136 pore Tri6, exact SHA-256 `e28d6049afc4b20b474152d315952361b01dce7052f7642d03a20ce8274d41f8` (только чтение). На P10DG M1 используется **не** прежний неправильный P10DC near0.17638мм/far3.62044мм, а новый неизменно pinned [P10DF candidate](../gmsh/P10DF_M1_FROM_H0_EMPIRICAL_CALIBRATION_CANDIDATE.geo): near=**0.42855883184652975 мм**, far=**7.0524788853066865 мм**, тот же OCC CAD/B6/9 physical groups, radial Threshold 1.5–18мм, Tet10, Gmsh4.15.2, два потока. Параметры выведены по измеренным геометрическим длинам H0, не являются доказанным оригинальным H0 генератором или предсказанием фактического объёма. Нет полярных/физических индикаторов.

Желаемое `Vtyp(M1)/Vtyp(H0)≈0.8`, `q=0.8^(1/3)`; грубый идеализированный ориентир N≈7388/.8=9235 Tet10 и pore Tri6≈136/q²≈158, **не Gmsh prediction**. Ключевое научное отличие P10DG от P10DE: **относительное сгущение относительно измеренной H0, а не H3** и отдельный radial-local gate.

## 2. Сохранённый исходный пакет

**Новый ZIP:** `research/packages/P10DG_R1_M1_EMPIRICAL_H0_MESH_ONLY_WINDOWS_20261121.zip`; размер **41800 байт**, SHA-256 **`4c5f3712931f7de5bfe0b9e1734aa37ed4d1b72c6553f7828fdd56808bce6a82`**; ZIP CRC **13/13** PASS, исходный pin SHA **12/12** PASS. Сборщик `research/proposals/P10DG_M1_H0_EMPIRICAL_MESH_ONLY_20261121/P10DG_build_bundle.py` создаёт детерминированный ZIP только из данного Git дерева (без сеток, EXE, истории или FEM). Внутри:

- Одна `01_RUN_P10DG_M1_MESH_ONLY.cmd`, `P10DG_one_click_m1.py`, `P10DG_windows_guards.py`;
- pinned P10DF GEO, исходный общий OCC GEO, опубликованный P10DF numeric calibration JSON;
- полный Python auditor P10DE core (MSH2/27QP) + P10DG radial-local gate + три исторические parser/curved QP support modules;
- отдельный `README_RU.md`, `P10DG_PINNED_SHA256.json`.

**Отдельная папка**, например `G:\Downloads\P10DG_R1_M1_EMPIRICAL_H0_MESH_ONLY_WINDOWS_20261121`, не в `G:\ildar\Stage3D07`. Путь к H0 по умолчанию `G:\ildar\Stage3D07\meshes\H0.msh`; Gmsh по умолчанию `C:\gmsh-4.15.2-Windows64\gmsh.exe` (переменные окружения `P10DG_H0_MSH`/`P10DG_GMSH_EXE` при другом расположении). Никаких импортов в Qt Creator и изменений оригинальных source/cache. После source/H0/Gmsh native version SHA/resource/synthetic preflight **ручная точная фраза `RUN ONE P10DG M1 MESH`**; перед первым Gmsh Popen атомарно пишется новый `P10DG_RUNS\P10DG_ONE_SHOT_USED.json`. После его создания повторять команду запрещено.

## 3. Ресурсные и научные STOP-условия

До запуска: ≥16ГиБ available RAM, ≥4ГиБ свободного диска. Монитор Gmsh: **900с wall / 8GiB опрошенной private /750MiB .msh /30MiB full log**; native ExitCode должен быть 0. Отдельный Python QA timeout **300с**. Старый Gmsh P10DE создал ~102k Tet10 за **3.00852с** с пиком0.2633GiB; P10DG предположительно будет более грубым и обычно займёт секунды или десятки секунд, но **прогноз по масштабированию не подтверждён новым запуском**. Ожидание QA — 10–60с, также не измерение. Программный watchdog не физический лимит аппаратной памяти.

Python QA: exact H0 SHA + H0 counts, обе ASCII MSH2.2/tag1–9, curved 27QP/Tet10 для **всех** элементов, corner determinant/quality, CAD curved volume, pore-wall sphere, radial×10 μ bins; общий ratio непарных медиан угловых Tet10 объёмов **0.65–0.95**, count M1>H0; новый additional gate для каждого radial band с ≥100 H0 Tet10: weighted median of 10 μ-bin median volume ratio **0.55–1.15**. Бины с 1 H0 centroid (0–20мкм) не являются надёжной парной оценкой и лишь описываются. Это широкие acceptance guards для **примерно** −20% типичного объёма, не математическая гарантия каждого элемента, не измерение истинной ошибки и не разрешение физического FEM.

Для диагностики любой STOP: отдельные `P10DG_RUN_MANIFEST.json` (source/H0/Gmsh/M1 SHA, native exit, wall/RAM, QA exit), `P10DG_RESULT.txt`, отдельный QA log, `QA/P10DG_H0_M1_MESH_QA.json`, два маленьких radial CSV, Gmsh log tail или traceback. Передать пользователю команду прислать ровно **один `P10DG_EVIDENCE.zip`** из нового `P10DG_RUNS\P10DG_M1_...`; полная M1.msh остается локально, без ее байтов второй независимый расчёт detJ невозможен. При STOP не перезапускать Gmsh, не удалять маркер.

## 4. Что реально проверено в этой среде

`python3 -m py_compile` четырёх новых модулей PASS. `P10DG_build_bundle.py` из отдельно распакованного ZIP запускал `P10DG_one_click_m1.py --selftest`: H0 SHA/source12/12 PASS, старый MSH2 parser + собственные 27QP/Tet10 synthetic и folded negative, новый radial over/under positive/negative **PASS**. **Регрессия по настоящим 140 radial×μ CSV из отвергнутого P10DE evidence**: все **5** достаточно населённых H0 radial bands корректно дают локальный STOP. Отрицательные изменение GEO и calibration JSON → **SHA STOP**. На Linux вызов без `--selftest` → явный `P10DG_STOP_NO_FEM` до marker и любых Gmsh, отдаёт действительный небольшой ZIP; ZIP CRC13/13 PASS, CMD CRLF/no BOM/нативный exit flow PASS.

**НЕТ** настоящего Windows Gmsh4.15.2, H0.msh и исходного физического Windows проекта в этой среде, поэтому **нет** созданной M1.msh, измеренных M1 N/volume/QP/ресурса, thermal/mechanical shape derivative M1 или сходимости. Следующий пользовательский результат — один `P10DG_EVIDENCE.zip` или STOP, затем независимое исследование реальной сетки. **Если геометрия принята, физический полный signed `(r,θ,φ,t)` R/EDV_VAR/jpeak M1 FEM санкционируется отдельно.** Адаптация M2 только по паре M0/M1 физики, никаких индикаторов M1.
