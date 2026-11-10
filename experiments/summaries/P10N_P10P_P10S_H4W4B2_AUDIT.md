# Контрольные результаты P10N/P10P/P10S — сетка H4W4B2

Источник: консольные строки, присланные исследователем 2026-11-08. Привязка к исходным CSV, физическому run_id, хешам сетки и версии Git ожидается.

## Префлайт

`nodes=367823`, `tet10=261091`, `pore_tri6=19140`, `pore_median_edge_mm=3.93760646225e-02`, `B6_volume_m3=9.00581528234e-07`, `steps=6`, `dt=150`, `deltas=1`.

Оценка занимаемой памяти из префлайта: `history_gib=3.78162342310`, `state_buffers_gib=6.30270570517`. На префлайте `nonlinear_forward_solves=0`. Для `delta_um=2.5` сообщено `thermal_matrix_parity=1.81807257430e-07`.

## P10S

```text
P10S_SPATIAL_PARTITION_OK mesh=H4W4B2 deltas=1 steps=6 bins=10 step_shell_rows=180 worst_partition_rel=2.60518887645e-10 nonlinear_forward_solves=1 mechanical_adjoint_solves=18
```

## P10P

```text
P10P_COMPONENT_AUDIT_OK mesh=H4W4B2 deltas=1 steps=6 nonlinear_forward_solves=1 mechanical_adjoint_solves=18 worst_component_partition_rel=9.65732140602e-13 step_component_rows=18
```

## P10N

```text
P10N_DELTA_SCAN_OK mesh=H4W4B2 deltas=1 steps=6 dt=150 nonlinear_forward_solves=1 reused_forward=0 mechanical_adjoint_solves=18 max_mechanical_equilibrium_rel=1.67003125241e-08 max_thermal_equilibrium_rel=4.90854828792e-11 checkpoint_roundtrip_bitwise=1 wall_s=1.35655147876e+04
```

Время: `13565.5147876 s ≈ 3 ч 46 мин 6 с`.

## Статус интерпретации

Пройдены встроенные тесты компонентного и пространственного разложения и проверка сохранения/восстановления состояния. **Нельзя из этих строк заключить**, что производная по форме пространственно сошлась или что основной алгоритм уже избавлен от центральных конечных разностей. Следующий методический приоритет — аналитические/AD геометрические частные производные, затем независимая проверка и сеточное исследование.
