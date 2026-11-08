# Stage 3D‑10B — установка аналитической линеаризации EDV

Предусловие: Stage 3D‑10A уже установлен, запуск `stage3d10a_local_history_adjoint` дал `P10A_LOCAL_HISTORY_ADJOINT_OK`.

## Состав архива

- `src/stage3d10b_edv_linearization.hpp` — аналитический JVP/VJP, **не изменяет** `edv_material.hpp`;
- `tests/stage3d10b_edv_linearization.cpp` — 144 направленных проверки, нулевое q и 12-шаговый аналитический adjoint;
- `CMakeLists.txt` — состояние исходного CMake от 03.11.2026 с дополнениями P10A и P10B;
- `STAGE3D10B_SCIENTIFIC_NOTE_RU.md` — математика, тесты и ограничения.

**Не перезаписывайте действующий `CMakeLists.txt`, если он изменялся после установки 10A.** Надёжнее скопировать два новых файла и добавить следующий небольшой блок к уже существующему CMake:

```cmake
# Stage 3D-10B: analytic JVP and Euclidean-Voigt VJP of E/ED/EDV update.
add_executable(stage3d10b_edv_linearization tests/stage3d10b_edv_linearization.cpp)
target_include_directories(stage3d10b_edv_linearization PRIVATE src)
if(MSVC)
 target_compile_options(stage3d10b_edv_linearization PRIVATE /O2 /W4)
else()
 target_compile_options(stage3d10b_edv_linearization PRIVATE -O2 -Wall -Wextra -Wpedantic)
endif()
add_test(NAME P10B_EDV_analytic_JVP_VJP COMMAND stage3d10b_edv_linearization)
```

## Точные действия в Qt Creator

1. Скопировать `src/stage3d10b_edv_linearization.hpp` в `G:\ildar\Stage3D07\src\` и `tests/stage3d10b_edv_linearization.cpp` в `G:\ildar\Stage3D07\tests\` (пути заменить при другом расположении).
2. Добавить указанный CMake-блок в существующий корневой `CMakeLists.txt`.
3. Qt Creator → **Desktop MinGW Release** → CMake Reconfigure → собрать только **`stage3d10b_edv_linearization`**.
4. Запустить эту цель **без аргументов**. Рабочий каталог — стандартный для цели, параметр `--root` не нужен.
5. Ожидаемая строка:

```text
P10B_EDV_LINEARIZATION_OK models=6 scenes=2 directions=144 ...
```

**Примерное время:** сам тест ориентировочно менее 5 секунд; сборка этой цели в Qt Creator на i7‑7700K — примерно 1–2 минуты. ОЗУ — десятки мегабайт. Расчётов МКЭ нет.

Если всё прошло, достаточно прислать одну итоговую строку `P10B_EDV_LINEARIZATION_OK ...` из консоли. Если нет — полный текст ошибки компиляции или запуска, не весь каталог проекта.

Текущая добавка не изменяет физическую модель, временную интеграцию, сетки HP и проверенные результаты Stage 3D‑09G.
