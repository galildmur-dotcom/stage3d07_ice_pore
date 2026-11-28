# P10IO R1 STOP: missing transitive CAD Include; R2 separately prepared

**Факт 24.11.2026:** пользователь выполнил один P10IO R1 mesh-only guarded запуск и прислал `P10IO_WORKER_ERROR.txt`, `P10IO_GMSH_LOG.txt`, `P10IO_M3_UNVERIFIED_EVIDENCE.zip`, `P10IO_GUARD_RESULT.json`. R1 guard: `WORKER_STOP`, `native exit_code=1`, `wall_s=.575`, peak_private_polled=774144 bytes, `one_shot_consumed=true`, `FEM_attempts=0`, `accepted_M3=false`, `mesh_sha256=null`.

Журнал Gmsh устанавливает точную причину: `P10GT_HXT10.geo` → `M0_ROTATED.geo` → **`sphere_pore_B6_refined_rotated.geo`**, последний транзитивный Include **не был включён в первоначальный ZIP**. Остановка на `gmsh.open`, `mesh.generate(3)` не достигнут, нет M3 CAD mesh/элементов и нет новых физических расчётов. Это ошибка комплектации источников ассистентом, не ошибка Gmsh HXT10 и не провал поля P10IN/D031/D029.

**R1 одноразовый marker израсходован и должен оставаться на месте навсегда; повтор старого пакета запрещён.** Ранее выполненные M1/M2 Gmsh и FEM также не затрагивались.

## Исправление R2

- Новый архив `research/packages/P10IO_R2_M3_FIRST_GUARDED_3D_MESH_ONLY_WINDOWS_20261124.zip`, SHA256 `03c54c7ea04738830d4c0b26ace4011d686c2b39dc743be458818c7f5a301814`.
- Добавлен оригинальный неизменённый `sphere_pore_B6_refined_rotated.geo`, SHA256 `e3f4d1c472e4d047962bf05f63406f2bbb20b89f20e74ac2e6f2ba8cfd305329`. Исходная rotated CAD не менялась.
- До native `gmsh.open()` и **до one-shot marker** проверяются все 7 pinned исходных файлов и полное замыкание графа `Include`: три exact GEO, неизвестный/циклический/отсутствующий include STOP_NO_GMSH. Вручную исполнять R1 после STOP запрещено.
- R2 marker `P10IO_R2_ONE_3D_ATTEMPT_CONSUMED.marker`, R2 evidence `P10IO_R2_M3_UNVERIFIED_EVIDENCE.zip`, отдельная чистая папка `G:\ildar\Stage3D07\P10IO_M3_MESH_ONLY_R2`; если старый R1 marker обнаружен в папке, R2 preflight требует чистую папку и STOP.
- Локальный источник QA: `P10IO_R2_PREFLIGHT_PASS_NO_GMSH_NO_FEM sources=7 geo_includes=3`; дополнительный **negative unit test** без третьего Include корректно останавливается `uncontrolled GEO include`; Python worker imports/old+new C² callback smoke PASS; ZIP CRC PASS. Сам Gmsh Python 4.15.2 недоступен в агентском runtime, поэтому **реальной R2 3D Gmsh попытки здесь нет**, её может выполнить пользователь на Windows после preflight.
- Метрический источник, физика, D031/D029 gates, 10 pinned pore seeds, 4threads/15min/8GiB-polled/30s-heartbeat — как в R1. R2 не разрешает FEM, а создаваемая M3 имеет статус `CANDIDATE_UNVERIFIED`.

**Следующий gate:** пользователь запускает `01_P10IO_PREFLIGHT_NO_GMSH_NO_FEM.cmd`, затем только после `EXIT=0` один раз `02_P10IO_ONE_M3_3D_MESH_ONLY.cmd` из **нового** R2 каталога. Вернуть один `P10IO_R2_M3_UNVERIFIED_EVIDENCE.zip`, затем независимая 729QP D031/D029 приёмка. Не объявлять M3 принятой до этого.
