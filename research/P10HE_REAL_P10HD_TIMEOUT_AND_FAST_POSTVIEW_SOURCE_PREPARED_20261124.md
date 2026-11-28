# P10HE — реальный P10HD time STOP, замена 1200 MathEval kernels на 3D PostView

**24.11.2026. `P10HD_REAL_1D_WALL_STOP`; `ORIGINAL_MATHEVAL_NOT_MESHABLE_WITH_300S`; `P10HE_FAST_3D_POSTVIEW_SOURCE_ONLY_PREPARED`; `M2 2D/3D/FEM=0`.**

## Независимый аудит первичного Windows P10HD

Первичный пользовательский `P10HD_ONE_1D_EVIDENCE.zip`: SHA256 **`ccf77ea3799f62f3d62a47f75a27d42b0262b68e3a3664dae921e55b06aa1a77`**; ZIP CRC PASS, 6 файлов. Manifest и preflight proof согласованы с pinned field SHA **`98ce03ed4a656dd6c3e9fc69f5c9711d7d8bbdc6bf61ddaceed9e656a918a85a`**. Gmsh 4.15.2 parse0.190с exit0. Ровно один native Gmsh `-1` на четырёх пробных линиях, wall300.349891с, peak private245772288 B, Windows Job hard4GiB, **WALL_LIMIT**, native exit1 после штатного остановочного действия. Log: Geometry и P10HC source «Done reading», «Meshing 1D», «Meshing curve 1 (Line)», «Meshing curve 2 (Line)», **нет «Done meshing 1D» и нет MSH**. M2 2D/3D, FEM не запускались.

Это не доказывает конкретный внутренний профиль Gmsh, но подтверждает **непрактичность текущего гигантского native MathEval при заданном 5-минутном лимите**. 1200 одинаковых компактных ядер с повторными sqrt/log и двойными суммами по тысячам фрагментов — сильная кандидатная причина; не тратить новый one-shot на простое увеличение wall. Оригинальные P10HD и P10HC markers не изменять и старую -1 не повторять.

## Новый поддерживаемый Gmsh путь

Официальная документация Gmsh 4.15.2 описывает **PostView** как 3D background mesh-size field со значениями размеров в узлах грубой исходной сетки. Вместо дорогостоящей оценки 1200 RBF при каждом запросе к Gmsh:

1. Read-only загрузить реальный pinned P10GT HXT10 **M1** из оригинального `P10GT_HXT10_EVIDENCE.zip` SHA `7bff029865bd69e12b8302a9f65b6159d61f58163300fdee81555954988a6ac3`, raw mesh SHA `47460969be26c2bd0a15e0b1425806fa350aa09aa2b4ac9f80605b433fc65ca7`. Ожидается 13 978 узлов /9 623 Tet10; CAD, физические группы и M1 files не перезаписывать.
2. Один раз вычислить исходный **механический** непрерывный C² `κ` P10HC в координатах существующих M1-узлов (Python numpy/scipy, вне Gmsh mesher).
3. Записать значения на четырёх corner-узлах каждого Tet10 как `SS(x1,y1,z1,...,x4,y4,z4){κ1,κ2,κ3,κ4}` в скалярное tetrahedron PostView; точный тип **SS** из документированного формата Gmsh, не ST (последний — scalar triangle).
4. Новый source GEO включает исходный P10GT M1 geometry/Field7 без изменения, `Merge` scalar 3D view, `Field[40]=PostView` с `ViewIndex=0`, `Field[43]=MathEval` короткой формулой `F7*(1−0.17*F40)^(1/3)`, `Background Field=43`. **Никакой вызов -1/-2/-3/FEM пакетом не выполняется**: выполняется лишь native Gmsh `-parse_and_exit` с timeout120с.

### Существенное научное ограничение

Исходное аналитическое поле — C², но интерполяция PostView на прямолинейных тетраэдрах M1 **не более C⁰** и использует хорды вместо curved Tet10 геометрии. Это гипотеза практического переноса, а не сохранённый автоматически строгий C² класс. P10HE вычисляет max, p95 и median локального расхождения κ в средних узлах Tet10 относительно линейной интерполяции; **до получения этих чисел нельзя объявлять PostView поле годным к M2**. Также нужно отдельно проверить interpolation search на поровой поверхности и работу Field[40] в native 2D/3D mesher. Весь signed 4D provenance сохранён, тепловые компоненты продолжают участвовать в PDE, но не в κ.

## Пакет и границы следующей проверки

Windows ZIP: `research/proposals/P10HE_POSTVIEW_SOURCE_ONLY_20261124/P10HE_R1_REAL_M1_C2_SAMPLE_C0_POSTVIEW_SOURCE_ONLY_WINDOWS_20261124.zip`, SHA256 **`944efa01831948aac6a95ac95f9cb05cb9397acea758bc708fef8ccc8cfbc2c7`**, 9 source файлов, CRC/byte compare PASS, Python syntax PASS.

Единственный запуск в новом каталоге: `01_P10HE_BUILD_POSTVIEW_NO_MESH.cmd`. Он автоматически ищет уже существующий исходный `P10GT_HXT10_EVIDENCE.zip` в `G:\ildar\Stage3D07\LOCAL_RUNS`, `G:\ildar\Stage3D07\P10GT_TOOLS_R1` или `G:\Downloads`, валидирует SHA, строит только scalar PostView и `P10HE_SOURCE_QA.json`, проверяет native Gmsh4.15.2 `-parse_and_exit`. **FEM=0, 2D=0, 3D=0, 1D=0**. Прислать `P10HE_SOURCE_ONLY_EVIDENCE.zip` (в том числе при STOP). Ориентировочное время для Python nodal sampling обычно секунды или минуты, нативный parse лимит2 мин; исходная M1 на ПК не пересчитывается.

Если C⁰ интерполяционная погрешность велика или Gmsh PostView не поддерживает корректный физический mesh source, дальнейший путь — отдельная Gmsh callback/API схема или компактная C² параметризация, без возврата к непрактичному 1.13 млн символов MathEval. Цель D-025 остаётся 15–25% реального локального уменьшения при κ=1 по 343/729QP, север/юг и неполярные зоны отдельно; **ни M2 геометрического GO, ни физического FEM GO сейчас нет**.
