# P10EB — оригинальный Windows P10EA R1 safe preflight прошёл, M2 3D ещё не запускалась

**Дата:** 22.11.2026. **Статус доказательства:** независимая проверка оригинального Windows evidence и двух реальных native Gmsh4.15.2 GEO parse logs, source SHA/GEO и меток оригинальной принятой M1. Это не построение M2, не FEM, не проверка пространственной сходимости.

## 1. Оригинал и непрерывность воспроизводимости

Исследователь передал единственный первичный P10EA_EVIDENCE.zip, **SHA-256 36d90b7c583614317c770f66d51c8729c57a4eb5f059fefdbac37b838e5d5ee3**, ZIP **8/8 CRC**, без изменений сохранён в research/evidence/P10EB_P10EA_REAL_SAFE_PREFLIGHT_PASS_20261122/input/P10EA_EVIDENCE.zip. Релиз подготовки P10EA R1 research/packages/P10EA_R1_M2_EXACT_INLINE_F6_ONE_3D_MESH_ONLY_WINDOWS_20261122.zip SHA256 **8b1650ae7808b117f5778ca726b2542c9cbc59365a09913128a322713b254009** (24 source entries), неизменён. Независимый аудитор scripts/p10eb_audit_p10ea_windows_preflight.py сводит ZIP/JSON/RESULT/GEO/Gmsh logs/коэффициенты и отвергает 8/8 намеренных in-memory подмен.

Оригинальный Windows manifest: revision P10EA_R1_EXACT_INLINE_F6_ONE_M2_3D_MESH_ONLY, status **P10EA_SAFE_PREFLIGHT_PASS_NO_M2_NO_FEM**, mode SOURCE_ONLY_PREFLIGHT, run P10EA_20261122_042904_271811; начало UTC04:29:04.271971, конец04:29:15.665431, суммарная длительность **11.39346с**. Source gate сообщает pin23/23, независимо подтверждённая исходная формула математики sample17 075. До запуска parse Windows wrapper сверил:

- **Только ORIGINAL принятую P10DG M1** с basename P10DG_M1_CANDIDATE.msh и SHA256 **ca6b6b6588dc72c5dd3ed2e92e24794560ee2407e350c8a44858e9c3c7d0360f**; не H0/U0/новая M1. Бинарник M1 не включён в ZIP, поэтому независимый локальный пересчёт его SHA невозможен — здесь проверена запись Windows wrapper и согласованность source control flow.
- Native Gmsh4.15.2 EXE SHA256 **317c43391e5b1fab3a1dd80dc5245dad6e2d087910f4b8ebc234bd6d4b8f41a1** по Windows wrapper; raw EXE на машине аудитора отсутствует.
- Windows preflight available RAM **58 514 984 960B (~54.49GiB)**, free disk **8 020 674 437 120B (~7.29TiB)** — прежние gates ≥16GiB/≥4GiB пройдены. Ограничения будущей *возможной* одной -3 попытки: wall900с, polled private8GiB, msh750MiB, log16MiB, 2 threads, QA отдельно300с. Фактического потребления этой памяти/диска M2 нет.

## 2. Два настоящих native Gmsh GEO разбора

| Проверка | Исходный GEO SHA256 | Native Gmsh4.15.2 | Статус |
|---|---|---:|---|
| A — original M1 Threshold Field2 | c6ec88a3fe91db0f3c369391a91aefbd1bc83f1d3033b38a985c3033c605ddd8 | 0.0253639с | Разобрана CAD, Done reading, Stopped, no Error |
| B — **полное** inline F6 κ20, ссылка только на F2 | 32f8f959002cbd41539e355a80437c2ca3be12fdd3ba12de31eadf2c021b9561 | 0.0208628с | Разобрана CAD, Done reading, Stopped, no Error |

Оба LOG содержат ровно один аргумент **-parse_and_exit** и никакого -1/-2/-3 или записи msh, оба независимо соответствуют исходным GEO A/B и **CAD GEO SHA256 8029a6ed22bcf312701cd6abc46bbe5575e52df16fd5218dd936b01d5cd6fcf0**. Историческая Windows CRLF ошибка P10DW R1 не повторилась: оригинальные GENERATED B и CAD совпадают побайтно с pinned release. Следовательно подтверждён синтаксический/геометрический native preflight исходника, но **не** вычисление поля при объёмном remeshing.

## 3. Полная разметка оригинальной M1 и научный предел коэффициента

