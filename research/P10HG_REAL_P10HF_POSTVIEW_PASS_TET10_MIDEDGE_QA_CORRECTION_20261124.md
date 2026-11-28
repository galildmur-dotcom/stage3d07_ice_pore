# P10HG — реальный P10HF PostView PASS, исправлена нумерация Tet10 при QA средних узлов

**24.11.2026. `REAL_P10HF_SOURCE_POSTVIEW_PASS`; `MIDSIDE_INTERPOLATION_NUMERICAL_VERDICT_WITHHELD`; `P10HG_CORRECTED_QA_PREPARED`; `NO NEW 1D/2D/3D/FEM`.**

## Первичное доказательство

Пользователь прислал `P10HE_SOURCE_ONLY_EVIDENCE.zip`, SHA256 **`acb6a4d50a67799d58766ab21e998ea63f832a48b8d78dd380cac0b99bb7b64e`**, 5 файлов, оригинальные raw M0/M1 mesh/FEM ZIP не публиковать. QA manifest: `protocol=P10HE_R1_POSTVIEW_C0_FROM_C2_NODAL_SOURCE_NO_MESH`, `status=P10HE_SOURCE_POSTVIEW_BUILD_AND_GMSH_PARSE_PASS_NO_MESH`. Pinned P10GT original evidence SHA `7bff029865bd69e12b8302a9f65b6159d61f58163300fdee81555954988a6ac3`, actual canonical M1 mesh SHA `47460969be26c2bd0a15e0b1425806fa350aa09aa2b4ac9f80605b433fc65ca7`, 13978 nodes /9623 Tet10, all 9623 scalar tetrahedra in source PostView. `κ_nodes∈[0,1]`, `.pos` 3118554B / SHA `bfdd973536293e8264221c8753e74c7586016f41c28e6850735c6373bd083182`; native Windows Gmsh4.15.2 parse-only exit0, wall0.33s. New 1D=0,2D=0,3D=0,FEM=0. **Поэтому source construction PASS; но не M2 mesh GO.**

## Критическое обнаружение в независимой проверке

Исходный P10HE Python код при контроле разности между настоящим C² κ в Tet10 midside и линейной PostView хордой неверно сопоставлял последние два средних узла:

- Старый ошибочный порядок для j=4,5: `(1,3),(2,3)`.
- Документированный в Gmsh4.15.2 **правильный** local edge ordering 10-node tetrahedron: `(0,1),(1,2),(2,0),(3,0),(3,2),(3,1)`.

Поэтому три опубликованные в исходном JSON величины `kappa_mid_edge_chord_linear_abs_max=0.7324694`, `...p95=0.0240556`, `...above_0p05_count=1098` **нельзя интерпретировать ни как доказанную ошибку, ни как доверенную оценку PostView**. Не исправлять их оценкой на глаз и не пытаться разрешить M2 по ошибочному статистическому файлу. Сама 3D scalar tetrahedron `SS` запись корректно использовала только четыре corner узла; этот недочёт находился **только** в постпроверке mid-edge, не в построении scalar view/узловых κ.

## Исправленный R3 только для QA

Отдельный ZIP `research/proposals/P10HG_CORRECT_TET10_EDGE_QA_20261124/P10HG_R3_CORRECT_TET10_MIDEDGE_QA_WINDOWS_20261124.zip`, SHA256 **`712282398a9d7c0052ace1b4701538286ca468852d9e6ebcf4a0455ca859e26e`**, 10 source files CRC/byte consistency PASS; source кода R1/P10HF опубликованные ZIP неизменны. Программа R3:

1. Проводит отдельный синтетический unit-test **точного порядка Gmsh Tet10** на линейном скалярном поле, ошибка `5.55e−17`, PASS.
2. На прежней pinned реальной M1 снова вычисляет **тот же** C² mechanical κ в узлах (NumPy-only, SciPy не нужна) и скалярный `SS` PostView (никаких новых Tet10).
3. Только после этого независимо пересчитывает корректные max/p95/median и количество случаев `|κ_C2−κ_linear|>0.05` в настоящих midside узлах; native Gmsh вызывается лишь в режиме `-parse_and_exit` с timeout120с. Физика FEM=0, mesh 1D/2D/3D=0, one-shot markers не меняются.

Windows один `.cmd`: `01_P10HG_CORRECTED_EDGE_QA_NO_MESH.cmd`. Передать `P10HE_SOURCE_ONLY_EVIDENCE.zip` из каталога R3. Пакет не должен спрашивать у исследователя разрешение на подготовку программы; предыдущий R2 успешный source не повторять, кроме этого точечного исправленного расчёта QA.

## Научная граница

Gmsh PostView на линейных хордах M1 сохраняет исходное C² κ только в corner nodes; интерполированное 3D поле не выше класса C⁰, и возле curved Tet10 pore surface возможно геометрическое несогласование. Окончательную приемлемость определять **после** корректного R3 mid-edge QA и независимого исследования интерполяции на физических северных/южных приполюсных и неполярных границах. Только затем планировать bounded surface-only Gmsh `-2`, никогда автоматически не переходить к M2 `-3` или FEM. D-025 реального `Veff(M2)/Veff(M1)∈[0.75,0.85]` при κ=1 и 343/729QP остаётся действующим.
