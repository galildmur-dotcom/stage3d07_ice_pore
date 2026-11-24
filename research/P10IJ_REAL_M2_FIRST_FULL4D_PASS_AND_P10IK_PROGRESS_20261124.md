# P10IJ real M2 signed-4D FEM PASS; P10IK progress contract

**Первый реальный M2 FEM+same-mesh analytic adjoint завершён, НЕ является окончательной оценкой сеточной сходимости.**

Исходное Windows evidence: `P10IJ_M2_FIRST_FULL4D_EVIDENCE.zip`, SHA256 `c81ac925d4e8d585f473847fd5f5b05b746111992608d77bef173c1d40535e74`. Это пользовательский локальный архив, содержащий производные физические CSV; публиковать сам ZIP отдельно только по явному решению и после проверки необходимости. Независимый повторный разбор содержимого через pinned `P10GY_temporal_series.independent_time_audit` прошёл (не доверять одному status в manifest).

## Прямая физика и аналитическая сопряжённая

- M2 SHA `d1ec65ffcc6e8fac7da925ecd66bbb9508450cf2ea837521442f57f45674c78b`, 9840 Tet10, 14305 nodes, curvature samples PASS, теги 2..9.
- Режим `R / EDV_VAR / ξ=0 / B6 cutoff 5 мм / t_final 900с / dt25с ×36 / 4 threads`, новая прямая история, согласованное аналитическое сопряжение на M2, FD геометрии=0.
- `native_exit_code=0`, `wall_s=905.9076845` (15 мин 5.9 с), `peak_private_bytes_polled=2103156736` (~2005.7 MiB), 8 GiB Job cap, ни одного STOP.
- Полные 4D CSV: 43236 строк = 1201×36; 1200 volume spatial bins плюс top Robin на шаг; независимое temporal QP и component closure PASS.
- `D_R jpeak(M2)=+2.559851025083483 м⁻¹`, против `M1 dt25 +2.628806049 м⁻¹` из P10GZ. `Δ(M2−M1)=−0.068955023917 м⁻¹` (−2.62305% от M1).
- Шесть signed составляющих M2 (м⁻¹): mechanical explicit −13.625454301975077; equilibrium +10.001428570997493; history +6.1111075534158905; thermal mass +0.0012249395849417946; thermal diffusion +0.07154426306023433; top Robin 0.0. Их сумма даёт +2.559851025083483.
- Локальная временная 4D сходимость пока не доказана по P10GZ. Нельзя выводить из одного глобального Δ=−2.62% локальную сеточную сходимость. Следующая физическая научная задача: независимо сравнить M1→M2 все 1200 spatial bins, раздельно 6 signed компонентов, приполюсную κ-поддержанную область и временные uncertainty flags.

## P10IK — обязательные сообщения в окне для будущих Windows пакетов

По отзыву пользователя в P10IJ R2 последней видимой строкой многие минуты оставалась `P10FR_COMPILE_SUCCESS: running EXE guard selftest`, хотя по `taskmgr` реально работал final `stage3d10fn_any_mesh_full4d.exe` с ~38% CPU/1.98 GB; в предыдущем runner отсутствовала строка запуска FEM и видимый монитор, но `capped_process` контролировал Job/время/выходные файлы. P10IJ M2 одноразовый marker **израсходован**; ни старый, ни новый скрипт не запускают на той же M2 повторно.

В исходник будущего launcher добавлен `ProgressHeartbeat` (test `SYNTHETIC_NO_FEM` PASS):

1. `P10IK_STAGE_START COMPILE_AND_EXE_SELFTEST` и `P10IK_STAGE_END ...` с временем;
2. `P10IK_NATIVE_FEM_START ... one_shot_consumed=1` сразу после markers, перед `Popen`;
3. каждые **30 с** `P10IK_HEARTBEAT NATIVE_FEM elapsed_s=... log_bytes=...` (не выдавать число шагов/процентов из ничего);
4. `P10IK_NATIVE_FEM_END exit=... wall_s=... peak_private_MiB=... stop_reason=...`;
5. существующие time/memory/output Job ограничения и одноразовая политика не изменены.

Проверен только Python heartbeat и пассивный монитор; **новая сборка Windows с этим интерфейсом НЕ запускалась**. На следующей новой сетке включить этот код в следующий пакет и отдельно выполнить preflight QA, прежде чем разрешать FEM. Нет необходимости выпускать новый физический пакет M2 ради интерфейса.