Оригинальный P10EA_M1_LABEL_SUMMARY.json содержит M1 **14145 nodes, 9736 Tet10, 178 pore Tri6**, весь Tet10 set промаркирован при линейных центроидах:

| Значение κ на центроиде Tet10 | Число Tet10 | Доля от 9736 |
|---|---:|---:|
| κ=0, сгущение по целевому полю не требуется | 9477 | 97.34% |
| 0<κ<1, плавный переход | 238 | 2.44% |
| κ=1, максимальное целевое сгущение | 21 | 0.22% |
| **Итого** | **9736** | **100%** |

Mean κ по центроидам **0.0118780454080**, описывает распределение по числу M1 Tet10, **не** долю физического объёма и не будущую глобальную относительную экономию. В целевой размерной функции 0≤κ≤1, **Vtarget_M2/Vtarget_M1=1−0.20κ∈[0.8,1]**, h2/h1 min0.9283177667. Ни один из 9736 M1 Tet10 не «не размечен»: κ=0 — легитимный приоритет. Точки у обоих полюсов получают больший приоритет в компактной radial×|μ| карте; это гипотеза физического сгущения после H0/M1, а не доказанный механизм приполюсной разницы D_R jpeak.

Числа отражают **проверенный интерфейс P10DN source-only маркировки** оригинальной M1, но не точечные вычисления фонового поля при Gmsh -3, не curved volume M2 и не фактически выполненные −0…20% на M2.

## 4. Независимый контроль и запреты

Аудитор scripts/p10eb_audit_p10ea_windows_preflight.py:

1. Проверяет оригинальный ZIP SHA, CRC8/8, точный набор восьми файлов и SHA24-member release P10EA.
2. Восстанавливает baseline Field2 из неизменного P10DN GEO, сравнивает byte-exact A/B/CAD с оригинальной поставкой, пересчитывает три GEO SHA.
3. Проверяет обоих native Gmsh CLI, чтение CAD/Done reading/Stopped/Wall, отсутствие Error или попыток mesh, согласованность manifest/RESULT и ресурсов.
4. Проверяет точные M1 count/label и κ/size target envelope.
5. Отвергает **8/8** намеренных в памяти подмен: F6 GEO, baseline GEO, M1 SHA, фиктивную native 3D, подложную запись parse success, замену -parse_and_exit на -3, удаление Done reading, испорченный счётчик κ.

Derived JSON research/evidence/P10EB_P10EA_REAL_SAFE_PREFLIGHT_PASS_20261122/derived/P10EB_P10EA_ORIGINAL_PREFLIGHT_AUDIT.json, SHA256 **d362a0db36179cfdbc2497252ec4a95caf0949b2473ed64bcfdd129a0d2e88f0**, статус **P10EB_ORIGINAL_P10EA_NATIVE_GEO_PARSE2_AND_M1_LABEL_PASS_NO_M2_NO_FEM**. Нативных Gmsh запусков на машине аудитора не делалось.

В оригинальном preflight manifest **native_1d_2d_attempts=0, native_3d_attempts=0, physical_FEM_attempts=0**. Это гарантирует лишь поведение *этого* preflight; **физические маркеры на Windows не предоставлены и непосредственно не проверены**. По опубликованному source кнопка01 не создаёт P10EA one-shot markers. Повторять consumed P10DO/P10DW или удалять старые markers нельзя.

## 5. Единственный следующий научный рубеж

**P10EB safe source/geometry gate PASS.** Теперь можно **предложить исследователю отдельную санкцию** на **один** bounded Windows Gmsh M2 -3 mesh-only P10EA R1 из **той же распакованной папки** при выполненном ≤24ч proof (после истечения 24ч безопасную кнопку01 надо выполнить заново), новой ручной фразе RUN ONE P10EA M2 3D MESH и прежних 900с/8GiB polled/750MiB/16MiB/2 threads плюс QA≤300с. Создание P10EA one-shot markers происходит непосредственно перед будущей native командой, поэтому попытка необратимо расходуется даже при timeout или QA STOP. Самая сильная проверка после будущего 3D — **full curved27QP всех Tet10, pore/CAD, quality, объёмы M1/M2 в 3×3 radial×|μ| зонах**, включая интегрированные curved объёмы; только после анализа можно обсуждать отдельный physical FEM M2.

**На этой стадии кнопку02 запускать НЕ РАЗРЕШЕНО**: в сообщении исследователя имеется только ZIP без прямого разрешения на новый native -3. Нового кода/пакета, увеличения resource cap или изменения целевого κ сейчас не требуется.
