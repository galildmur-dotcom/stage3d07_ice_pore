# Stage 3D-06-P5: протокол проверки

- Сборка GCC 14.2 Release C++20, OpenMP ON/OFF: PASS.
- Пять независимых unit-тестов и два `Qt --dry-run`: 7/7 PASS c OpenMP; 7/7 PASS без OpenMP.
- Реальная H0 FEM-регрессия для E/ED/EDV и CONST/VAR, Jacobi/AS0/AS1: 12/12 сравнений checkpoint PASS при допуске 1e-6.
- H2 EDV/VAR Jacobi/AS0 checkpoint: PASS, см. H2_CHECKPOINT.csv.
- Выигрыша по времени полного шага нет, Jacobi остаётся базовым.
- Linux измерения из одного и того же набора исходников и тепловых данных, нативную Windows сборку проверить самостоятельно.
