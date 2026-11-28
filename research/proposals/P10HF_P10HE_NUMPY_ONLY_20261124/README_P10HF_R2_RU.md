# P10HF R2 — исправление отсутствующего SciPy в P10HE R1

Ошибка первого Windows запуска `ModuleNotFoundError: No module named 'scipy'` — **недостаток исходного пакета**, а не ошибка пользователя или M1. Исправлено вычисление C² поля через уже установленный `numpy`. **Не нужно устанавливать scipy и не повторяйте прежний P10HE R1**.

1. Распакуйте новый ZIP `P10HF_R2_P10HE_NUMPY_ONLY_SOURCE_WINDOWS_20261124.zip` в новую папку, например `G:\ildar\Stage3D07\P10HF_TOOLS_R2`.
2. Запустите один файл `01_P10HF_POSTVIEW_NO_SCIPY.cmd` (двойной щелчок). Сначала проходит независимый `1200-bin` NumPy selftest без обращения к mesh; затем построение source-only PostView из **старого** P10GT M1 evidence, как в предыдущем пакете.
3. Пришлите `P10HE_SOURCE_ONLY_EVIDENCE.zip` из папки P10HF R2 (если STOP, тот же архив с QA). При ошибке до создания архива пришлите текст окна.

Потребуется только Python3+numpy (по вашему прошлому traceback NumPy уже импортировался успешно). Исходный `P10GT_HXT10_EVIDENCE.zip` SHA `7bff029865bd69e12b8302a9f65b6159d61f58163300fdee81555954988a6ac3` будет найден автоматически среди ранее сохранённых доказательств в `G:\ildar\Stage3D07\LOCAL_RUNS`, `G:\ildar\Stage3D07\P10GT_TOOLS_R1` или `G:\Downloads`. Никогда не перезапускайте старую M1 физику.

Геометрия M1 и исходный C² mechanical κ не изменены. Построение `PostView` в 9 623 линейных tetra-chords по четырём вершинам — **пока только C⁰ диагностическая интерполяция**; отчет отдельно проверит её ошибку в midside Tet10. Native Gmsh4.15.2 запускается только `-parse_and_exit` (timeout 120с); не будет ни новых 1D/2D/3D сеток, ни FEM, ни расходования старых one-shot markers.
