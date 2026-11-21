# P10BF: протокол C++-совместимости после получения `stage3d10v_analytic_shape.hpp`

Дата: 19.11.2026. Контрольная среда: Linux, g++ (Debian) 14.2.0, `-std=c++20`. **Без CMake, MinGW, Windows и большого FEM.**

## Проверяемые исходники

Полный путь ниже дан относительно корня GitHub-дерева. Файлы архивного пользовательского снимка сохраняют оригинальные байты, не подменяют базовую ветку `src/`:

| Файл в `research/sources/P10BF_UNCOMMITTED_20261118/` | SHA-256 |
|---|---|
| `CMakeLists.txt` | `453f41a086b1284a7c4da4bba2e343b106edae602adc2ee180fa9fd91abbbddf` |
| `src/stage3d10p_partial_audit.cpp` | `73cdbf9ee75de9f32ae8490baeedd760b00797670a4c6c869277405e45963f7a` |
| `src/stage3d10w_analytic_adjoint.cpp` | `70873515734edaa42ce96366e636fa6c385a114cd08564817b283fadeccdcd46` |
| `src/stage3d10az_probe_export.hpp` | `9bf6b9729da9e2ff698ef8f890fcc88b8d3fb2ef787708992605a72d0ec8e57d` |
| `src/stage3d10ba_polar_export.hpp` | `92b81c258b11fad8ccd4915d215f567cbdf61b642c61e9dbe47732b294ead373` |
| `src/stage3d10v_analytic_shape.hpp` | `ad9b5f8d24dcbbbd7678a01a32ef5947e198173c779c7e4efe1da48beca4f7e3` |
| `tests/stage3d10v_analytic_shape.cpp` | `f5c70aba380da9a45c234b33c8ac2f90879d1d59784033a759b7193ab111ca12` |

Пять исходников из первоначального ZIP некоммиченны относительно пользовательского Windows HEAD `c0498f6dc98628b62eff996a76844297c7a35094`; два дополнительно переданных заголовка получены позже. Приписывать всем семи исходникам чистый Git HEAD или конкретный исторический `.exe` запрещено.

## Тест 1 — Tet10/unit с максимально включёнными опциями

Запускается из корня репозитория, оригинальные файлы не редактируются:

```bash
snapshot=research/sources/P10BF_UNCOMMITTED_20261118
g++ -std=c++20 -O1 -w -I"$snapshot/src" -Isrc \
 -DSTAGE3D10Y_ANALYTIC_SHELL_AUDIT -DSTAGE3D10AZ_QP_PROBE \
 -DSTAGE3D10BA_POLAR_AUDIT -DSTAGE3D10BD_TEMPORAL_AUDIT \
 -DSTAGE3D10BE_TEMPORAL_AUDIT \
 "$snapshot/tests/stage3d10v_analytic_shape.cpp" -o /tmp/p10bf_complete_unit
/tmp/p10bf_complete_unit
```

В предыдущем опыте unit подставлял старый канонический `src/stage3d10v_analytic_shape.hpp` и заканчивался `error: 'QpProbe' in namespace 'ice3d::p10v' does not name a type`. Теперь новый P10V лежит в `snapshot/src`, который компилятор использует для заголовков теста, и исходная ошибка устранена.

Фактический вывод (exit code 0):

```text
P10V_ANALYTIC_SHAPE_UNIT residual_rel=5.4808975582e-09 history_rel=3.0865921973e-07 functional_rel=2.5227648913e-06 models=6 functionals=4 quadrature_points=27
P10V_ANALYTIC_SHAPE_UNIT_OK
P10Y_ANALYTIC_SHELL_UNIT_OK models=6 functionals=4 bins=2
P10AZ_QP_PROBE_UNIT_OK objective=1 equilibrium=1 history=1 csv_output=1 repeated_append=1
P10BA_POLAR_UNIT_OK equal_area=1 qp_coordinates=1 400_rows=1 shell_radial_parity=1
P10BD_TEMPORAL_UNIT_OK schedules=3 all_step_polar_rows=1200,2400,3600 original_p10ba_preserved=1
P10BE_TEMPORAL_UNIT_OK schedules=4 dt25_steps=36 polar_rows=7200 audit_rows=72 legacy_p10bd_preserved=1
```

