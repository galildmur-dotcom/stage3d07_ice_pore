# P10IY — новая guarded попытка M4 после P10IV geometry STOP (24.11.2026)

**Статус `P10IY_SOURCE_ONLY_PREPARED`, реальная M4 новая сетка НЕ строилась, FEM=0.** Исходные результаты P10IW и P10IX сохранены, старый P10IV R1 local/profile one-shot markers не сбрасываются и не повторяются. Действует D-030: самостоятельный D031 quality hard gate, отдельная D029 target 25–50% actual supported Veff и последующая физическая сходимость.

## Полная идентичность и сдерживание

Пакет для пользователя: `P10IY_R1_M4_REPAIRED_GUARDED_MESH_ONLY_WINDOWS_20261124.zip`, SHA256 **`7d798b148a9acd1e7c3045fb4fff9300cf03e195c064ee8a0938bc073e3214ec`**, 1,862,568 bytes, ZIP CRC 20/20 PASS. Содержит 16 SHA-pinned входов/исходников, 3 рекурсивных CAD GEO (original CAD SHA `f1227074616375c28706e1e55cddde370b9a9fca069aab88513b4313c8239f51`), принятые exact M2 SHA `d1ec65ff...`, M3 SHA `3d6ce765...`, P10HA/P10IM/P10IT и P10IX source-only QA. Меши M2/M3 включены **только в приватно переданный ZIP**, не публикуются в публичном GitHub; публично сохраняются только source/protocol без больших исходных MSH.

Локально Python `py_compile` PASS, exact 16 source SHA + 3 recursive Include source-only preflight PASS, negative tamper M3 SHA STOP PASS, source-only field callback sample PASS. Gmsh Python API 4.15.2 на Windows обязателен. **Никакой новой Gmsh генерации или FEM в ходе подготовки не выполнено**.

## Новые физические поля размера

Постановка исходного CAD и десять исторических embedded pore points сохранены ради сопоставимости эксперимента, но не объявлены обязательным неизменным инвариантом алгоритма. От ранее использованного P10IV callback новая ревизия отличается двумя дополнениями:

1. Северное C² поле size: полярное `δ_N=.11445576719134759 → .18`, при той же южной `δ_S=.12998093714900827`. Один наблюдавшийся M3→M4 отклик задаёт **только феноменологическую гипотезу** около `.7114` actual N Veff ratio; не обещать достижения D029 на новой сетке.
2. Near-wall C² локальная поправка вокруг физического направления нормированной проекции центра проблемной pore-wall грани Tet10 10378. Compact Wendland angular chord support .45, quintic radial fade to d=.5мм, max extra log-size .10; в центре отвергнутого тетра новый ratio≈.938615 от прежнего проектного размера. Уменьшение h **не является доказательством улучшения качества Tet10**.

Вместе эти изменения реализованы одним Python Gmsh4.15.2 `setSizeCallback` на *полной оригинальной 3D CAD*, без вручную изменённого M3 node topology, без FD производной формы. Worker выдаёт `P10IY_M4_R2_CANDIDATE_UNVERIFIED.msh` и JSON. Источник/поле pinned, параметры hardcoded с проверкой P10IX QA.

## Windows One Click

1. Распаковать ZIP в новую чистую отдельную папку вне `G:\ildar\Stage3D07`, без переноса старых one-shot markers.
2. Двойной щелчок `01_P10IY_PREFLIGHT_NO_GMSH_NO_FEM.cmd`. При отсутствии PASS — STOP, 02 не запускать.
3. Двойной щелчок **один раз** `02_P10IY_ONE_M4_REPAIR_MESH_ONLY.cmd`; нет ручного ввода `RUN ONE`. Новый локальный и профильный `LOCALAPPDATA/Stage3D07_OneShot_Markers/P10IY_R1...` marker создаются **до native Gmsh**, чтобы запретить повтор при ошибке и из другой папки. Heartbeat не реже 30с. Лимит 900с, monitored private RAM8ГиБ, output MSH250МиБ, log32МиБ, 4 threads.
4. Исследователь присылает **единственный** `P10IY_R1_M4_REPAIR_UNVERIFIED_EVIDENCE.zip`. Если STOP — передать оригинальный ZIP/LOG, **не** удалять маркеры и не перезапускать.

Оценка на пользовательском i7-7700K: ограничение 15мин/8ГиБ, ожидаемый фактический Gmsh по предыдущему опыту порядка десятков секунд, однако **новая сетка не измерена**, и быстрый исход не гарантирован.

## Приёмка после native evidence

После единственного реального mesh-only провести независимый read-only curved Tet10 D031: minSICN≥.20, minSJ≥.40, gamma≥.15, Gmsh/27/343/729 detJ>0, CAD closure, теги Tri6 и полюса, в частности не повторилась ли проблема около физического прежнего Tet10 10378 (номер в новой сетке может измениться). Независимо D029 actual supported north/south 729QP `Veff(new M4/M3)∈[.50,.75]`, `N_eff≥30`, 343→729 drift. Не считать неуспех D029 геометрическим D031 STOP, `q` только диагностика. FEM M4 **только после** geometry GO и отдельного научно-ресурсного решения.
