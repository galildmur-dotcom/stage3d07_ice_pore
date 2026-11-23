# P10GT R1 — один ограниченный трёхмерный HXT10 кандидат

Дата: 23.11.2026. **Подготовка SOURCE/UNIT, реальный новый 3D native ещё НЕ выполнялся.** Цель — проверить перенос положительного результата 20-case P10GR Tri6 на объёмную 3D Tet10, без FEM.

Точно один кандидат: `ALGO6_A09_MU20` = Frontal-Delaunay 2D Algorithm6 + HXT 3D Algorithm10, alpha=.09 и smooth south angular mu≤−.8 plateau с затуханием до mu=−.2. Исходное full M0 F3 раскрыто в одно самодостаточное MathEval без вложенных F3/F4/F5. Исходный rotated OCC CAD pore/B6, физические границы, глобальный factor=.9378887276834518, радиальное C¹ поле и порядок 2 неизменны. Важно: численные требования D-027 M1 задаются независимо и не подгоняются под этот новый кандидат.

**Протокол 01→02:**

1. Распаковать пакет в **новый** `G:\ildar\Stage3D07\P10GT_TOOLS_R1` — не поверх P10GL/P10GR.
2. Один раз `01_P10GT_PREFLIGHT_NO_MESH.cmd`: проверяет exact source/Gmsh/M0/frozen D-027 SHA и native `-parse_and_exit`; без сетки. Ожидаем `P10GT_PREFLIGHT_PASS_NO_MESH`.
3. Не позднее24ч после preflight однократно `02_P10GT_ONE_HXT10_3D_ONLY.cmd`. Не вводить фраз или путей. Одна команда `gmsh -3 -nopopup -nt 2`, лимит900с, Windows Job private8GiB, свободная RAM≥12GiB и диск≥4GiB, mesh≤128MiB, log≤8MiB, видимый heartbeat каждые2с. Два новых permanent local/profile one-shot markers создаются ДО запуска. При STOP повторять 02 запрещено, markers не удалять.
4. Прислать **один** `LOCAL_RUNS\P10GT_HXT10_*\P10GT_HXT10_EVIDENCE.zip`, даже если STOP. Если ZIP нет — `P10GT_02_RESULT.txt`/текст окна. Не нужны другие архивы, EXE, VTU или FEM истории.

В 02 выполняется первичная независимая geometry QA 27QP и Tet10/physical Tri6 проверки, однако **результат даже PASS не означает M1 GO**: требуется отдельный read-only **343/729QP** аудит глобального effective V ratio [0.80,0.85], положительности sampled detJ, физического южного и северного near-polar [≤0.98] и 18 signed зон диагностически. Сохранить quality/sliver/face-adjacent grading и CAD hard gates. FEM=0. Старые P10GL/P10GR 02 израсходованы; их повтор недопустим.

Оценка на ПК i7-7700K, 64GB RAM: реальное время **неизвестно** — может быть от минут до 15мин, при превышении 900с STOP. Максимальная private RAM Gmsh 8GiB, без механики/температуры. Это безопасная одиночная попытка проверки **алгоритма построения сетки**, а не физический эксперимент.
