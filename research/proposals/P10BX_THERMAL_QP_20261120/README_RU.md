# P10BX — изолированная opt-in интеграция thermal QP в P10P/P10W

**Статус:** исследовательское предложение, проверенное компиляцией и синтетическим native unit. **Не применять в рабочем Windows-дереве автоматически.** 20.11.2026.

## Состав

- `src/stage3d10p_partial_audit.cpp` — полная копия точного P10P Git blob `b1bab7385e86928306617a4ec930d31e9b478a3f` с ограниченными вставками под `STAGE3D10BX_THERMAL_QP_DIAGNOSTIC`. Без флага числовая схема обратного шага сохранена; битовая эквивалентность на реальном FEM не заявлена.
- `src/stage3d10w_analytic_adjoint.cpp` — неизменённая копия точного оригинального P10W Git blob `0cf185831f82c885ca6b60ce35aa32057f6623dc`; нужна, чтобы quoted include нашёл локальный P10BX P10P в этом каталоге.
- `stage3d10bx_thermal_step_hook.hpp` — контракт между исходным `CSR D.mass,D.conduct,D.robinload` и ранее проверенным `p10bw::contract_step`. Проверяет отдельно массу, остальное как `diffusion+Robin`, и полный результат с `abs_error <= 1e-10 + 1e-8*scale`.
- `P10BX_thermal_step_native_unit.cpp` — 7 синтетических режимов (R: dt=150,75,50,25; tz/y20 dt=150; moving-top dt=75) + 1 отрицательная проверка некорректного размера; без FEM. Повторно использует исходный тест P10BW.

Зависимости: **неизменённые** `src/` и `tests/` из исторического Git commit `90fd2559c0224ac0a7d2dbe2fe081a6a319080e4`, а также опубликованные P10BW `stage3d10bw_thermal_qp_partition.hpp` и `P10BW_thermal_qp_native_unit.cpp` из `research/proposals/P10BW_THERMAL_QP_20261120/`. При сборке include-пути должны указывать на обе директории.

## Режим исполнения и CSV

Внутри исходного `p10n::reverse_scan` после **штатного** теплового `H::solve`, только для `jpeak` (`obs==1`) и единственной аналитической скорости P10W, вычисляется QP-срез с теми же `psi_n, theta_n, theta_(n-1), dt, ambient_n` и `D.shape`. Исходный CSR-сумматор **остаётся вычисляющим** `result[k][obs].thermal`, поверх него идёт проверка. Суммы проверяются по шагам и по полной истории. Флаг выключен в штатной P10W.

При будущем *отдельно разрешённом* физическом запуске программа должна создать:

1. `P10BX_THERMAL_STEP_AUDIT.csv` — по одной строке `jpeak` на шаг; исходные CSR mass/(conduct включая Robin)/(load), QP mass/diffusion/Robin/total, абсолютная и нормированная невязки, допуск, число QP/объём и Robin-площадь;
2. `P10BX_THERMAL_QP_STEP_BINS.csv` — 100 объёмных radial×polar ячеек на шаг, *плюс* одна отдельная строка top Robin `shell_bin=-1, polar_bin=-1`; thermal Tet10 — 64 QP, Tri6 — 16 QP.

**Эти CSV пока НЕ получены:** real-mesh `reverse_scan` намеренно не запускался. Измеренные 8/8 — только operator unit.

## Пример только синтетического native unit

В отдельном чистом каталоге Linux с указанными header/include деревьями:

```sh
g++ -std=c++20 -O2 -Wall -Wextra -Wpedantic \
  -I <pinned>/src -I <P10BX> -I <P10BW> \
  <P10BX>/P10BX_thermal_step_native_unit.cpp -o p10bx_unit
./p10bx_unit
```

Для P10W диагностической компиляции применить `-DSTAGE3D10BX_THERMAL_QP_DIAGNOSTIC`, `-I <pinned>/src -I <pinned>/tests -I <P10BX> -I <P10BW>` к `<P10BX>/src/stage3d10w_analytic_adjoint.cpp`, и определить `STAGE3D10K_SOURCE_ROOT` как точный абсолютный путь к clean source. **Только `--selftest`** без физической сетки. `--preflight` запрещён на этой стадии: уже вызывает физический тепловой `solve_forward`.

Точный протокол, результаты и ограничения: `research/P10BX_THERMAL_QP_OPTIN_INTEGRATION_20261120.md` и `research/evidence/P10BX_NATIVE_INTEGRATION_20261120/derived/`.

## Запреты

Это **proposal**, не коммит в штатные `src/`, не Windows-инсталлятор, не разрешение на FEM и не оценка погрешности физического решения. Не смешивать с пользовательским dirty Git деревом или историческим H2 EXE. Перед любым реальным H0/H2 требуется отдельное согласование протокола, времени/памяти и текущих SHA/dirty-state; D-012 остаётся.
