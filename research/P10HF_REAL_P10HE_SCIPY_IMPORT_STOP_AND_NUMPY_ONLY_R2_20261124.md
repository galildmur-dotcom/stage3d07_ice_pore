# P10HF — реальный P10HE STOP на импорте SciPy; исправленный автономный NumPy R2

**24.11.2026. `P10HE_R1_IMPORT_STOP`; `NO_MESH_OR_FEM`; `P10HF_R2_SOURCE_QA_PASS`; `USER_NATIVE_R2_PENDING`.**

Исходное сообщение исследователя после однократного запуска прежнего `01_P10HE_BUILD_POSTVIEW_NO_MESH.cmd`:

```text
File "...P10HE_build_view.py", line 22, in <module>
  import p10hc_continuous_kappa_geo as field
File "...p10hc_continuous_kappa_geo.py", line 19, in <module>
  from scipy.spatial import cKDTree
ModuleNotFoundError: No module named 'scipy'
```

На Windows модуль `numpy` до этого импортировался успешно, `scipy` отсутствует. Это **наша техническая ошибка упаковки зависимостей**, а не отказ исследовательского метода PostView. Исходная программа остановилась **до** чтения pinned M1 evidence, обработки данных, создания `.pos` и native Gmsh; ни один one-shot marker не расходован. Не требовать от исследователя установки scipy; прежний P10HE R1 ZIP/исходные markers оставить неизменными и больше не запускать.

## Исправление без изменения математики κ

Из центрального source `scripts/p10hc_continuous_kappa_geo.py` удалена зависимость `scipy.spatial.cKDTree`. Функция `rbf_at_points` теперь использует только `numpy`:

1. В 4D нормированных координатах `u,x_dir,y_dir,z_dir` сначала точно отбрасываются кандидаты с `|Δu|>=1`; такие центры **математически не могут попадать в компактный support** ядра радиуса1.
2. Для остальных сохраняется исходное полное 4D расстояние `q`, функция Вендланда `W(q)=(1−q)^4_+(4q+1)`, 25/36 общий нормирующий множитель, epsilon `1e−12`, диапазон `[0,1]` и механические веса P10HB.
3. В исходном 1200-bin selftest `max |κ_numpy−κ_P10HA|≈3.2·10⁻¹³`.
4. Независимый parity unit-test исследовательского окружения против **старой SciPy KDTree реализации** на 1200 исходных центрах и 2000 воспроизводимых псевдослучайных физических точках: `max |κ_numpy−κ_scipy|<10⁻¹²`, PASS. SciPy используется только в локальном тесте сравнения и **отсутствует в Windows R2**.
5. Контрольная выборка 13 978 произвольных физических x/y/z точек обработана NumPy-only за **≈0.35с в нашем Linux окружении**; это не измерение на пользовательском i7-7700K.

Исходный механический 4D научный выбор M0/M1, C² сглаживание, CAD и M1 Tet10 не изменены. Истинная source-to-PostView передача пока в R2 не выполнена на Windows; C⁰ хордовую интерполяцию и mid-edge QA требуется отдельно проверить по оригинальной M1 (как в P10HE).

## Новый Windows пакет R2

`research/proposals/P10HF_P10HE_NUMPY_ONLY_20261124/P10HF_R2_P10HE_NUMPY_ONLY_SOURCE_WINDOWS_20261124.zip`, SHA256 **`7ba5e608b80ca07003030f64b8b9acf5e6f9ea380a5528d26a0809958d022b1c`**, 10 файлов, архив CRC и byte-content check PASS; исходный P10HE R1 ZIP SHA `944efa01831948aac6a95ac95f9cb05cb9397acea758bc708fef8ccc8cfbc2c7` архивно неизменён.

Единственный Windows запуск в новом каталоге: `01_P10HF_POSTVIEW_NO_SCIPY.cmd`. Сначала NumPy-only selftest на всех 1200 source bins; только после PASS тот же source-only P10HE builder прочитает прежнее pinned M1 evidence, создаст scalar `SS` 3D PostView по Tet10 и выполнит Gmsh 4.15.2 только `-parse_and_exit` с timeout120с. **Никакого Gmsh -1/-2/-3, FEM или повторного физического M1**. Отправить `P10HE_SOURCE_ONLY_EVIDENCE.zip` из нового каталога P10HF R2 или точный вывод экрана при остановке до evidence.

Результат пока не M2 GO. Строгость D-025 15–25% реального локального объёма, polar/off-polar controls, 343/729QP и отдельный физический GO остаются обязательными.
