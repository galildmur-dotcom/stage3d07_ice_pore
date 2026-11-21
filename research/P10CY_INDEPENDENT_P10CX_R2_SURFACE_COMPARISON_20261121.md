# P10CY — независимый аудит реальной Windows Gmsh4.15.2 поверхности U1_geo

**21.11.2026, D-018A.** Уровень: реальное выполнение Windows 2D + оригинальные проверенные CSV/JSON и независимый offline audit, **не** 3D Tet10 и не физический FEM.

## Новизна и источники

P10CW уже сделал одну Linux surface-mesh на runtime Gmsh4.13.1 и обнаружил единственный southern Tri6 с corner quality=0.0747478437. P10CX R1 не дошёл до mesh из-за blank native exit в version probe. P10CX R2 отдельно исправил только preflight и на Windows выполнил новую 2D mesh-only попытку.

**Оригинальный R2 Windows ZIP**: `P10CX_R2_EVIDENCE.zip`, SHA256 `27766d2ab11b38aeb964e91909035fe8a8665ea1d7fa403ae03f3afbd7535e86`, ZIP CRC **9/9 PASS**. Сохранён без изменения под `research/evidence/P10CY_R2_WINDOWS_INDEPENDENT_20261121/input/`. Независимый контроль — `research/proposals/P10CY_REAL_R2_INDEPENDENT_20261121/p10cy_independent_surface_compare.py`, derived JSON `research/evidence/P10CY_R2_WINDOWS_INDEPENDENT_20261121/derived/P10CY_R2_INDEPENDENT_SURFACE_COMPARE.json` SHA256 `725e61801e0de64a584dc3bc524b8696b7eac3420d09e74b7828e44599752ae4`.

## 1. Воспроизводимость Windows R2

| Контроль | Подтверждено |
|---|---|
| Native Gmsh version exit | **0**; stdout `4.15.2` |
| SHA Windows EXE | `317c43391e5b1fab3a1dd80dc5245dad6e2d087910f4b8ebc234bd6d4b8f41a1` (совпадает с R1) |
| GEO / OCC / Python SHA gates | **3/3 PASS**, те же pinned источники P10CV |
| Python synthetic / Gmsh surface / Python QA native exits | **0 / 0 / 0** |
| Gmsh surface wall time / peak private memory | **4.417 с / 0.2743 ГиБ** (сообщено R2 Windows runner) |
| Windows `.msh` | 16 802 633 байт, SHA256 `fad1bbf0012d11e144e2af457c2c5eb11e7c5fecce9d8833eb164f4617894915` на Windows |
| Original output | 9 файлов ZIP; сохранены unit, stdout/stderr, 120-cell CSV и JSON |
| Status | `P10CX_SURFACE_QA_NO_SLIVER_NO_3D_NO_FEM` |

Саму Windows `.msh` пользователь не передавал: её SHA-256 подтверждён Windows скриптом, но вторично по сырым байтам ассистент его **не проверял**. Gmsh stdout пишет 175602 узла и **88328 элементов всех сущностей**, тогда как MSH2 physical-file QA видит 175602 узла и **87798 physical elements**: разные области подсчёта, не автоматически потерянные 530 элементов.

## 2. Действительная поверхность на двух установках

| Показатель | Linux runtime 4.13.1, P10CW | Windows 4.15.2, P10CX R2 |
|---|---:|---:|
| Tri6 physical `PORE_WALL` | 74592 | **74578** |
| Площадь по плоским треугольникам, мм² | 12.5653411904 | **12.5653409315** |
| Медиана max corner-edge, мкм | 20.0150093 | **20.0128075** |
| 5% / 95% max edge, мкм | 19.6014 /22.3348 | **19.6210 /22.2989** |
| Минимальный straight-corner quality | **0.07474784** | **0.48062286** |
| Tri6 с quality<0.1 / quality<0.2 | 1 /1 | **0 /0** |
| Полярная доля chordal площади (ожидается 20%) | 20.00774% | **20.00038%** |
| Полярная/неполярная медиана hmax | 1.002031 | **1.001705** |
| Занятые 10 μ×12 φ ячейки | 120/120 | **120/120** |

**Независимый P10CY exact-cell parity:** все 120 CSV строк имеют правильные `(μ,φ)` ключи; counts в CSV/JSON совпали целочисленно, суммарные 74578 Tri6 и плоская площадь замкнулись; hmedian/area для каждой клетки совпали с JSON в допуске 1e-12; SHA и native exits подтверждены. Normalized total variation count-distribution между двумя surface meshes на 120 клетках = **0.00509952 (0.510%)**. 14 Tri6 разницы ≈0.0188% общего числа. Это описательная метрика распределения, не оценка ошибки FEM.

Худший Tri6 в Windows находится в южной μ0, φ1 (φ≈44.23°), но его corner quality=**0.48062286**, то есть прежний sliver `<0.1` **не воспроизводится** на этой сетке. Выборочная проверка Gmsh stdout: high-order optimization completed, 0 плохих элементов во внутреннем диагностическом сообщении оптимизатора. Это не непрерывное доказательство положительного detJ на будущих **3D curved Tet10**.

## 3. Допустимый научный вывод

**Surface geometry gate PASS в оговорённом смысле:** на одном реальном Windows Gmsh4.15.2 mesh-only запуске размер стенки ~20мкм, угловое покрытие и Tri6 corner quality принимаются; полюса не имеют выраженной систематической size-bias. Единственный ранее наблюдённый плохой Tri6 из Linux 4.13.1 не повторился. Величина qmin выросла на **0.405875**.

**Оговорка причинности:** изменились одновременно версия нативной библиотеки Gmsh и платформа/сборка; две конкретные сетки не являются контролируемым доказательством, что именно версия Gmsh исправила дефект. Это только межустановочная невоспроизводимость одного sliver. Действительный механизм больших полярных производных формы на старых **объёмных** H4W* и истинная локальная погрешность D_Rjpeak остаются **UNKNOWN**.

**Не доказано:** качество/положительность детерминантов 3D Tet10, реальное распределение 0–20/20–100мкм QP в объёме, расход ресурсов полного 3D, сходимость по сетке и времени полной adjoint производной. R2 ничего не менял в C++ и не запускал FEM.

## 4. Единственный следующий минимальный этап

До новой Gmsh `-3` нужно спроектировать **ресурсный mesh-only 3D feasibility gate** для той же U1_geo: явно оценить N(Tet10), expected RAM/время/файл на i7-7700K/64ГиБ, верхние границы watchdog, verify 27QP curved detJ и радиально-полярно-азимутальное QP-покрытие, не полагаясь на corner-centroid. Сетка U1_geo всё ещё **не** физическая M1; перед любым настоящим FEM потребуется отдельная санкция и signed thermal/mechanical 4D protocol. Повторять R1/R2 2D без нового вопроса — **STOP_DUPLICATE**.
