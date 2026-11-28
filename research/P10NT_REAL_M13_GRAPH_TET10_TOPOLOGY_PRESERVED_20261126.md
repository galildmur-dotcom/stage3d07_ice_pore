# P10NT — реальное Windows Gmsh4.15.2: полное соответствие объёмной топологии M13 (26.11.2026)

**Статус: P10NT_VOLUME_VERTEX_TOPOLOGY_PASS; D031_CANONICAL_QUALITY_PENDING; M13_NOT_ACCEPTED; FEM0/M13R3=0.**

## Первичные входы

Исследователь передал `P10NT_VOLUME_GRAPH_CORRESPONDENCE_RESULT.json` и `P10NT_GMSH_GRAPH_LOG.txt`. SHA256 закреплённой M13 R2 `57403ba43fa299417d519046cebdf50fa4968b670c071a8b7882748b50f51e9c`; JSON status `AUDIT_COMPLETED_NO_R3_NO_FEM`, Gmsh HighOrderElastic in-memory optimizer2.7097068s, FEM0, mesh generation0, mesh_written0, markers0. Синтетический graph fixture PASS. Первичные user-файлы хранятся отдельно, публично публикуются только derived findings.

## Графовые доказательства

Строгая координатная биекция неизменных boundary corner nodes дала 1262 уникальные anchors. У 3509 corner vertices WL graph refinement показал совпадение гистограмм цветов before/after на каждом раунде. Round0 unique1264 / unresolved2245; round1 unique3497 / unresolved12; round2 unique3509 / unresolved0. Итог `UNIQUE_GRAPH_LABEL_BIJECTION` на всех 3509 vertex nodes.

По установленной биекции:
- `tet_count_before=tet_count_after=matched_tet_vertex_sets=18004`;
- missing-after0 / extra-after0;
- `edge_association_mismatch_tets=0`;
- `verified_vertex_topology_preserved=true`;
- граничные Tri6 `boundary_tri6_preserved=true`.

Это подтверждает полную сохранность **проверенной комбинаторной топологии 18004 Tet10**, включая соответствия 6 edge-midside positions на уровне каждого элемента. Не утверждается, что координаты внутренних вершин/криволинейные объёмы неизменны; наоборот оптимизатор переместил их.

## Перемещения

Для соответствующих corner vertices: median0.0076151811mm, p95 0.0367776532mm, max0.0783734425mm. Для 108024 вхождений midside nodes: p95 0.0417041405mm, max0.0965342014mm; boundary moved midside occurrences 0. Реальный boundary geometry P10NR/P10NS preserved. Значения midside относятся к **вхождениям** в тетраэдральные рёбра, не к уникальным node count.

## Обобщение evidence chain

P10NQ point cloud Hausdorff0 on boundary; P10NR all 2512 boundary Tri6 preserved; P10NS R2 corrected analytic 27/343/729 sampled detJ positive everywhere on all 18004 Tet10, min 729 QP 1.652187534e−13 → 1.744919075e−13 (~+5.61%); P10NT exact combinatorial vertex-topology and edge association preserved. Native Gmsh logs quality estimate worst distortion0.281159→0.641825 (metric is separate from sampled minDetJ).

**Не объявлять D-031 geometry GO:** независимая canonical Gmsh оценка minSJ/minSICN/gamma, полярные worst-elements и детальное QA сохраняются отдельным следующим этапом P10NU, только in-memory Gmsh quality; никакой M13 R3/FEM автоматически. После завершения D-031 отдельный M13 acceptance passport и решение о дальнейших действиях.
