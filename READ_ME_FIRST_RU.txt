STAGE 3D-06 -- новый запуск H1/EDV_VAR с временным шагом 75 с (Qt Creator)

1. Сохраните резервную копию CMakeLists.txt и src/qt_creator_runner.cpp.
2. Распакуйте содержимое ЭТОГО PATCH в корневую папку вашего существующего проекта Stage3D06.
   Заменяются только CMakeLists.txt и src/qt_creator_runner.cpp.
   LOCAL_RUNS, meshes, результаты, проверки и бинарные контрольные точки НЕ включены в ZIP.
3. В Qt Creator выберите MinGW Release; перезапустите конфигурацию CMake.
4. Соберите проект Ctrl+B.
5. Выберите цель stage3d06_qt_H1_dt75 и запустите Ctrl+R.
6. Параметры: H1, EDV, VAR, xi=0, quad=3, dt=75 s, tend=3600 s (48 шагов).
7. Результаты: LOCAL_RUNS/H1_dt75_q3/{thermal,mechanics/EDV_VAR}.
8. По окончании приложите G06_campaign.csv и EDV_VAR/time_series.csv.

Не используйте --clean, если хотите сохранить предыдущие результаты.
Проект и физическая модель не изменены, добавлена только ещё одна CMake-цель
с конфигурацией по умолчанию. Linux GCC Release сборка и dry-run нового
запускателя проверены. Реальная 48-шаговая серия H1/EDV_VAR в этом патче
пока не запускалась. Проверка Windows/MinGW выполняется на компьютере пользователя.
