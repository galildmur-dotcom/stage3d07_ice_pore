# Проверка fallback без OpenMP

Linux GCC 14.2 Release, `-DSTAGE3D06P_OPENMP=OFF`: собраны `stage3d06_spatial` и `stage3d06_benchmark_optimized`, прошёл H0 E_CONST q3 t=300 при `--threads 1 --parallel-assembly on`; `stage3d06_benchmark_optimized --dry-run` также прошёл. Когда OpenMP не найден, нативная Qt-цель по умолчанию использует 1 поток. Сценарий с `--threads 4` в такой сборке корректно отвергается.
