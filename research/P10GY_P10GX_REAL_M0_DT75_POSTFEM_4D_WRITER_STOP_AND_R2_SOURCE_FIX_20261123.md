# P10GY — реальный P10GX STOP в 4D writer; исправление R2 с source-level тестом 12/36 шагов

**23.11.2026. `P10GX_M0_DT75_NATIVE_EXIT2_POST_FEM_4D_WRITER_STOP`; `P10GY_R2_SOURCE_CXX_SELFTEST_DYNAMIC_WRITER_PASS`; новые Windows P10GY физические попытки 0.** Не считать P10GX M0 dt75 валидным 4D результатом, не использовать его для dt-сходимости.

## Первичные данные

- Пользователь прислал `P10GX_PARTIAL_STOP_EVIDENCE.zip`, SHA256 `757dc5043c07e8fc07575fe19c22fa83fd2e8a5d42826d1f68b129ae4499e866`, outer/inner CRC PASS, ровно один вложенный `P10GX_M0_DT75_EVIDENCE.zip` (6865 B). Отдельный `P10GX_02_RESULT.txt` SHA256 `caac4bd2e2844c5f7f7bafad0084793ee138ea79885a353ceacce3c2d5d5d70f`.
- M0 SHA `926a9c903765ce77fd560300d10614d3cece3d4cd4d7813027e45e92d33870d6`; dt75, steps12, R/EDV_VAR/ξ0/t_f=900/B6=5mm. Реальный native solver **exit2** после **241.542099с**, polled peak **1,186,742,272 B**, Job limit8GiB, stop_reason пуст; остановок watchdog/RAM/disk нет. Один persistent marker `LOCAL_RUNS/P10GX_ONE_SHOT_MARKERS/M0_DT75_STEPS12_926a9c903765ce77_01c07d0ef73d.json` израсходован. Не удалять и не повторять R1.
- В `P10GX_SOLVER_LOG.txt` подтверждены обратные 12/12, вплоть до step1, успешные линейные решатели. **Окончательный стоп:** `P10W_ERROR: P10DD requires 6x150s and every step populated`. Не образовались `P10DD_SIGNED_R_THETA_PHI_T.csv` и `P10DD_FULL4D_CLOSURE_AUDIT.csv`, хотя есть глобальные P10W CSV — они не заменяют 4D acceptance.
- Точная причина в **унаследованном** `stage3d10dd_4d_partition.hpp::write_csv`: `if(steps!=6 || dt!=150 || ...) throw` не был расширен в P10GX R1. При первой подготовке P10GX были изменены два C++ параметрических gate (CLI/parse) и один в `stage3d10p_partial_audit.cpp`, но пропущен gate **после дорогостоящего FEM**. Это дефект нашего source QA. Отдельно всё ещё нельзя считать `jpeak` локально временно сошедшимся.

## Исправленный источник P10GY R2

- Новый изолированный ZIP `research/packages/P10GY_R2_M0_M1_SEVEN_DT_FIXED_4D_WRITER_WINDOWS_20261123.zip`, 109 членов, 402105 B, CRC PASS, SHA256 **`08333e669e7e0058693d6db31c63b002706d3440eccec3ee42c126d41fa7aad4`**. Новые `P10GY_ONE_SHOT_MARKERS`; исходные P10GX/past P10GV/P10FN markers, EXE/исходные сетки без изменений.
- Параметрический writer допускает только `6≤steps≤36`, `steps*dt=900` и все заполненные snapshots. Внешний CLI принимает лишь **семь** пар `6×150,12×75,15×60,18×50,20×45,25×36,36×25`; режим сохраняется R, EDV_VAR, ξ0, B6 и analytically differentiable same-mesh. Никакой произвольной многосотшаговой физики, альтернативных mode или неограниченных FEM.
- **Новая обязательная source-level unit** внутри нативного `--selftest`: синтетически вызывает **настоящий `ice3d::p10dd::write_csv`** для 12 и 36 Snapshot intervals, проверяет реально созданные `1201×steps+1` строк, закрытие компонент к нулевому reference; удаляет только собственный временный каталог. Не заменяет проверку физической сходимости.
- В отдельном Linux чистом извлечении исходники source-hash validated; C++20/OpenMP компиляция/линковка PASS; `--selftest` exit0, P10I18/P10W/P10DD/P10FN guards PASS, **`P10GY_DYNAMIC_4D_WRITER_12_36_SELFTEST_OK`** и `P10DD_FULL4D_CLOSURE_OK steps=12/36` наблюдались на реальном writer без FEM. Python source `--selftest` PASS. Исходный уже выполненный P10GV M1 dt150 CSV адаптивный QA был проверен на прошлой стадии, реальных dt75/25 Windows P10GY расчётов ещё 0.

## Следующая операция

Пакет P10GY — **новый отдельный Windows one-click**, а не снятие старого STOP: `01_P10GY_PREFLIGHT_NO_FEM.cmd` затем при PASS `02_P10GY_NEW_12_RUN_CAMPAIGN.cmd`, в новой папке `G:\ildar\Stage3D07\P10GY_TOOLS_R2`. 12 новых расчётов dt75/60/50/45/36/25 на M0/M1, 900с; один свежий marker и bounded fresh forward + same-mesh adjoint на каждую пару; жёсткий Job ≤8GiB, watchdog≤2400с, ≤2GiB outputs, 4 threads, STOP-first без автовозобновления. Ориентир всей кампании 1.5–3ч (при прежнем dt75 M0 фактически 241.5с, но обобщение на остальные уровни приблизительно). Выход **один** `P10GY_12_RUNS_EVIDENCE.zip` либо `P10GY_PARTIAL_STOP_EVIDENCE.zip`; журнал `P10GY_02_RESULT.txt` по необходимости. Передать архив ассистенту, не присылать `forward_history.bin`.

Не удалять/не перезаписывать исходные user data. Не запускать P10GX R1 снова; M2 пока STOP до независимого 4D temporal convergence pilot. Это новый защищённый фикс с более строгим обнаружением ошибки **до** дорогого FEM.
