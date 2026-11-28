# P10GT R1 — один HXT10 3D-кандидат после успешного P10GR/P10GS surface DOE

Дата 23.11.2026. **SOURCE/UNIT/ZIP PASS, реальный Windows native 3D пока 0, FEM0.** Цель — проверить перенос адаптивного поля `ALGO6_A09_MU20` с поверхности на объёмную Tet10, не объявляя автоматически M1 GO.

## Научное основание

P10GR 20/20 реальных native Windows Gmsh4.15.2 `-2` и независимый P10GS MSH QA PASS: `ALGO6_A09_MU20` (Frontal-Delaunay Algorithm6, alpha=.09, plateau physical μ≤−.8, C¹ fade to μ=−.2), south edge median 0.369401мм против Algorithm6 baseline 0.422669мм (ratio.873970), north1.00605, equator1.013659, pore qmin0.647207, max adjacent edge characteristic ratio1.370995. Это сильный **2D** кандидат, но объёмная плотность и Tet10 качество не измерены. Методическое D-027 frozen: global 0.80≤QV729≤0.85, physical populated polar0–500µm QV729≤0.98, positive curved detJ 27/343/729QP, CAD, sliver, соседняя градация; 18 signed зон diagnostic-only.

## Новый источник без подмены экспериментального поля

Самодостаточный ZIP `research/proposals/P10GT_3D_ALGO6_A09_MU20_20261123/P10GT_R1_ONE_GUARDED_HXT10_WINDOWS_20261123.zip`, SHA256 **`5a755f9b52c4a24cfa12a5272c0a9214e1bdb376901f223914b42995c08d9aff`**, 13 файлов. Драйвер генерируется из закреплённого P10GR source ZIP SHA `5bc94e2939f6a96c1c2e7b9a77a721e3b1b8c02cbc2eb9342e80f53717f72909`, исходного self-contained F7 без F3/F4/F5 ссылок, и дополнительно source selftest **доказывает буквальное совпадение полного MathEval F7 с P10GR `ALGO6_A09_MU20`**. CAD rotated pore/B6, h-factor `0.9378887276834518`, исходные M0 pins и frozen D-027 не меняются; 2D Algorithm6, 3D HXT Algorithm10, ElementOrder2.

Два CMD: `01_P10GT_PREFLIGHT_NO_MESH.cmd` — SHA Gmsh4.15.2/M0/frozen, native `-parse_and_exit`, no mesh, proof≤24ч; `02_P10GT_ONE_HXT10_3D_ONLY.cmd` — **одна** защищённая native команда `-3 -nt2` ≤900с/8GiB private memory, heartbeat в окне каждые2с с последней строкой Gmsh, source outputs SHA and independent 27QP + curved Tri6/Tet10 audit, permanent distinct local/profile one-shot markers **до** native. Перед запуском RAM free≥12GiB и disk free≥4GiB; MSH≤128MiB/log≤8MiB, evidence ZIP≤144MiB. Два одинаковых deterministic ZIP builds SHA PASS, CRC13/13, isolated extract+selftest PASS, non-Windows native STOP PASS, tampered source ZIP STOP PASS. Запуск Windows ещё не проверен.

Программа записывает все доказательства даже при STOP и не вызывает FEM. Пакет сохраняет 27QP preliminary verdict, однако **независимый полный 343/729QP и физические polar macro zones обязательны до любой M1 GO**; 27QP PASS не является допуском и локальное сгущение не гарантирует D-027 глобальную долю объёма. Конкретные пороги D-027 зафиксированы ранее на M0 в `P10GJ_D027_FROZEN_GATES.json`, их нельзя подгонять по результату.

Операционно: распаковать только в новую папку `G:\ildar\Stage3D07\P10GT_TOOLS_R1`, выполнить 01, после PASS однократно 02, прислать один `LOCAL_RUNS\P10GT_HXT10_*\P10GT_HXT10_EVIDENCE.zip` или при отсутствии ZIP `P10GT_02_RESULT.txt`/текст окна. Не повторять 02 на STOP, не удалять markers, не менять старые P10GL/P10GR данные. Поскольку D-028 действует, для **подготовки** и самостоятельного **запуска исследователем** ограниченной диагностической кнопки повторное ритуальное разрешение не требуется. Примерная длительность на i7-7700K неизвестна; hard900с, RAM8GiB max, FEM0.
