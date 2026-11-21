# P10DH — P10DG R1 Windows остановлен до Gmsh: отсутствует ручное подтверждение

**21.11.2026. Фактический статус: PREFLIGHT PASS; MANUAL CONFIRMATION STOP; M1 Gmsh NOT STARTED; M1.msh НЕ СОЗДАНА; FEM=0.** Это **не** геометрический провал поля P10DF и не завершённый опыт M1. Цель научного протокола D-018D остаётся прежней: M0=историческая H0; M1 — сгущение типичного объёма по всей области приблизительно на 20%, без физико-зависимых индикаторов до физических M0/M1.

## 1. Входные свидетельства и независимая проверка

Исследователь передал **оригинальный** `P10DG_EVIDENCE.zip`: **2408 байт**, SHA-256 **`55af9103f2cae7a2d99a1fded640068ec69833d79482bd81adec4b27428a33f0`**, ZIP CRC **3/3 PASS**; три файла `P10DG_RUN_MANIFEST.json`, `P10DG_RESULT.txt`, `P10DG_STOP_TRACE.txt`. Архив сохранён без изменений в `research/evidence/P10DH_P10DG_PRELAUNCH_STOP_20261121/input/`. Источник запуска — опубликованный неизменённый P10DG R1 ZIP SHA **`4c5f3712931f7de5bfe0b9e1734aa37ed4d1b72c6553f7828fdd56808bce6a82`**, CRC13/13, pinned source SHA12/12. Самостоятельный verifier `scripts/p10dh_verify_p10dg_prelaunch_stop.py` проверил оригинальные SHA, CRC, 12 пакетных файлов, внутреннюю согласованность manifest/result/trace, статический порядок подтверждения → launch/marker и четыре негативных изменения manifest (FEM/status/reason/native exit) — **PASS**. Машинный итог в `research/evidence/P10DH_P10DG_PRELAUNCH_STOP_20261121/derived/P10DH_P10DG_PRELAUNCH_AUDIT.json`.

Факты Windows manifest, проверенные на согласованность:

| Параметр | Установленный результат |
|---|---|
| UTC start → finish | 11:51:32.805044 → 11:51:45.096545; **12.291501 с** |
| Историческая H0 | найден `G:\ildar\Stage3D07\meshes\H0.msh`, SHA `e28d6049afc4b20b474152d315952361b01dce7052f7642d03a20ce8274d41f8` |
| Windows Gmsh | EXE найден, `-version`=**4.15.2**, **только preflight**, настоящего `-3` не было |
| Available RAM / free disk перед запуском | 58,063,900,672 байта (~54.08 GiB) / 8,020,930,568,192 байта (~7.29 TiB) |
| Synthetic QA | пять перечисленных unit-tests, включая folded curved 27QP и radial over/under negative, **PASS по manifest** |
| Отказ | `P10DG_STOP: manual one-shot phrase not confirmed` |
| Native Gmsh mesh / geometry QA | **не запускались**, exit codes отсутствуют |
| M1 Tet10 / Tri6 / качество / median-volume ratio | **UNKNOWN**, не вычислялись |
| Физические расчёты | **0** |

Traceback указывает на `P10DG_one_click_m1.py` строка 215: `require(answer == CONFIRM, "manual one-shot phrase not confirmed")`. По исходному коду marker `P10DG_RUNS\P10DG_ONE_SHOT_USED.json` создаётся **позже**, только внутри `launch()` непосредственно до `subprocess.Popen(gmsh)`. Следовательно, в **данном исполнении** одноразовый marker не записывался, а Gmsh не запускался. Саму Windows файловую систему удалённо мы не проверяли; наличие marker от какого-либо **другого** исполнения нельзя исключить только по присланному ZIP. В manifest нет ни `exact_gmsh_argv`, ни `native_exit_code`, ни `m1_mesh_sha256`, ни `qa_exit_code`. **Preflight PASS не равен mesh geometry PASS.**

## 2. Безопасное продолжение той же санкции

Один ранее разрешённый **Gmsh mesh-only опыт P10DG ещё НЕ израсходован**: ручная проверка не пустила исполнение к Gmsh. **Новая версия пакета и новая калибровка не нужны.** Исследователь на своём Windows ПК:

1. **Не удаляя** предыдущий каталог `P10DG_RUNS\P10DG_M1_...` с STOP/evidence, проверяет, что в корне распакованного пакета **нет** `P10DG_RUNS\P10DG_ONE_SHOT_USED.json`. Если marker существует, **STOP, не удалять marker, не повторять**: прислать его содержимое/сведения.
2. В **той же** уже распакованной папке P10DG запускает `01_RUN_P10DG_M1_MESH_ONLY.cmd`. После `P10DG PREFLIGHT PASS` ожидает точный prompt `Введите ровно RUN ONE P10DG M1 MESH:`.
3. Вводит **в точности** латинскими символами, без кавычек, включая пробелы: `RUN ONE P10DG M1 MESH`; затем Enter. **Только Enter** либо иная фраза гарантированно дадут prelaunch STOP, без Gmsh.
4. Ожидает один Gmsh4.15.2 + отдельно full curved27QP/global/radial geometry QA. Предохранители: 900 с на Gmsh, 8 GiB private, 750 MiB MSH и затем 300 с QA; фактическое время M1 ещё не измерено. Никакого M1 FEM запускать не нужно.
5. Передаёт **только новый** `P10DG_EVIDENCE.zip` из **наиболее свежей** папки `P10DG_RUNS\P10DG_M1_...`, а не уже полученный архив prelaunch STOP. Полная `.msh` остаётся на компьютере.

Ни повтор P10DE Gmsh, ни M2 adaptive, ни физический M1 этим шагом не разрешены. После **реального** нового свидетельства нужно отдельно оценить M1 global ratio 0.65–0.95, радальные ratio 0.55–1.15 в populated bands, curved 27QP и прочие геометрические ограничения; при последующем настоящем geometry STOP автоматического повторного meshing не будет.

## 3. Границы выводов

Здесь **нет новых научных данных о пространственной дискретизации или производных**: P10DD H0 signed mechanical/thermal `(r,θ,φ,t)` остаётся последним принятым **физическим** baseline. Невозможно оценить число M1 элементов, реальное снижение объёма или сходимость M0/M1, поскольку Gmsh-меширование не произошло. Дальнейшая научная последовательность остаётся: одна реальная mesh-only M1 → QA → отдельно разрешённый полный физический M1 → только после M0/M1 выбор адаптивной M2.
