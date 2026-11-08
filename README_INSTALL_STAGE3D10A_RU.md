# Stage 3D‑10A — дополнительный тест, без замены физического решателя

## Что внутри

- `tests/stage3d10a_local_history_adjoint.cpp` — новый C++20-тест обратного прохода через 12 конститутивных шагов;
- `CMakeLists.txt` — CMake из архива `ICE_3D_SOURCE_20261103_0804.zip` с добавленной целью P10A и CTest;
- `STAGE3D10A_SCIENTIFIC_NOTE_RU.md` — математика, результаты самотеста, ограничения.

**Внимание:** полная программа и расчётные данные не изменялись. Присланный `CMakeLists.txt` основан на исходниках от 03.11.2026. Если ваш `CMakeLists.txt` менялся после выгрузки, **не перезаписывайте его** — добавьте только следующий блок в конец существующего файла:

```cmake
# Stage 3D-10A: independent full-history reverse-mode preflight.
add_executable(stage3d10a_local_history_adjoint tests/stage3d10a_local_history_adjoint.cpp)
target_include_directories(stage3d10a_local_history_adjoint PRIVATE src)
if(MSVC)
 target_compile_options(stage3d10a_local_history_adjoint PRIVATE /O2 /W4)
else()
 target_compile_options(stage3d10a_local_history_adjoint PRIVATE -O2 -Wall -Wextra -Wpedantic)
endif()
add_test(NAME P10A_local_history_reverse_vs_FD COMMAND stage3d10a_local_history_adjoint)
```

## Установка на Windows

1. Сохраните копию действующего `CMakeLists.txt` (один маленький файл, **не** весь каталог 200 ГБ).
2. Закройте/остановите текущие расчёты Qt Creator, если они выполняются.
3. Скопируйте новый файл `tests/stage3d10a_local_history_adjoint.cpp` в `G:\ildar\Stage3D07\tests\` (заменить путь, если проект расположен иначе).
4. Если `CMakeLists.txt` не менялся с выгрузки от 03.11.2026, можно скопировать поставляемый CMakeLists; в противном случае добавьте блок выше вручную, **не заменяя** существующие изменения.
5. Qt Creator → **Desktop MinGW Release** → CMake Reconfigure → собрать цель `stage3d10a_local_history_adjoint` → Run **без аргументов**. Рабочий каталог — обычный для этой цели, специальный `--root` не нужен.

Ожидается шесть строк `P10A_CASE_OK ...` и итоговая строка:

```text
P10A_LOCAL_HISTORY_ADJOINT_OK models=6 steps=12 reverse_vs_full_history_FD
```

**Оценка времени:** выполнение теста — ориентировочно менее 5 секунд, сборка на i7‑7700K/MinGW Release обычно до 1–2 минут. RAM — малая (десятки МБ), выходных массивов FEM/VTU нет.

Если результат не совпадёт, пришлите **один** текст консоли с сообщением `P10A_...`, а не архив всей папки. Если совпадёт, достаточно написать `P10A_LOCAL_HISTORY_ADJOINT_OK`.

## Не перепутать смысл теста

Параметр `a` в тесте — синтетический параметр истории деформации и температуры. Он **не** реализует нормальную вариацию сферической поры y20. Тест доказывает согласованность дискретной обратной рекурсии с FD полного локального пути на 12 шагах в проверенных случаях, **не** работоспособность глобального adjoint и не точность производных формы.