## Тест 2 — исходник production/P10BE и `--selftest`

Точный исходник — `snapshot/src/stage3d10w_analytic_adjoint.cpp`; он включает `snapshot/src/stage3d10p_partial_audit.cpp`. Компиляция с максимальными определениями P10BE, Linux `-O0` (отдельно от Windows Release):

```bash
snapshot=research/sources/P10BF_UNCOMMITTED_20261118
g++ -std=c++20 -O0 -w -I"$snapshot/src" -Isrc -Itests \
 -DSTAGE3D06_ROOT_DIR='"."' \
 -DSTAGE3D10Y_ANALYTIC_SHELL_AUDIT -DSTAGE3D10S_SPATIAL_AUDIT \
 -DSTAGE3D10AZ_QP_PROBE -DSTAGE3D10BA_POLAR_AUDIT \
 -DSTAGE3D10BD_TEMPORAL_AUDIT -DSTAGE3D10BE_TEMPORAL_AUDIT \
 "$snapshot/src/stage3d10w_analytic_adjoint.cpp" -o /tmp/p10bf_production_selftest
/tmp/p10bf_production_selftest --selftest
```

Фактический вывод (exit code 0):

```text
P10I_PRODUCTION_ADJOINT_OK models=6 functionals=3 cases=18 replayed_steps=216 max_window=4 j6_temp_FD_rel=3.195489345685e-10 j6_shape_FD_rel=2.967581909493e-07 jpeak_temp_FD_rel=8.102737341419e-11 jpeak_shape_FD_rel=5.595618775652e-08 jen_temp_FD_rel=2.184810646703e-10 jen_shape_FD_rel=4.433433409555e-08 gauge_functional_rel=6.452189131574e-16 dropped_history_rel=6.388824166451e-01 adjoint_equilibrium_rel=5.967189189981e-13
P10W_DEPENDENCY_SELFTEST_OK analytic_coupling_verified=0
P10Y_SHELL_BINS_SELFTEST_OK bins=10
P10BD_TEMPORAL_BINS_SELFTEST_OK allowed_dt=150,75,50 horizon_s=900
P10BE_TEMPORAL_BINS_SELFTEST_OK allowed_dt=25 steps=36 horizon_s=900
```

`STAGE3D06_ROOT_DIR` заменяет строковый путь, задаваемый обычным CMake; первый компиляционный тест без его определения остановился только на этой недостающей переменной сборочной среды, не на новой зависимости P10V. В самой CMake-конфигурации архивного снимка путь задаётся `STAGE3D10K_SOURCE_ROOT`.

`P10W_DEPENDENCY_SELFTEST_OK analytic_coupling_verified=0` **не доказывает** саму полную аналитическую связку: это selftest уже существующей зависимости P10I. Отдельный P10V unit выше проверяет дискретную производную Tet10, но не полноценную пространственную сходимость трёхмерной формы.

## Результат и ограничения

1. Ранее недостающий `p10v::QpProbe` найден в подлинном пользовательском файле; обе контрольные C++ программы компилируются и проходят тесты.
2. Все семь архивированных файлов имеют зарегистрированные SHA-256. Исходные P10BB CSV и итоговые таблицы не менялись.
3. Полный граф CMake целей P10AZ/BA/BD/BE, линковка MinGW Release и реальный запускаемый P10BE FEM **не проверялись**. Исторические Windows `.exe` нельзя доказательно привязать к этим семи файлам.
4. Контрольный набор составлен наложением пользовательского снимка на более старые текущие базовые `src/` GitHub. Это проверка интерфейсной совместимости, а не доказательство идентичности всего локального пользовательского Git дерева.
5. Следующий инженерный этап — безопасно согласовать и проверить перенос в канонические `src/`/`tests/`/`CMakeLists.txt`, получив при необходимости подтверждение актуального локального HEAD; затем запустить Windows MinGW/CMake unit и preflight. Тяжёлые FEM-эксперименты для самого устранения пробела исходников не нужны.
