# P10NS — автономная объёмная Tet10 диагностика после P10NR (26.11.2026)

**Статус: SOURCE-ONLY PREPARED, Windows native PENDING, FEM0, M13 R3 NOT RUN.**

Основание — действительный P10NR Windows результат от 26.11.2026: 5030 boundary nodes, 4420 coordinate-relabelled tags, boundary Tri6 all eight physical groups 2–9 preserved (2512 faces, 0 missing/extra) при HighOrderElastic. Источник M13 R2 SHA256 `57403ba43fa299417d519046cebdf50fa4968b670c071a8b7882748b50f51e9c`.

**Новый вопрос:** сохранились ли геометрические угловые тетраэдры Tet10 независимо от element/node IDs, и какой эффект elastic optimization оказывает на координаты midside и знак sampled curved Jacobian?

Подготовлен `research/tools/p10ns_volume_audit.py`. На одной неизменной исходной M13 R2 строятся before и in-memory HighOrderElastic after snapshots без записи новых MSH и без FEM. Источник импортирует закреплённые `sample` P10NQ и `classify` P10NR. Строгая координатная биекция только **угловых** узлов Tet10 допуск1e−12 м; не предполагает неизменности срединных координат. Индексация по множеству 4 вершин каждого Tet10 (не element tag), проверка шести edge-midpoint ассоциаций и физических displacement. Все 18004 Tet10 проверяются; если угловые узлы действительно перемещены, выдаётся диагностический STOP — точная биекция не выдумывается.

Квадратичный геометрический Jacobian Tet10 вычисляется аналитически через градиенты Lagrange-P2 shape functions. На каждом Tet10 детерминант до/после проверяется на детерминированных внутренних Duffy-Gauss 3³=27, 7³=343, 9³=729 точках (суммарно 1099 точек/элемент на состояние). Это sampled sign audit, **не математическая гарантия глобального detJ>0**, не canonical Gmsh D-031 minSJ/minSICN/gamma. Batch64. Отрицательный detJ synthetic fixture и affine detJ=1 unit протестированы.

Локально: Python syntax PASS; `P10NS_SYNTHETIC_TET10_JACOBIAN_PASS` (affine positive, perturbed negative, exact coordinate-remapped corner topology). Native Gmsh module в облачном окружении отсутствует, реального Windows результата **нет**. Самодостаточный ZIP `P10NS_M13_TET10_VOLUME_AUDIT_WINDOWS_20261126.zip` (6 файлов; 1.24MB) с pinned raw M13 R2, three py, CMD, README. ZIP CRC PASS, source mesh SHA verified. В отдельную папку распаковать, двойной клик `01_P10NS_RUN_VOLUME_AUDIT.cmd`; без PowerShell/ручных команд/markers. Возвратить только `P10NS_VOLUME_TOPOLOGY_QUALITY_RESULT.json` и `P10NS_GMSH_VOLUME_LOG.txt` — также при STOP.

**Gate:** P10NS source prepared ≠ M13 accepted. После Windows доказательства проверить full Tet10 corner topology, midside displacements, positive 27/343/729 sampled detJ, независимые canonical Gmsh quality до отдельного решения о M13 mesh use/FEM. Никаких новых физрасчётов и M13 R3.
