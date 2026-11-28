# P10IB R2 — мгновенное закрытие CMD при Windows запуске

Пользователь сообщил, что окно P10IB R1 сразу закрывается, артефактов пока не прислал. Подтверждён дефект UX лаунчера: в `01_P10IB_ONE_ORIGINAL_CAD_2D_NO_FEM.cmd` есть `exit /b` на всех выходах, без `pause`, при двойном щелчке вывод исчезает. Это не доказывает причину отказа Python/Gmsh.

Исправление R2: `research/proposals/P10IB_ORIGINAL_CAD_2D_20261124/01_P10IB_R2_DIAGNOSTIC_REPLACEMENT.cmd`. Скопировать его поверх старого CMD (переименовать в `01_P10IB_ONE_ORIGINAL_CAD_2D_NO_FEM.cmd`), остальные данные P10IB R1 не менять. R2 сохраняет `P10IB_LAUNCH_DIAGNOSTICS.txt`, всегда оставляет окно открытым посредством `pause`, проверяет `where python`, `python --version`, `import gmsh`, **не запускает guard если `P10IB_ONE_2D_ATTEMPT_CONSUMED.marker` существует**. Если маркер отсутствует, запускается исходный однократный guard. При STOP вернуть диагностику и существующие guard/log/error, без ручного перезапуска исходного процесса. 3D/FEM=0.

Пока Windows evidence отсутствует: исходную физическую причину старта не утверждать. Модель M2 и D-029 остаются STOP.
