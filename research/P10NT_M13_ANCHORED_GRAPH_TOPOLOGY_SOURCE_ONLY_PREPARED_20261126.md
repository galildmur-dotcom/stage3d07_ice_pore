# P10NT — source-only графовое соответствие Tet10 M13 (26.11.2026)

## Статус

`SOURCE_ONLY_PREPARED, GMSH_NATIVE0, FEM0, M13_R3_0`. Изготовлен отдельный автономный Windows ZIP `P10NT_M13_TET10_GRAPH_TOPOLOGY_WINDOWS_20261126.zip` (7 файлов, ~1.25 MB, CRC7/7). Содержит точную `P10NA_M13_R2_CANDIDATE_UNVERIFIED.msh` SHA256 `57403ba43fa299417d519046cebdf50fa4968b670c071a8b7882748b50f51e9c`, Python modules P10NQ/P10NR/P10NS R2, новый `p10nt_topology_graph_audit.py`, CMD+README. Пакет распаковывается в новую папку, запускается одной `01_P10NT_RUN_GRAPH_TOPOLOGY.cmd` без PowerShell, текстовых команд и интерактивных подтверждений. Ресурсное исполнение Gmsh на Windows пока **не проводилось**.

## Научный мотив

P10NS R2: 18 004 Tet10 curved determinant sampled на 27/343/729 QPs positive0; minDetJ improved ~5.61%, boundary Tri6 preserved. При этом только 1262/3509 corner vertices совпали точными координатами, directed nearest cloud Hausdorff 0.0783734 мм. Точная coordinate-bijection для внутреннего узла 5031 отсутствует; P10NS не установил volume topology. Ближайшая точка сама по себе не доказывает идентичность вершины.

## P10NT алгоритм

1. Загрузить точную исходную M13 R2 в Gmsh4.15.2, взять before snapshot, выполнить строго **in memory** `HighOrderElastic` (никакой записи новой mesh/one-shot/FEM), взять after snapshot.
2. Сопоставить boundary corner vertices по проверенным P10NR координатам с допуском 1e−12m; каждой паре выдать индивидуальную якорную метку, независимую от node IDs.
3. Построить угловой граф Tet10 (6 неориентированных рёбер каждого тетраэдра), degree и число инцидентных Tet10. Для внутренних узлов начальная метка degree/incident, для граничных уникальная anchor.
4. До 12 детерминированных раундов WL-тип уточнения цветов по мультимножеству цветов соседей; SHA256 от сортированных меток, в каждом раунде сверять кратности цветов before/after.
5. Если **каждый** corner vertex получил единственный matching color на обеих сторонах, построить полную биекцию и сравнить для всех 18 004 Tet10 мультимножества четырёх mapped corner nodes (без element IDs); проверить шесть edge-midpoint correspondences и распределения реальных перемещений. Если цвета неоднозначны или кратности нарушены, честно `INDETERMINATE`/`COLOR_MULTIPLICITY_MISMATCH`; не выдумывать биекцию и не выдавать topology GO.

## QA

Python selftest `P10NT_SYNTHETIC_GRAPH_BIJECTION_PASS`: две Tet10 vertex-four subsets, один перемещённый внутренний угол и новая полная перенумерация, unique anchored graph bijection recovered; negative test missing corner vertex rejected. ZIP CRC7/7 PASS, exact raw mesh SHA pinned by code. Настоящих Gmsh Windows графовых данных **ещё нет**, full topology not claimed.

Пользователь возвращает `P10NT_VOLUME_GRAPH_CORRESPONDENCE_RESULT.json` и `P10NT_GMSH_GRAPH_LOG.txt`. P10NT не принимает M13; canonical D-031 minSJ/minSICN/gamma ещё отдельно требуется.
