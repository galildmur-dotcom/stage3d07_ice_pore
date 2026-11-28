# P10JC — восстановление исходного набора и обнаружение разрыва provenance FEM (24.11.2026)

**Status: SOURCE_PROVENANCE_STOP; no FEM, no compilation, no mesh generation.**

После реального Windows P10JA M4 geometry-input PASS восстановлены из GitHub 113 файлов по манифесту `P10FN_R1_GENERAL_M0_MN_TWO_STAGE_WORKFLOW_NO_INPUT`. Все 113 файлов SHA256 в точности совпадают, 0 mismatch. SHA манифеста: `fe6df5f1a6ddad85f137f5c65f588407fdff0deea8ce17dcd8dbb5b36fcd5838`. Реконструкция GitHub выполнена read-only, без публикации приватной M4.

**Это НЕ тот solver-source bundle, который выполнял успешный M3.** Реальный пользовательский P10IQ report зафиксировал `source_revision=P10GY_R2_FIXED_4D_WRITER_12_36_SELFTEST_GUARDED_ONE_SHOTS`, в отчёте P10IR указан исходный набор из 101 SHA-pinned files. Старый публичный P10FN manifest содержит 113 файлов и отличающуюся ревизию. Старая публичная `stage3d10fn_any_mesh_full4d.cpp` содержит строгую проверку CLI `--steps 6 --dt 150`, не допускающую 36×25; фактический M3 (`P10IR_MANIFEST.json`, исполняемый EXE SHA `9cbe31f74346001851d54616837340422cc5c0629fcdfae1f5164004d5cc46f5`) действительно выполнен в режиме 36×25, 900 s, 4 потокa. Это **не противоречие физическому M3**: GitHub содержит исходные трансформации P10GX (whitelist 6x150/12x75/.../36x25) и P10GY (dynamic 4D writer 12/36 test), которые объясняют расширение временной сетки; но без точного 101-файлового ZIP, использованного при P10IQ/P10IR, нельзя независимо доказать SHA эквивалентность, отсутствие промежуточных патчей и полноценный source compatibility GO.

Границы проверки:
- D031/D029 геометрия M4: **GO P10IZ**.
- Windows P10JA M4 входная сетка: **PASS**, FEM=0.
- Публичный старый P10FN 113-file hash check: **PASS**, но относится к иной ревизии.
- Exact P10GY/P10IR 101-file solver inventory: **NOT VERIFIED**.
- M4 FEM: **BLOCKED pending exact original source provenance**.

Следующее действие: получить **точный исходный Windows ZIP `P10IR_M3_FIRST_REAL_FULL4D_WINDOWS_ONE_SHOT_20261124.zip`** (не архив результатов `P10IR_M3_FIRST_FULL4D_EVIDENCE.zip`) либо `P10GY_R2_M0_M1_SEVEN_DT_FIXED_4D_WRITER_WINDOWS_20261123.zip` плюс последующие хешированные P10IQ/P10IR исходники. Не изменять никаких источников до SHA сверки. Затем ограниченный source-only P10JC 101-file verification, совместимость M4 pin и режим 36×25, отдельное одобрение FEM. Никакого автоматического перепуска существующих one-shot markers.

Репозиторий: исследовательская ветка `research/p10bb-w5b2-20261118`. Источники: `research/proposals/P10FN_GENERAL_WINDOWS_20261122`, `research/proposals/P10GX_TEMPORAL_4D_SERIES_20261123/build_p10gx.py`, `research/proposals/P10GY_TEMPORAL_4D_RECOVERY_20261123/build_p10gy.py`, `research/P10IR_M3_FIRST_REAL_FULL4D_WINDOWS_PREPARED_20261124.md`, пользовательские P10IQ/P10IR JSON.
