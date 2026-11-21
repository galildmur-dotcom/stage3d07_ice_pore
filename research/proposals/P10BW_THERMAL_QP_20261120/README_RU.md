# P10BW — только предложение диагностического исходного модуля

**НЕ загружать и не вставлять автоматически в `G:\ildar\Stage3D07`.** Этот
каталог содержит проверенный изолированный C++ header и нативный unit, **не**
внедрённую производственную модификацию и **не** инструкцию нового FEM-запуска.

Файлы:

1. `stage3d10bw_thermal_qp_partition.hpp` — потоковое разложение аналитического
   теплового контракта ψᵀ dA на 10×10 физических областей и отдельную верхнюю
   Robin-грань, точно по 64 точкам Tet10 и 16 точкам Tri6.
2. `P10BW_thermal_qp_native_unit.cpp` — нативная C++ проверка против оригинального
   P10L CSR и отдельного центрального FD **только в unit**.

Для независимой Linux-сборки требуется положить в отдельную временную папку
`pinned/` две **точные Git blob** (скачивать из отдельной истории GitHub commit
`90fd2559c0224ac0a7d2dbe2fe081a6a319080e4`, не из произвольного ZIP):

- `geometry_stage3d01.cpp` blob `5bd5928efb20a9e1cd846398fc629dcbfbf4fcca`;
- `stage3d10l_thermal_adjoint.hpp` blob `2169d1b7602a68f336900d9be3e02861d48582f3`.

Из каталога, содержащего подкаталоги `pinned/` и `proposal/`:

```bash
g++ -std=c++20 -O2 -Wall -Wextra -Wpedantic -I pinned -I proposal \
  proposal/P10BW_thermal_qp_native_unit.cpp -o P10BW_thermal_qp_native_unit
./P10BW_thermal_qp_native_unit
```

Ожидается `P10BW_EXACT_P10L_QP_PARTITION_UNIT_OK tests=7 FEM=0
production_patch_applied=NO`. На других компиляторах результат не заявлен до
их запуска. Подробные ограничения и научные выводы —
`research/P10BW_EXACT_P10L_THERMAL_QP_NATIVE_UNIT_20261120.md`.

**Не выполнять FEM или изменений Windows Git в рамках P10BW.** Для будущей
интеграции в P10P/Qt Creator сначала проверить точную текущую базу и получить
утверждение на соответствующий объём работы/ресурс.
