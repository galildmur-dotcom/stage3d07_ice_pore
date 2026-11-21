# P10BO — исходный Windows отчёт о действительной Qt Creator toolchain

Дата 19.11.2026. Пользователь приложил **оригинальный** `P10BO_TOOLCHAIN_REPORT.txt`: **992 байта**, SHA-256 `7887b95b6910880e02ac350a7442aa14a8c58e5762ff852ecf28c4eb3d9f300b`. Побайтовая копия в `input/`. Статус `RESULT=P10BO_TOOLCHAIN_AUDIT_OK_NO_BUILD`; скрипт только читал CMakeCache/метаданные компилятора/доступность программ, не выполнял clone, build, тесты или FEM.

## Проверенные значения первичного отчёта

| Поле | Значение |
|---|---|
| Local time | `2026-11-19T17:23:00.7704761+05:00` |
| Project root | `G:\ildar\Stage3D07` |
| Старый `CMAKE_GENERATOR` | `NMake Makefiles JOM` |
| Старый `CMAKE_MAKE_PROGRAM` | `jom` (имя, не абсолютный путь) |
| Старый `CMAKE_CXX_COMPILER` | `C:/mingw64/bin/g++.exe`, `CACHED_COMPILER_EXISTS=True` |
| `CMAKE_CXX_COMPILER_ID` | `GNU` |
| `CMAKE_CXX_COMPILER_VERSION` | `13.1.0` |
| `CMAKE_CXX_PLATFORM_ID` | `MinGW` |
| `CMAKE_BUILD_TYPE` / OpenMP | `Release` / `ON` |
| CMake / Git PATH | `C:\Program Files\CMake\bin\cmake.exe` / `C:\Program Files\Git\cmd\git.exe` |
| Tools missing **from PATH** | `ninja.exe`, `mingw32-make.exe`, `jom.exe`, `g++.exe`, `cl.exe` |

**Важная трактовка:** хотя `PATH_g++.exe=NOT_FOUND`, абсолютный компилятор `C:/mingw64/bin/g++.exe` **существует**. Отсутствие `mingw32-make.exe` в `PATH` **не доказывает**, что его нет непосредственно в `C:\mingw64\bin`. Аналогично `CACHED_MAKE_EXISTS=False` для строки `jom` означает, что относительное имя `jom` не было найдено как путь при `Test-Path`; это не доказательство отсутствия JOM во всех папках Qt Creator. Метаданные GNU/MinGW получены из старого созданного CMake файла; наличие компилятора не доказывает недавний clean rebuild.

## Следующее техническое решение

Согласно [CMake MinGW Makefiles](https://cmake.org/cmake/help/latest/generator/MinGW%20Makefiles.html), для новой отдельной сборки GNU MinGW подходит генератор **`MinGW Makefiles`**, если доступна программа `mingw32-make.exe` и её каталог добавлен в `PATH` процесса. Менять существующий старый `NMake Makefiles JOM` каталог **не нужно**: новые CMakeCache и build должны создаваться в независимом checkout Git SHA `90fd2559c0224ac0a7d2dbe2fe081a6a319080e4`.

Подготовлен отдельный `tools/P10BP_MINGW_CLEAN_BUILD_ONECLICK_20261119.zip`, который **до clone/build** проверяет `C:\mingw64\bin\mingw32-make.exe`, точную GNU 13.1.0/MinGW compiler и неизменившуюся старую JOM конфигурацию. Если make отсутствует, он прекращает работу с отчётом; ничего не скачивает и не меняет. Только после preflight ручное `BUILD P10BP` создаёт независимый GitHub clone/build и четыре коротких теста.

**Статус P10BP:** код подготовлен, ещё не выполнялся Windows. Следующий ожидаемый первичный файл — **один `P10BP_EVIDENCE.zip`**. Исторические EXE P10BE не аттестованы, новых FEM/CSV нет; полная пространственная сходимость геометрической производной не доказана.
