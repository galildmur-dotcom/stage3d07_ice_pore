# P10NU — M13 canonical Gmsh D-031 quality Windows preflight prepared (26.11.2026)

**STATUS: SOURCE_ONLY_PREPARED; GMSH_NATIVE0; M13R3_0; FEM0.**

Доказательная база: P10NQ boundary point clouds preserved; P10NR 2512 boundary Tri6 preserved; P10NS R2 source/after curved positive detJ on all 18004 Tet10 sampled 27/343/729 (min729 1.6521875e−13→1.7449191e−13, +5.61%); P10NT 1262 boundary graph anchors, 3509/3509 unique graph vertex bijection, all 18004 Tet10 corner sets and edge association preserved, max corner motion0.07837mm, midside0.09653mm. Эти результаты не заменяют canonical quality gate.

Новый тест `research/tools/p10nu_canonical_quality.py` использует только штатный Gmsh 4.15.2 API `gmsh.model.mesh.getElementQualities` на точных 18004 элементах типа11, до и после строго **in-memory** `HighOrderElastic`. Точные documented qualityName (`minSICN`,`minSJ`,`gamma`,`minDetJac`) и пороги D-031 из принятой M9 P10LB: 0.20,0.40,0.15,>0 соответственно. Основа API: https://gmsh.info/doc/texinfo/#gmsh_002fmodel_002fmesh_002fgetElementQualities . Для каждой метрики считаются counts, min/p01/p05/median/p95/max, nonpositive и below-threshold, 20 worst tetra centroids с радиальным положением от поры, north/south/nonpolar. Старые/new IDs **не** попарно сопоставляются, сравниваются распределения и геометрические позиции. Отдельно repeat boundary Tri6 invariant.

Source syntax+synthetic gates positive/negative PASS, ZIP6/6 CRC PASS, pinned original M13 R2 MSH SHA256 `57403ba43fa299417d519046cebdf50fa4968b670c071a8b7882748b50f51e9c`, архив `P10NU_M13_CANONICAL_QUALITY_WINDOWS_20261126.zip` 1.24 MB, self-contained. Native Gmsh в текущем runtime отсутствует, real Windows quality **не измерены**, цифры не приписываются.

Для пользователя: распаковать в новую папку, двойной клик `01_P10NU_RUN_CANONICAL_QUALITY.cmd`. Никаких PowerShell, ручных фраз или переписывания исходной сетки. Вернуть `P10NU_M13_CANONICAL_QUALITY_RESULT.json` и `P10NU_GMSH_QUALITY_LOG.txt` (при STOP оригинальный лог). Код при успешном gate выдаёт лишь `QUALITY_GATE_PASS_ONLY_NOT_M13_ACCEPTANCE` — итоговый M13 acceptance passport после независимого анализа данных; FEM автоматически не разрешён.
