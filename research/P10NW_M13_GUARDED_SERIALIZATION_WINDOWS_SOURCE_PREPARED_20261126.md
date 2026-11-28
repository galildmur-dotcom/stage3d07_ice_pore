# P10NW — одна защищённая запись оптимизированной M13 и повторный reimport-аудит (26.11.2026)

**СТАТУС: SOURCE_ONLY_PREPARED; REAL WINDOWS NATIVE PENDING; OPTIMIZED_MSH_NOT_YET_WRITTEN; FEM0.**

## Исходная доказательная база

P10NV паспорт `research/evidence/P10NV_M13_IN_MEMORY_GEOMETRY_PASSPORT_20261126.json` дал `GEOMETRY_GO_IN_MEMORY_ONLY_NO_PRODUCTION_MSH`. P10NQ–P10NT подтвердили boundary point cloud / 2512 Tri6 / 3509 corner graph bijection / 18004 Tet10 topology / sampled27/343/729 positive detJ; P10NU canonical D031 quality after HighOrderElastic: minSICN0.3177166282≥.20, minSJ0.6418251242≥.40, gamma0.2446522347≥.15, minDetJac1.744892546e−13>0. Но оптимизированная MSH отсутствует, её SHA не известен.

## Новый единственный P10NW опыт

Пакет `P10NW_M13_OPTIMIZED_SERIALIZATION_WINDOWS_20261126.zip` 10 файлов (~1.25 MB), source exact M13 R2 SHA `57403ba43fa299417d519046cebdf50fa4968b670c071a8b7882748b50f51e9c`, Gmsh4.15.2 Python API. Новые `research/tools/p10nw_serialize_m13.py` и `research/tools/p10nw_collect_evidence.py` плюс P10NQ/NR/NS-R2/NT/NU dependencies.

Одна CMD `01_P10NW_RUN_ONE_SERIALIZE_M13.cmd` в **новой папке**, без PowerShell и ввода. До любой записи:
- SHA source, Gmsh exact version, absence of output/local/global markers;
- in-memory HighOrderElastic с закреплёнными FixBoundaryNodes1, IterMax50, PassMax5, NumLayers2;
- independent boundary Tri6, exact sphere radius, full canonical four D031 quality gates and anchored graph verification of 18004 Tet10.
При pre-write STOP MSH не создаётся.

Перед первой записью новой MSH2.2 ASCII `P10NW_M13_OPTIMIZED_CANDIDATE.msh` создаётся постоянный глобальный `%LOCALAPPDATA%/P10NW_STAGE3D07_M13_OPTIMIZED_ONESHOT_CONSUMED.marker`, затем локальный marker. Они **никогда не удаляются** и не переиспользуются даже после STOP; вывод не перезаписывается. Отдельный output bounded ≤64MiB.

После записи **gmsh.clear + gmsh.open output file**, точный SHA256 written bytes, проверка 18004 Tet10 / физгруппы 2–9, Gmsh D031, boundary Tri6, exact sphere, reloaded corner graph bijection и 6 midside-node associations. Требовать положительные quality gates, относительное совпадение canonical minima≤1e−8, перемещения corner+mid reimport≤1e−12м. Если всё PASS: `SERIALIZED_M13_REIMPORT_PASS_NO_FEM`. Лишь это доказывает новый записанный файл. Ни FEM, ни M13 R3 объявляется до результата.

Результат упаковывается в **один** `P10NW_M13_SERIALIZED_EVIDENCE.zip` с JSON, оригинальным log и **новой ~3MB MSH** (допустимо, чтобы независимо воспроизвести и аттестовать новую сетку в последующем чате). Другие кэши, исполняемые файлы, markers туда не включаются.

## QA и пределы

Local Python compile PASS, synthetic serialization gate positive/negative PASS, Linux native run STOP before any marker/output PASS, ZIP CRC10/10 PASS. Real Windows Gmsh write/reimport не исполнен. На ПК исследователя ориентировочно 1–5 минут, но точный native bound неизвестен. При любом STOP исходные marker/output сохранять, кнопку не повторять. После evidence делать independent P10NX serialized mesh QA/паспорт, только потом отдельное FEM GO.
