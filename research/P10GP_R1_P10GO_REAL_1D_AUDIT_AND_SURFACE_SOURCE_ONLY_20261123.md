# P10GP R1 — реальный P10GO 1D PASS и подготовка поверхности без запуска Gmsh

Дата: 23.11.2026. Источник — полученный от исследователя архив `P10GO_1D_PROBE_EVIDENCE.zip`, SHA-256 `747983ec066e2d52829b8782e91c44b4c731df5d03264e5600f5d55749b9ae71`, ZIP CRC 12/12. Оригинальный архив не публикуется.

## Независимая read-only проверка

Оба фактических Gmsh 4.15.2 вызова содержали `-1 -nopopup -nt 2`, `-format msh2`, exit=0, `Done meshing 1D`, `Done writing`, ошибок `Error:` нет. Хеши исходных GEO и журналов совпадают с JSON. Контрольный A `Background Field=3`: wall 0.50537210 с, внутреннее 1D 0.00297618 с. Новый B `Field[7]` с самодостаточным C¹ выражением без ссылок F3/F4/F5: wall 0.50605800 с, внутреннее 1D 0.00536394 с. Ранее P10GN вложенные F3 ссылки D/E завершились по 30-секундному лимиту. Следовательно, обход воспроизводимо решает наблюдавшееся зависание *на одномерном этапе данной геометрии*; это не доказательство внутренней причины Gmsh, качества 2D/3D или требуемых объёмов M1.

`P10GO_PROGRESS.json` содержит предфинальный статус `STOP_INCOMPLETE_1D_DIAGNOSTIC`, потому что исходный сценарий записывает progress после каждого case, а итоговый `status` обновляет только после цикла. `P10GO_MANIFEST.json` корректно содержит `DIAG_BOTH_1D_COMPLETED_NO_3D`. Это не повторный STOP. Оба one-shot разрешения исчерпаны; **02 P10GO не повторять, markers не удалять**. Фактически native 2D=0, 3D=0, FEM=0.

## Новый минимальный P10GP: SOURCE-ONLY

`research/proposals/P10GP_SURFACE_SOURCE_ONLY_20261123/P10GP_surface_source.py` извлекает byte-pinned source из P10GO и воспроизводит 2 взаимно сопоставимых GEO-кандидата поверхности:

- A: исходное F3, та же повернутая OCC сфера и B6;
- B: самодостаточное поле F7 с южной C¹ поправкой 0.06, тот же CAD/B6;
- одинаковые `Mesh.MeshSizeFactor=0.9378887276834518`, Delaunay `Mesh.Algorithm=5`, порядок 2 (Tri6);
- 10 201 source QA точек, точная проверка эквивалентности P10GO, четыре C¹ шва, диапазон множителя [0.94,1.00].

Source-only скрипт не вызывает `gmsh.exe`, `-2`, `-3` или FEM. Архив `P10GP_R1_SURFACE_SOURCE_ONLY.zip`: SHA-256 `236defb377103ef45e8ac193264fac8213290c7d00e02fc1025e53c9f700cc3a`, восемь GEO файлов плюс manifest, CRC/все внутренние SHA PASS. Это **не Windows One Click для запуска** и не разрешение выполнить новую native попытку.

## Дальнейший барьер

Перед native 2D требуется отдельный согласованный ограниченный Windows запускатель: точный EXE SHA, preflight, byte-stable GEO, два собственных one-shot markers, явно ограниченные время/RAM/вывод, отдельные каталоги A/B, запрет 3D/FEM, оригинальные журналы и evidence ZIP. После него независимая проверка Tri6 surfaces (physical groups, pore/B6 closure, curved QP, physical north/south q и edge sizes) определит, можно ли вообще предлагать отдельный 3D опыт.

Frozen D-027: global QV729 M1/M0 в [0.80,0.85], physical near-polar QV729 ≤0.98, CAD/curved Tri6/Tet10 и положительный 27/343/729QP detJ; 18 подписанных зон только полная диагностика, не 18/18 hard. M1 STOP, FEM=0.
