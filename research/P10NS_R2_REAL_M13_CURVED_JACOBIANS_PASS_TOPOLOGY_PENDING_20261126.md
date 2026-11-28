# P10NS R2 — реальная Windows проверка M13 R2 после HighOrderElastic (26.11.2026)

**Статус: CURVED_TET10_SAMPLED_JACOBIAN_PASS / BOUNDARY_TRI6_PASS / VOLUME_TOPOLOGY_INDETERMINATE. FEM0, M13 R3 не создавался.**

## Первичные свидетельства

Исследователь передал оригинальные `P10NS_VOLUME_TOPOLOGY_QUALITY_RESULT(2).json` и `P10NS_R2_GMSH_VOLUME_LOG.txt`; предыдущие `(1)` и исходный без суффикса — R1 AUDIT_ERROR, их отрицательные detJ неверны (порядок 2 midside). R2 source SHA M13 R2 `57403ba43fa299417d519046cebdf50fa4968b670c071a8b7882748b50f51e9c`. Native Gmsh4.15.2 source preflight PASS, injected synthetic PASS, `AUDIT_COMPLETED_NO_R3_NO_FEM`, optimizer wall2.6635277s; mesh_generation0, files_written0, FEM0, markers0. Оригинальные файлы не публикуются.

## Криволинейная геометрия на точных 18 004 Tet10

| QP на элемент | QP суммарно | minDetJ до, m³ | minDetJ после, m³ | Nonpositive до/после |
|---:|---:|---:|---:|---:|
| 27 | 486108 | 1.6528481910907702e-13 | 1.7454418527263308e-13 | 0/0 |
| 343 | 6175372 | 1.6522055662689716e-13 | 1.7449421327038182e-13 | 0/0 |
| 729 | 13124916 | 1.6521875341449308e-13 | 1.7449190754792124e-13 | 0/0 |

Плотнейшая квадратура: рост minDetJ ~5.61%. Gmsh native `Volume mesh: worst distortion=0.281159` → `Final volume mesh: worst distortion=0.641825`. Это разные метрики, нельзя приравнивать их и выводить D-031 acceptance из sampled detJ. Все boundary Tri6 снова preserved TRUE.

## Внутренние угловые вершины и нерешённый вопрос

Всего 3509 corner vertices до и после; nearest-coordinate exact match 1262 (<1e−12m), у 2247 нет точной координатной пары. Directed corner-cloud Hausdorff в обе стороны `0.07837344249249029 мм`; p95 nearest `0.036777653158933464 мм`. **Это расстояния до ближайшего узла, а не доказанное перемещение каждого соответствующего узла.** Точный corner bijection недоступен: `nonunique coordinate match: old node 5031, candidates 0`. `volume_topology_status=NOT_PROVEN_NO_ASSUMED_CORNER_BIJECTION`, status `INDETERMINATE`; не делать вывода «топология изменена» или «топология сохранена».

## Диспозиция и следующий этап

P10NS R2 sampled geometry PASS, M13 **НЕ ПРИНЯТА**. Следующий новый научный вопрос: восстановить corner vertex bijection **по комбинаторному графу Tet10 с неизменными boundary vertices как якорями**, сверить все 18004 vertex tetrahedra и затем edge-midside incidence независимо от перемещения внутренних координат. Нельзя принуждать nearest spatial map к однозначности, если она не доказана. Сначала source-only/synthetic graph correspondence и ограниченный in-memory native Windows diagnostic без FEM, без генерации M13 R3. Только после этого отдельно canonical Gmsh D-031 minSJ/minSICN/gamma и окончательное geometry GO/STOP.
