cmake_minimum_required(VERSION 3.20)
project(Stage3D06SpatialRheology LANGUAGES CXX)
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
add_executable(stage3d03_mechanical src/mechanical.cpp)
add_executable(stage3d02_thermal src/thermal.cpp)
if(MSVC)
  target_compile_options(stage3d03_mechanical PRIVATE /O2 /W4)
  target_compile_options(stage3d02_thermal PRIVATE /O2 /W4)
else()
  target_compile_options(stage3d03_mechanical PRIVATE -O3 -Wall -Wextra -Wpedantic)
  target_compile_options(stage3d02_thermal PRIVATE -O3 -Wall -Wextra -Wpedantic)
endif()
enable_testing()
add_test(NAME MAT_T01_T02_T03_T06 COMMAND stage3d03_mechanical --mode material --out ${CMAKE_CURRENT_BINARY_DIR}/material)
add_test(NAME G03_01_affine_patch COMMAND stage3d03_mechanical --mesh ${CMAKE_CURRENT_SOURCE_DIR}/meshes/H0.msh --mode patch --out ${CMAKE_CURRENT_BINARY_DIR}/patch)
add_test(NAME MAT_T05_heterogeneous_manufactured COMMAND stage3d03_mechanical --mesh ${CMAKE_CURRENT_SOURCE_DIR}/meshes/SLAB3D_G02.msh --mode mms --out ${CMAKE_CURRENT_BINARY_DIR}/mms)
add_test(NAME G03_01_Candidate_A_slab COMMAND stage3d03_mechanical --mesh ${CMAKE_CURRENT_SOURCE_DIR}/meshes/SLAB3D_G02.msh --mode slab --out ${CMAKE_CURRENT_BINARY_DIR}/slab)
add_test(NAME MAT_T04_same_temperature_reference COMMAND stage3d03_mechanical --mesh ${CMAKE_CURRENT_SOURCE_DIR}/meshes/SLAB3D_G02.msh --mode tref --out ${CMAKE_CURRENT_BINARY_DIR}/tref)

add_test(NAME G03_01_free_rigid_modes COMMAND stage3d03_mechanical --mesh ${CMAKE_CURRENT_SOURCE_DIR}/meshes/H0.msh --mode rigid --out ${CMAKE_CURRENT_BINARY_DIR}/rigid)
add_test(NAME G03_01_pure_free_expansion COMMAND stage3d03_mechanical --mesh ${CMAKE_CURRENT_SOURCE_DIR}/meshes/H0.msh --mode pure --out ${CMAKE_CURRENT_BINARY_DIR}/pure)

# Stage 3D-04: independent ED material-point implementation and verification.
# The ED material module is also used by Stage 3D-06 spatial FEM.
add_executable(stage3d04_ed_point tests/ed_point.cpp)
target_include_directories(stage3d04_ed_point PRIVATE src)
if(MSVC)
  target_compile_options(stage3d04_ed_point PRIVATE /O2 /W4)
else()
  target_compile_options(stage3d04_ed_point PRIVATE -O2 -Wall -Wextra -Wpedantic)
endif()
foreach(test_case reference relaxation recovery tangent temperature energy objectivity restart)
  add_test(NAME G04_${test_case} COMMAND stage3d04_ed_point --test ${test_case})
endforeach()

# Stage 3D-05: E+ED+EDV nonlinear material point, isolated from spatial Tet10 solver.
add_executable(stage3d05_edv_point tests/edv_point.cpp)
target_include_directories(stage3d05_edv_point PRIVATE src)
if(MSVC)
  target_compile_options(stage3d05_edv_point PRIVATE /O2 /W4)
else()
  target_compile_options(stage3d05_edv_point PRIVATE -O2 -Wall -Wextra -Wpedantic)
endif()
foreach(test_case reference implicit tangent temperature energy objectivity stress_control limits restart temporal)
  add_test(NAME G05_${test_case} COMMAND stage3d05_edv_point --test ${test_case})
endforeach()

# Stage 3D-06: coupled-in-time 3D equilibrium for E, ED and EDV.
add_executable(stage3d06_spatial src/spatial_reology.cpp)
if(MSVC)
  target_compile_options(stage3d06_spatial PRIVATE /O2 /W4)
else()
  target_compile_options(stage3d06_spatial PRIVATE -O3 -Wall -Wextra -Wpedantic)
endif()
if(WIN32)
  # Separate Windows headers from C++20 FEM/material headers (byte/CONST clashes).
  target_sources(stage3d06_spatial PRIVATE src/win_process_memory.cpp)
  target_link_libraries(stage3d06_spatial PRIVATE Psapi)
endif()
add_test(NAME G06_H0_E_smoke_900 COMMAND stage3d06_spatial
  --mesh ${CMAKE_CURRENT_SOURCE_DIR}/meshes/H0.msh
  --temp-dir ${CMAKE_CURRENT_SOURCE_DIR}/results/H0_dt300_xi0
  --out ${CMAKE_CURRENT_BINARY_DIR}/G06_smoke
  --law E --modulus CONST --times 900)
find_package(Python3 COMPONENTS Interpreter QUIET)
if(Python3_Interpreter_FOUND)
 add_test(NAME G06_H0_72_steps_and_legacy_parity
  COMMAND ${Python3_EXECUTABLE} ${CMAKE_CURRENT_SOURCE_DIR}/scripts/check_stage06.py
  --campaign ${CMAKE_CURRENT_SOURCE_DIR}/results/G06_H0_dt300
  --reference ${CMAKE_CURRENT_SOURCE_DIR}/results
  --out ${CMAKE_CURRENT_BINARY_DIR}/G06_check.json)
endif()
if(Python3_Interpreter_FOUND)
 add_test(NAME G06_EDV_checkpoint_bitwise_resume
  COMMAND ${Python3_EXECUTABLE} ${CMAKE_CURRENT_SOURCE_DIR}/scripts/test_restart_stage06.py
  --executable $<TARGET_FILE:stage3d06_spatial>
  --mesh ${CMAKE_CURRENT_SOURCE_DIR}/meshes/H0.msh
  --temperature ${CMAKE_CURRENT_SOURCE_DIR}/results/G06_thermal_H0_dt300)
endif()

# Native Qt Creator launch targets. These are console executables, with no Qt API
# dependency. Select a target in Qt Creator and press Run; no external shell needed.
set(STAGE3D06_ROOT_DIR "${CMAKE_CURRENT_SOURCE_DIR}")
configure_file(src/qt_runner_paths.hpp.in
    "${CMAKE_CURRENT_BINARY_DIR}/generated/qt_runner_paths.hpp" @ONLY)
foreach(qt_target IN ITEMS stage3d06_qt_check stage3d06_qt_run stage3d06_qt_H1 stage3d06_qt_H0_dt300 stage3d06_qt_H0_dt150 stage3d06_qt_H0_dt75 stage3d06_qt_H1_dt150 stage3d06_qt_H1_dt75 stage3d06_qt_H2_dt150 stage3d06_qt_diagnose_H1 stage3d06_qt_diagnose_H2)
    add_executable(${qt_target} src/qt_creator_runner.cpp)
    target_include_directories(${qt_target} PRIVATE "${CMAKE_CURRENT_BINARY_DIR}/generated")
    add_dependencies(${qt_target} stage3d02_thermal stage3d06_spatial)
    if(MSVC)
        target_compile_options(${qt_target} PRIVATE /W4 /O2)
    else()
        target_compile_options(${qt_target} PRIVATE -O2 -Wall -Wextra -Wpedantic)
    endif()
endforeach()
target_compile_definitions(stage3d06_qt_check PRIVATE STAGE3D06_SMOKE_DEFAULT=1)
target_compile_definitions(stage3d06_qt_H1 PRIVATE STAGE3D06_H1_DEFAULT=1)
add_test(NAME G06_QT_native_launcher_dryrun COMMAND stage3d06_qt_run --dry-run)
add_test(NAME G06_QT_H1_launcher_dryrun COMMAND stage3d06_qt_H1 --dry-run)
# End-to-end short integration test: the exact Run path used by Qt Creator.
add_test(NAME G06_QT_native_H0_E_chain COMMAND stage3d06_qt_check)
set_tests_properties(G06_QT_native_H0_E_chain PROPERTIES RUN_SERIAL TRUE)

# Direct-run, reproducible temporal-refinement presets (same mesh, quadrature and xi=0).
target_compile_definitions(stage3d06_qt_H0_dt300 PRIVATE STAGE3D06_H0_DT300_DEFAULT=1)
target_compile_definitions(stage3d06_qt_H0_dt150 PRIVATE STAGE3D06_H0_DT150_DEFAULT=1)
target_compile_definitions(stage3d06_qt_H0_dt75 PRIVATE STAGE3D06_H0_DT75_DEFAULT=1)
target_compile_definitions(stage3d06_qt_H1_dt150 PRIVATE STAGE3D06_H1_DT150_DEFAULT=1)
target_compile_definitions(stage3d06_qt_H1_dt75 PRIVATE STAGE3D06_H1_DT75_DEFAULT=1)
target_compile_definitions(stage3d06_qt_H2_dt150 PRIVATE STAGE3D06_H2_DT150_DEFAULT=1)
add_test(NAME G06_QT_H0_dt150_preset_dryrun COMMAND stage3d06_qt_H0_dt150 --dry-run)
add_test(NAME G06_QT_H0_dt75_preset_dryrun COMMAND stage3d06_qt_H0_dt75 --dry-run)
add_test(NAME G06_QT_H1_dt150_preset_dryrun COMMAND stage3d06_qt_H1_dt150 --dry-run)
add_test(NAME G06_QT_H1_dt75_preset_dryrun COMMAND stage3d06_qt_H1_dt75 --dry-run)
add_test(NAME G06_QT_H2_dt150_preset_dryrun COMMAND stage3d06_qt_H2_dt150 --dry-run)

target_compile_definitions(stage3d06_qt_diagnose_H1 PRIVATE STAGE3D06_H1_QP_POST_DEFAULT=1)
target_compile_definitions(stage3d06_qt_diagnose_H2 PRIVATE STAGE3D06_H2_QP_POST_DEFAULT=1)
add_test(NAME G06_QT_H1_QP_post_dryrun COMMAND stage3d06_qt_diagnose_H1 --dry-run)
add_test(NAME G06_QT_H2_QP_post_dryrun COMMAND stage3d06_qt_diagnose_H2 --dry-run)
if(Python3_Interpreter_FOUND)
  add_test(NAME G06_QP_checkpoint_postprocess_consistency
    COMMAND ${Python3_EXECUTABLE} ${CMAKE_CURRENT_SOURCE_DIR}/scripts/test_qp_postprocess.py
    --exe $<TARGET_FILE:stage3d06_spatial> --root ${CMAKE_CURRENT_SOURCE_DIR})
endif()

# 2026-10-10 scientific refinement campaign (native Qt Creator CPU launch, no PowerShell).
foreach(campaign_target IN ITEMS stage3d06_campaign_plan stage3d06_campaign_phase1 stage3d06_campaign_phase2 stage3d06_campaign_phase3 stage3d06_campaign_full)
  add_executable(${campaign_target} src/refinement_campaign.cpp)
  target_include_directories(${campaign_target} PRIVATE "${CMAKE_CURRENT_BINARY_DIR}/generated")
  add_dependencies(${campaign_target} stage3d06_qt_run)
endforeach()
target_compile_definitions(stage3d06_campaign_plan PRIVATE STAGE3D06_CAMPAIGN_PLAN=1)
target_compile_definitions(stage3d06_campaign_phase1 PRIVATE STAGE3D06_CAMPAIGN_PHASE=1)
target_compile_definitions(stage3d06_campaign_phase2 PRIVATE STAGE3D06_CAMPAIGN_PHASE=2)
target_compile_definitions(stage3d06_campaign_phase3 PRIVATE STAGE3D06_CAMPAIGN_PHASE=3)
add_test(NAME G06_REFINEMENT_H3_H4_PLAN COMMAND stage3d06_campaign_plan)

add_executable(stage3d06_convergence_report src/refinement_report.cpp)
target_include_directories(stage3d06_convergence_report PRIVATE "${CMAKE_CURRENT_BINARY_DIR}/generated")

# Stage3D06-P: optional OpenMP. Without it code stays serial and numerical model is unchanged.
option(STAGE3D06P_OPENMP "Enable parallel PCG operations" ON)
if(STAGE3D06P_OPENMP)
 find_package(OpenMP COMPONENTS CXX QUIET)
 if(OpenMP_CXX_FOUND)
  target_link_libraries(stage3d06_spatial PRIVATE OpenMP::OpenMP_CXX)
 endif()
endif()
# Explicit physical baseline retained in a separate, pristine source tree below.
# Native Qt Creator benchmark targets are provided in subsequent package patches.

# Frozen last received Stage3D06 source, compiled separately from all P patches.
add_executable(stage3d06_baseline_serial baseline_serial/spatial_reology.cpp)
if(MSVC)
 target_compile_options(stage3d06_baseline_serial PRIVATE /O2 /W4)
else()
 target_compile_options(stage3d06_baseline_serial PRIVATE -O3 -Wall -Wextra -Wpedantic)
endif()
if(WIN32)
 target_sources(stage3d06_baseline_serial PRIVATE baseline_serial/win_process_memory.cpp)
 target_link_libraries(stage3d06_baseline_serial PRIVATE Psapi)
endif()

foreach(benchmark IN ITEMS stage3d06_benchmark_serial stage3d06_benchmark_optimized stage3d06_campaign_optimized)
 add_executable(${benchmark} src/qt_benchmark_p.cpp)
 target_include_directories(${benchmark} PRIVATE "${CMAKE_CURRENT_BINARY_DIR}/generated")
 add_dependencies(${benchmark} stage3d02_thermal stage3d06_spatial stage3d06_baseline_serial)
endforeach()
target_compile_definitions(stage3d06_benchmark_serial PRIVATE STAGE3D06P_RUN_BASELINE=1)
target_compile_definitions(stage3d06_campaign_optimized PRIVATE STAGE3D06P_RUN_CAMPAIGN=1)
add_test(NAME P06_QT_baseline_preset COMMAND stage3d06_benchmark_serial --dry-run)
add_test(NAME P06_QT_optimized_preset COMMAND stage3d06_benchmark_optimized --dry-run)
add_test(NAME P06_QT_campaign_preset COMMAND stage3d06_campaign_optimized --dry-run)
if(Python3_Interpreter_FOUND)
 set(STAGE3D06P_TEST_THREADS 1)
 if(STAGE3D06P_OPENMP AND OpenMP_CXX_FOUND)
  set(STAGE3D06P_TEST_THREADS 4)
 endif()
 add_test(NAME P06_H0_EDV_4threads_numeric_regression
  COMMAND ${Python3_EXECUTABLE} ${CMAKE_CURRENT_SOURCE_DIR}/scripts/p06_test_h0.py
  --baseline $<TARGET_FILE:stage3d06_baseline_serial>
  --optimized $<TARGET_FILE:stage3d06_spatial>
  --mesh ${CMAKE_CURRENT_SOURCE_DIR}/meshes/H0.msh
  --temp-dir ${CMAKE_CURRENT_SOURCE_DIR}/results/G06_thermal_H0_dt300 --threads ${STAGE3D06P_TEST_THREADS})
 set_tests_properties(P06_H0_EDV_4threads_numeric_regression PROPERTIES TIMEOUT 120)
endif()

# Serial fallback for Windows Kits without a usable OpenMP runtime.
if(NOT STAGE3D06P_OPENMP OR NOT OpenMP_CXX_FOUND)
 foreach(t IN ITEMS stage3d06_benchmark_optimized stage3d06_campaign_optimized)
  target_compile_definitions(${t} PRIVATE STAGE3D06P_NO_OPENMP=1)
 endforeach()
endif()

# Stage 3D-06-P2: isolated SpMV kernel verification + throughput benchmark.
add_executable(stage3d06_spmv_benchmark tests/p2_spmv_benchmark.cpp)
if(MSVC)
 target_compile_options(stage3d06_spmv_benchmark PRIVATE /O2 /W4)
else()
 target_compile_options(stage3d06_spmv_benchmark PRIVATE -O3 -Wall -Wextra -Wpedantic)
endif()
if(STAGE3D06P_OPENMP AND OpenMP_CXX_FOUND)
 target_link_libraries(stage3d06_spmv_benchmark PRIVATE OpenMP::OpenMP_CXX)
endif()
add_test(NAME P2_SpMV_H0_1thread_correctness
 COMMAND stage3d06_spmv_benchmark --mesh ${CMAKE_CURRENT_SOURCE_DIR}/meshes/H0.msh --repeats 3 --threads 1 --tolerance 1e-12)
if(STAGE3D06P_OPENMP AND OpenMP_CXX_FOUND)
 add_test(NAME P2_SpMV_H0_4thread_correctness
  COMMAND stage3d06_spmv_benchmark --mesh ${CMAKE_CURRENT_SOURCE_DIR}/meshes/H0.msh --repeats 3 --threads 4 --tolerance 1e-12)
endif()

# Two independent Qt Creator launchers, each with its own result directory.
foreach(name IN ITEMS stage3d06_benchmark_p2_legacy stage3d06_benchmark_p2_projected)
 add_executable(${name} src/qt_benchmark_p.cpp)
 target_include_directories(${name} PRIVATE "${CMAKE_CURRENT_BINARY_DIR}/generated")
 add_dependencies(${name} stage3d02_thermal stage3d06_spatial)
 if(MSVC)
  target_compile_options(${name} PRIVATE /O2 /W4)
 else()
  target_compile_options(${name} PRIVATE -O2 -Wall -Wextra -Wpedantic)
 endif()
endforeach()
target_compile_definitions(stage3d06_benchmark_p2_legacy PRIVATE STAGE3D06P_P2_RUN_LEGACY=1)
target_compile_definitions(stage3d06_benchmark_p2_projected PRIVATE STAGE3D06P_P2_RUN_PROJECTED=1)
add_test(NAME P2_QT_legacy_dryrun COMMAND stage3d06_benchmark_p2_legacy --dry-run)
add_test(NAME P2_QT_projected_dryrun COMMAND stage3d06_benchmark_p2_projected --dry-run)

add_executable(stage3d06_compare_restart tools/stage3d06_compare_restart.cpp)
target_compile_features(stage3d06_compare_restart PRIVATE cxx_std_20)
if(MSVC)
 target_compile_options(stage3d06_compare_restart PRIVATE /O2 /W4)
else()
 target_compile_options(stage3d06_compare_restart PRIVATE -O3 -Wall -Wextra -Wpedantic)
endif()
add_test(NAME P2_Checkpoint_self_compare
 COMMAND stage3d06_compare_restart
 --baseline ${CMAKE_CURRENT_SOURCE_DIR}/LOCAL_RUNS/H0_dt300_q3/mechanics/E_CONST/restart.bin
 --optimized ${CMAKE_CURRENT_SOURCE_DIR}/LOCAL_RUNS/H0_dt300_q3/mechanics/E_CONST/restart.bin
 --output ${CMAKE_CURRENT_BINARY_DIR}/P2_checkpoint_self_compare.csv)
if(Python3_Interpreter_FOUND)
 add_test(NAME P2_H0_EDV_projected_legacy_regression
 COMMAND ${Python3_EXECUTABLE} ${CMAKE_CURRENT_SOURCE_DIR}/scripts/p2_test_h0.py
 --solver $<TARGET_FILE:stage3d06_spatial>
 --mesh ${CMAKE_CURRENT_SOURCE_DIR}/meshes/H0.msh
 --temp-dir ${CMAKE_CURRENT_SOURCE_DIR}/results/G06_thermal_H0_dt300
 --threads ${STAGE3D06P_TEST_THREADS})
 set_tests_properties(P2_H0_EDV_projected_legacy_regression PROPERTIES TIMEOUT 150)
endif()
if(Python3_Interpreter_FOUND)
 add_test(NAME P2_H0_all_E_ED_EDV_CONST_VAR
 COMMAND ${Python3_EXECUTABLE} ${CMAKE_CURRENT_SOURCE_DIR}/scripts/p2_test_all6.py
 --solver $<TARGET_FILE:stage3d06_spatial>
 --mesh ${CMAKE_CURRENT_SOURCE_DIR}/meshes/H0.msh
 --temp-dir ${CMAKE_CURRENT_SOURCE_DIR}/results/G06_thermal_H0_dt300
 --threads ${STAGE3D06P_TEST_THREADS})
 set_tests_properties(P2_H0_all_E_ED_EDV_CONST_VAR PROPERTIES TIMEOUT 180)
endif()

# Stage 3D-06-P3: symmetric multi-color block SGS tests (same C++20 implementation).
add_executable(stage3d06_p3_mcsgs_unit tests/p3_mcsgs_unit.cpp)
target_include_directories(stage3d06_p3_mcsgs_unit PRIVATE "${CMAKE_CURRENT_SOURCE_DIR}/src")
if(MSVC)
 target_compile_options(stage3d06_p3_mcsgs_unit PRIVATE /O2 /W4)
else()
 target_compile_options(stage3d06_p3_mcsgs_unit PRIVATE -O3 -Wall -Wextra -Wpedantic)
endif()
if(STAGE3D06P_OPENMP AND OpenMP_CXX_FOUND)
 target_link_libraries(stage3d06_p3_mcsgs_unit PRIVATE OpenMP::OpenMP_CXX)
endif()
add_test(NAME P3_MCSGS_small_1thread COMMAND stage3d06_p3_mcsgs_unit --small)
add_test(NAME P3_MCSGS_parallel_large COMMAND stage3d06_p3_mcsgs_unit --parallel)
add_test(NAME P3_MCSGS_Tet10_adjacent_cliques COMMAND stage3d06_p3_mcsgs_unit --tet10)
if(Python3_Interpreter_FOUND)
 add_test(NAME P3_H0_all6_Jacobi_MCSGS_regression
  COMMAND ${Python3_EXECUTABLE} ${CMAKE_CURRENT_SOURCE_DIR}/scripts/p3_test_h0.py
  --solver $<TARGET_FILE:stage3d06_spatial>
  --mesh ${CMAKE_CURRENT_SOURCE_DIR}/meshes/H0.msh
  --thermal $<TARGET_FILE:stage3d02_thermal>
  --compare $<TARGET_FILE:stage3d06_compare_restart>
  --threads ${STAGE3D06P_TEST_THREADS})
 set_tests_properties(P3_H0_all6_Jacobi_MCSGS_regression PROPERTIES TIMEOUT 600)
endif()
# Self-contained, shell-free, two-stage native Qt Creator launcher;
# it generates the matching thermal history, then performs the FEM analysis.
# Separate P3 directory; old P2 results are never overwritten.
foreach(target IN ITEMS stage3d06_p3_qt_H0_mcsgs stage3d06_p3_qt_H4_mcsgs)
 add_executable(${target} src/qt_benchmark_p.cpp)
 target_include_directories(${target} PRIVATE "${CMAKE_CURRENT_BINARY_DIR}/generated")
 target_compile_definitions(${target} PRIVATE STAGE3D06P_P3_RUN_MCSGS=1)
 add_dependencies(${target} stage3d02_thermal stage3d06_spatial)
 if(MSVC)
  target_compile_options(${target} PRIVATE /O2 /W4)
 else()
  target_compile_options(${target} PRIVATE -O2 -Wall -Wextra -Wpedantic)
 endif()
endforeach()
target_compile_definitions(stage3d06_p3_qt_H0_mcsgs PRIVATE STAGE3D06P_P3_H0_DEFAULT=1)
target_compile_definitions(stage3d06_p3_qt_H4_mcsgs PRIVATE STAGE3D06P_P3_H4_DEFAULT=1)
if(NOT STAGE3D06P_OPENMP OR NOT OpenMP_CXX_FOUND)
 foreach(target IN ITEMS stage3d06_p3_qt_H0_mcsgs stage3d06_p3_qt_H4_mcsgs)
  target_compile_definitions(${target} PRIVATE STAGE3D06P_NO_OPENMP=1)
 endforeach()
endif()
add_test(NAME P3_QT_H0_mcsgs_dryrun COMMAND stage3d06_p3_qt_H0_mcsgs --dry-run)
add_test(NAME P3_QT_H4_mcsgs_dryrun COMMAND stage3d06_p3_qt_H4_mcsgs --dry-run)
# Stage3D06-P3: MC-SGS integration

# Stage 3D-06-P3.1 indexed-color CSR: separate reproducible Qt Creator target.
# Original P3 and P2 targets remain unchanged.
add_executable(stage3d06_p31_qt_H0_mcsgs_fast src/qt_benchmark_p.cpp)
target_include_directories(stage3d06_p31_qt_H0_mcsgs_fast PRIVATE "${CMAKE_CURRENT_BINARY_DIR}/generated")
target_compile_definitions(stage3d06_p31_qt_H0_mcsgs_fast PRIVATE
 STAGE3D06P_P31_RUN_MCSGS_FAST=1 STAGE3D06P_P3_H0_DEFAULT=1)
add_dependencies(stage3d06_p31_qt_H0_mcsgs_fast stage3d02_thermal stage3d06_spatial)
if(MSVC)
 target_compile_options(stage3d06_p31_qt_H0_mcsgs_fast PRIVATE /O2 /W4)
else()
 target_compile_options(stage3d06_p31_qt_H0_mcsgs_fast PRIVATE -O2 -Wall -Wextra -Wpedantic)
endif()
if(NOT STAGE3D06P_OPENMP OR NOT OpenMP_CXX_FOUND)
 target_compile_definitions(stage3d06_p31_qt_H0_mcsgs_fast PRIVATE STAGE3D06P_NO_OPENMP=1)
endif()
add_test(NAME P31_QT_H0_fast_dryrun COMMAND stage3d06_p31_qt_H0_mcsgs_fast --dry-run)
if(Python3_Interpreter_FOUND)
 add_test(NAME P31_H0_all6_reference_fast_checkpoint
 COMMAND ${Python3_EXECUTABLE} ${CMAKE_CURRENT_SOURCE_DIR}/scripts/p31_test_h0.py
 --solver $<TARGET_FILE:stage3d06_spatial>
 --mesh ${CMAKE_CURRENT_SOURCE_DIR}/meshes/H0.msh
 --thermal $<TARGET_FILE:stage3d02_thermal>
 --compare $<TARGET_FILE:stage3d06_compare_restart>
 --threads ${STAGE3D06P_TEST_THREADS})
 set_tests_properties(P31_H0_all6_reference_fast_checkpoint PROPERTIES TIMEOUT 600)
endif()

# Stage3D06-P4: block incomplete Cholesky IC(0), experimental SPD preconditioner.
add_executable(stage3d06_p4_ic0_unit tests/p4_ic0_unit.cpp)
target_include_directories(stage3d06_p4_ic0_unit PRIVATE "${CMAKE_CURRENT_SOURCE_DIR}/src")
if(MSVC)
 target_compile_options(stage3d06_p4_ic0_unit PRIVATE /O2 /W4)
else()
 target_compile_options(stage3d06_p4_ic0_unit PRIVATE -O3 -Wall -Wextra -Wpedantic)
endif()
add_test(NAME P4_IC0_exact_block_tridiagonal COMMAND stage3d06_p4_ic0_unit --exact)
add_test(NAME P4_IC0_mixed_dirichlet_and_spd COMMAND stage3d06_p4_ic0_unit --mixed)
add_test(NAME P4_IC0_breakdown_rejected COMMAND stage3d06_p4_ic0_unit --breakdown)
add_executable(stage3d06_p4_qt_H0_ic0 src/qt_benchmark_p.cpp)
target_include_directories(stage3d06_p4_qt_H0_ic0 PRIVATE "${CMAKE_CURRENT_BINARY_DIR}/generated")
target_compile_definitions(stage3d06_p4_qt_H0_ic0 PRIVATE STAGE3D06P_P4_RUN_IC0=1 STAGE3D06P_P3_H0_DEFAULT=1)
add_dependencies(stage3d06_p4_qt_H0_ic0 stage3d02_thermal stage3d06_spatial)
if(MSVC)
 target_compile_options(stage3d06_p4_qt_H0_ic0 PRIVATE /O2 /W4)
else()
 target_compile_options(stage3d06_p4_qt_H0_ic0 PRIVATE -O2 -Wall -Wextra -Wpedantic)
endif()
if(NOT STAGE3D06P_OPENMP OR NOT OpenMP_CXX_FOUND)
 target_compile_definitions(stage3d06_p4_qt_H0_ic0 PRIVATE STAGE3D06P_NO_OPENMP=1)
endif()
add_test(NAME P4_QT_H0_ic0_dryrun COMMAND stage3d06_p4_qt_H0_ic0 --dry-run)
if(Python3_Interpreter_FOUND)
 add_test(NAME P4_H0_all6_Jacobi_IC0_regression
 COMMAND ${Python3_EXECUTABLE} ${CMAKE_CURRENT_SOURCE_DIR}/scripts/p4_test_h0.py
  --solver $<TARGET_FILE:stage3d06_spatial>
  --mesh ${CMAKE_CURRENT_SOURCE_DIR}/meshes/H0.msh
  --thermal $<TARGET_FILE:stage3d02_thermal>
  --compare $<TARGET_FILE:stage3d06_compare_restart>
  --threads ${STAGE3D06P_TEST_THREADS})
 set_tests_properties(P4_H0_all6_Jacobi_IC0_regression PROPERTIES TIMEOUT 600)
endif()

# Stage3D06-P5: one-level additive Schwarz (AS0 disjoint / AS1 graph overlap).
add_executable(stage3d06_p5_schwarz_unit tests/p5_schwarz_unit.cpp)
target_include_directories(stage3d06_p5_schwarz_unit PRIVATE "${CMAKE_CURRENT_SOURCE_DIR}/src")
if(MSVC)
 target_compile_options(stage3d06_p5_schwarz_unit PRIVATE /O2 /W4)
else()
 target_compile_options(stage3d06_p5_schwarz_unit PRIVATE -O3 -Wall -Wextra -Wpedantic)
endif()
if(STAGE3D06P_OPENMP AND OpenMP_CXX_FOUND)
 target_link_libraries(stage3d06_p5_schwarz_unit PRIVATE OpenMP::OpenMP_CXX)
endif()
foreach(case_name IN ITEMS partition symmetric mixed_spd threads regression)
 add_test(NAME P5_AS_${case_name} COMMAND stage3d06_p5_schwarz_unit --${case_name})
endforeach()
foreach(method IN ITEMS as0 as1)
 add_executable(stage3d06_p5_qt_H0_${method} src/qt_benchmark_p.cpp)
 target_include_directories(stage3d06_p5_qt_H0_${method} PRIVATE "${CMAKE_CURRENT_BINARY_DIR}/generated")
 add_dependencies(stage3d06_p5_qt_H0_${method} stage3d02_thermal stage3d06_spatial)
 if(method STREQUAL "as0")
  target_compile_definitions(stage3d06_p5_qt_H0_${method} PRIVATE STAGE3D06P_P5_RUN_AS0=1 STAGE3D06P_P3_H0_DEFAULT=1)
 else()
  target_compile_definitions(stage3d06_p5_qt_H0_${method} PRIVATE STAGE3D06P_P5_RUN_AS1=1 STAGE3D06P_P3_H0_DEFAULT=1)
 endif()
 if(NOT STAGE3D06P_OPENMP OR NOT OpenMP_CXX_FOUND)
  target_compile_definitions(stage3d06_p5_qt_H0_${method} PRIVATE STAGE3D06P_NO_OPENMP=1)
 endif()
 add_test(NAME P5_QT_H0_${method}_dryrun COMMAND stage3d06_p5_qt_H0_${method} --dry-run)
endforeach()
if(Python3_Interpreter_FOUND)
 add_test(NAME P5_H0_physical_regression
 COMMAND ${Python3_EXECUTABLE} ${CMAKE_CURRENT_SOURCE_DIR}/scripts/p5_test_h0.py
 --solver $<TARGET_FILE:stage3d06_spatial>
 --mesh ${CMAKE_CURRENT_SOURCE_DIR}/meshes/H0.msh
 --thermal $<TARGET_FILE:stage3d02_thermal>
 --compare $<TARGET_FILE:stage3d06_compare_restart>
 --threads ${STAGE3D06P_TEST_THREADS})
 set_tests_properties(P5_H0_physical_regression PROPERTIES TIMEOUT 600)
endif()

# Stage 3D-07A: read-only inventory of existing H0-H4 histories and checkpoints.
# Standalone native tool for Qt Creator: no solver, Python, Qt runtime or OpenMP required.
add_executable(stage3d07_inventory src/stage3d07_inventory.cpp)
target_include_directories(stage3d07_inventory PRIVATE "${CMAKE_CURRENT_BINARY_DIR}/generated")
if(MSVC)
  target_compile_options(stage3d07_inventory PRIVATE /O2 /W4)
else()
  target_compile_options(stage3d07_inventory PRIVATE -O2 -Wall -Wextra -Wpedantic)
endif()
add_test(NAME P07_inventory_help COMMAND stage3d07_inventory --help)
if(Python3_Interpreter_FOUND)
 add_test(NAME P07_inventory_synthetic_regression
  COMMAND ${Python3_EXECUTABLE} ${CMAKE_CURRENT_SOURCE_DIR}/tests/p07_inventory_regression.py
          $<TARGET_FILE:stage3d07_inventory>)
endif()

# Stage 3D-07D: checkpoint-only fixed physical shell QP stress postprocessor.
# Uses the original Tet10 and EDV implementation but does NOT time-step.
add_executable(stage3d07d_shells src/stage3d07d_shells.cpp)
target_include_directories(stage3d07d_shells PRIVATE "${CMAKE_CURRENT_BINARY_DIR}/generated")
if(MSVC)
 target_compile_options(stage3d07d_shells PRIVATE /O2 /W4)
else()
 target_compile_options(stage3d07d_shells PRIVATE -O2 -Wall -Wextra -Wpedantic)
endif()
if(WIN32)
 target_sources(stage3d07d_shells PRIVATE src/win_process_memory.cpp)
 target_link_libraries(stage3d07d_shells PRIVATE Psapi)
endif()
add_test(NAME P07D_help COMMAND stage3d07d_shells --help)
add_test(NAME P07D_dry_run_no_timestepping COMMAND stage3d07d_shells --dry-run)
if(Python3_Interpreter_FOUND)
 add_test(NAME P07D_synthetic_stress_checkpoint
  COMMAND ${Python3_EXECUTABLE} ${CMAKE_CURRENT_SOURCE_DIR}/tests/p07d_synthetic_stress.py
   --postprocessor $<TARGET_FILE:stage3d07d_shells>
   --mesh ${CMAKE_CURRENT_SOURCE_DIR}/meshes/H0.msh)
 set_tests_properties(P07D_synthetic_stress_checkpoint PROPERTIES TIMEOUT 180)
endif()

# Stage 3D-07E: same checkpoint-only postprocessor with C1 smoothed observation
# zones and exact-geometry volume reference. Does NOT alter P07D or solver.
add_executable(stage3d07e_smooth src/stage3d07d_shells.cpp)
target_compile_definitions(stage3d07e_smooth PRIVATE STAGE3D07E_SMOOTH=1)
target_include_directories(stage3d07e_smooth PRIVATE "${CMAKE_CURRENT_BINARY_DIR}/generated")
if(MSVC)
 target_compile_options(stage3d07e_smooth PRIVATE /O2 /W4)
else()
 target_compile_options(stage3d07e_smooth PRIVATE -O3 -Wall -Wextra -Wpedantic)
endif()
if(WIN32)
 target_sources(stage3d07e_smooth PRIVATE src/win_process_memory.cpp)
 target_link_libraries(stage3d07e_smooth PRIVATE Psapi)
endif()
add_test(NAME P07E_help COMMAND stage3d07e_smooth --help)
add_test(NAME P07E_dry_run_no_timestepping COMMAND stage3d07e_smooth --dry-run)
if(Python3_Interpreter_FOUND)
 add_test(NAME P07E_synthetic_checkpoint_and_volumes
  COMMAND ${Python3_EXECUTABLE} ${CMAKE_CURRENT_SOURCE_DIR}/tests/p07e_synthetic_smooth.py
   --postprocessor $<TARGET_FILE:stage3d07e_smooth>
   --mesh ${CMAKE_CURRENT_SOURCE_DIR}/meshes/H0.msh
   --legacy $<TARGET_FILE:stage3d07d_shells>)
 set_tests_properties(P07E_synthetic_checkpoint_and_volumes PROPERTIES TIMEOUT 180)
endif()

# Stage 3D-08A: independent geometry shape modes, no physical timestepping.
add_executable(stage3d08_geometry src/stage3d08_geometry.cpp)
target_include_directories(stage3d08_geometry PRIVATE "${CMAKE_CURRENT_BINARY_DIR}/generated")
if(MSVC)
 target_compile_options(stage3d08_geometry PRIVATE /O2 /W4)
else()
 target_compile_options(stage3d08_geometry PRIVATE -O3 -Wall -Wextra -Wpedantic)
endif()
# Qt Creator: choose this target and press Run with NO arguments.
add_test(NAME P08_geometry_help COMMAND stage3d08_geometry --help)
add_test(NAME P08_geometry_H0_radius COMMAND stage3d08_geometry
 --mesh ${CMAKE_CURRENT_SOURCE_DIR}/meshes/H0.msh
 --out ${CMAKE_CURRENT_BINARY_DIR}/P08_tests/radius --mode radius --delta-um 10,5,2.5 --quad 3)
add_test(NAME P08_geometry_H0_translation COMMAND stage3d08_geometry
 --mesh ${CMAKE_CURRENT_SOURCE_DIR}/meshes/H0.msh
 --out ${CMAKE_CURRENT_BINARY_DIR}/P08_tests/tx --mode tx --delta-um 10 --quad 3)
add_test(NAME P08_geometry_H0_quadrupole COMMAND stage3d08_geometry
 --mesh ${CMAKE_CURRENT_SOURCE_DIR}/meshes/H0.msh
 --out ${CMAKE_CURRENT_BINARY_DIR}/P08_tests/y20 --mode y20 --delta-um 10 --quad 3)

# Native Qt Creator radius finite-difference experiment, fresh coupled fields per mesh.
add_executable(stage3d08_qt_radius_fd_H0 src/stage3d08_radius_fd.cpp)
target_include_directories(stage3d08_qt_radius_fd_H0 PRIVATE "${CMAKE_CURRENT_BINARY_DIR}/generated")
add_dependencies(stage3d08_qt_radius_fd_H0 stage3d08_geometry stage3d02_thermal stage3d06_spatial)
if(MSVC)
 target_compile_options(stage3d08_qt_radius_fd_H0 PRIVATE /O2 /W4)
else()
 target_compile_options(stage3d08_qt_radius_fd_H0 PRIVATE -O2 -Wall -Wextra -Wpedantic)
endif()
if(WIN32)
 target_link_libraries(stage3d08_qt_radius_fd_H0 PRIVATE Psapi)
endif()
add_test(NAME P08_radius_FD_dry_run COMMAND stage3d08_qt_radius_fd_H0 --dry-run)

if(NOT STAGE3D06P_OPENMP OR NOT OpenMP_CXX_FOUND)
 target_compile_definitions(stage3d08_qt_radius_fd_H0 PRIVATE STAGE3D08_NO_OPENMP=1)
endif()

# Stage 3D-08B: ready-to-run spatial/temporal shape-derivative refinement.
# Presets reuse P08A coupled thermal/EDV solver, q3 xi=0 tend=3600.
# Each target has an independent output folder; completed H0/dt300 is reused,
# not computed again. Start with stage3d08b_H0_dt150 and send small reports.
foreach(preset IN ITEMS H0_150 H1_300 H1_150 H2_150 H0_300_CUTOFF4)
 if(preset STREQUAL "H0_150")
  set(target_name stage3d08b_H0_dt150)
 elseif(preset STREQUAL "H1_300")
  set(target_name stage3d08b_H1_dt300)
 elseif(preset STREQUAL "H1_150")
  set(target_name stage3d08b_H1_dt150)
 elseif(preset STREQUAL "H2_150")
  set(target_name stage3d08b_H2_dt150)
 else()
  set(target_name stage3d08b_H0_dt300_cutoff4)
 endif()
 add_executable(${target_name} src/stage3d08_radius_fd.cpp)
 target_include_directories(${target_name} PRIVATE "${CMAKE_CURRENT_BINARY_DIR}/generated")
 add_dependencies(${target_name} stage3d08_geometry stage3d02_thermal stage3d06_spatial)
 target_compile_definitions(${target_name} PRIVATE STAGE3D08B_${preset}=1)
 if(MSVC)
  target_compile_options(${target_name} PRIVATE /O2 /W4)
 else()
  target_compile_options(${target_name} PRIVATE -O2 -Wall -Wextra -Wpedantic)
 endif()
 if(NOT STAGE3D06P_OPENMP OR NOT OpenMP_CXX_FOUND)
  target_compile_definitions(${target_name} PRIVATE STAGE3D08_NO_OPENMP=1)
 endif()
 add_test(NAME P08B_${preset}_dryrun COMMAND ${target_name} --dry-run)
endforeach()

add_executable(stage3d08b_report src/stage3d08b_report.cpp)
target_include_directories(stage3d08b_report PRIVATE "${CMAKE_CURRENT_BINARY_DIR}/generated")
if(MSVC)
 target_compile_options(stage3d08b_report PRIVATE /O2 /W4)
else()
 target_compile_options(stage3d08b_report PRIVATE -O2 -Wall -Wextra -Wpedantic)
endif()
add_test(NAME P08B_report_help COMMAND stage3d08b_report --help)
if(Python3_Interpreter_FOUND)
 add_test(NAME P08B_report_synthetic
  COMMAND ${Python3_EXECUTABLE} ${CMAKE_CURRENT_SOURCE_DIR}/tests/p08b_report_synthetic.py
          --report $<TARGET_FILE:stage3d08b_report>)
endif()

# Stage3D-08C: eight physical shape modes, coupled EDV/VAR FD and read-only report.
# Run translations first; harmonics are deliberately a separate, expensive target.
foreach(preset IN ITEMS translations harmonics)
 set(target stage3d08c_H0_${preset})
 add_executable(${target} src/stage3d08c_shape_fd.cpp)
 target_include_directories(${target} PRIVATE "${CMAKE_CURRENT_BINARY_DIR}/generated")
 add_dependencies(${target} stage3d08_geometry stage3d02_thermal stage3d06_spatial)
 if(preset STREQUAL "harmonics")
  target_compile_definitions(${target} PRIVATE STAGE3D08C_HARMONICS=1)
 endif()
 if(NOT STAGE3D06P_OPENMP OR NOT OpenMP_CXX_FOUND)
  target_compile_definitions(${target} PRIVATE STAGE3D08_NO_OPENMP=1)
 endif()
 if(MSVC)
  target_compile_options(${target} PRIVATE /O2 /W4)
 else()
  target_compile_options(${target} PRIVATE -O2 -Wall -Wextra -Wpedantic)
 endif()
 add_test(NAME P08C_${preset}_dryrun COMMAND ${target} --dry-run)
endforeach()
add_executable(stage3d08c_report src/stage3d08c_report.cpp)
target_include_directories(stage3d08c_report PRIVATE "${CMAKE_CURRENT_BINARY_DIR}/generated")
if(MSVC)
 target_compile_options(stage3d08c_report PRIVATE /O2 /W4)
else()
 target_compile_options(stage3d08c_report PRIVATE -O2 -Wall -Wextra -Wpedantic)
endif()
add_test(NAME P08C_report_help COMMAND stage3d08c_report --help)
if(Python3_Interpreter_FOUND)
 add_test(NAME P08C_report_synthetic
  COMMAND ${Python3_EXECUTABLE} ${CMAKE_CURRENT_SOURCE_DIR}/tests/p08c_report_synthetic.py
          --report $<TARGET_FILE:stage3d08c_report>)
endif()
# Verify every nonradial mode at both FD amplitudes, independently of the FEM runner.
foreach(mode IN ITEMS tx ty tz y20 y21c y21s y22c y22s)
 add_test(NAME P08C_geometry_${mode}
  COMMAND stage3d08_geometry
   --mesh ${CMAKE_CURRENT_SOURCE_DIR}/meshes/H0.msh
   --out ${CMAKE_CURRENT_BINARY_DIR}/P08C_geometry/${mode}
   --mode ${mode} --delta-um 5,2.5 --quad 3)
endforeach()

# Stage 3D-08D: GH3 stochastic shape sensitivities of j6 (R,tz,y20).
# No new physics or FEM duplication; reuses the thermal/mechanical/geometry executables.
add_executable(stage3d08d_H0_gh3 src/stage3d08d_gh3.cpp)
target_include_directories(stage3d08d_H0_gh3 PRIVATE "${CMAKE_CURRENT_BINARY_DIR}/generated")
add_dependencies(stage3d08d_H0_gh3 stage3d08_geometry stage3d02_thermal stage3d06_spatial)
if(NOT STAGE3D06P_OPENMP OR NOT OpenMP_CXX_FOUND)
 target_compile_definitions(stage3d08d_H0_gh3 PRIVATE STAGE3D08_NO_OPENMP=1)
endif()
if(MSVC)
 target_compile_options(stage3d08d_H0_gh3 PRIVATE /O2 /W4)
else()
 target_compile_options(stage3d08d_H0_gh3 PRIVATE -O2 -Wall -Wextra -Wpedantic)
endif()
add_test(NAME P08D_GH3_math_and_derivatives COMMAND stage3d08d_H0_gh3 --selftest)
add_test(NAME P08D_GH3_dryrun COMMAND stage3d08d_H0_gh3 --dry-run)

# Stage 3D-08E: GH5 comparison against GH3, with verified xi=0 reuse.
add_executable(stage3d08e_gh5 src/stage3d08e_gh5.cpp)
target_include_directories(stage3d08e_gh5 PRIVATE "${CMAKE_CURRENT_BINARY_DIR}/generated")
add_dependencies(stage3d08e_gh5 stage3d08_geometry stage3d02_thermal stage3d06_spatial)
if(NOT STAGE3D06P_OPENMP OR NOT OpenMP_CXX_FOUND)
  target_compile_definitions(stage3d08e_gh5 PRIVATE STAGE3D08_NO_OPENMP=1)
endif()
if(MSVC)
  target_compile_options(stage3d08e_gh5 PRIVATE /O2 /W4)
else()
  target_compile_options(stage3d08e_gh5 PRIVATE -O2 -Wall -Wextra -Wpedantic)
endif()
add_test(NAME P08E_GH5_moments_and_derivatives COMMAND stage3d08e_gh5 --selftest)
add_test(NAME P08E_GH5_dryrun COMMAND stage3d08e_gh5 --dry-run)

# Stage 3D-09A: matched constitutive E/ED/EDV x E_CONST/E_VAR comparison.
add_executable(stage3d09a_models src/stage3d09a_models.cpp)
target_include_directories(stage3d09a_models PRIVATE "${CMAKE_CURRENT_BINARY_DIR}/generated" src)
add_dependencies(stage3d09a_models stage3d02_thermal stage3d06_spatial)
if(NOT STAGE3D06P_OPENMP OR NOT OpenMP_CXX_FOUND)
 target_compile_definitions(stage3d09a_models PRIVATE STAGE3D08_NO_OPENMP=1)
endif()
if(MSVC)
 target_compile_options(stage3d09a_models PRIVATE /O2 /W4)
else()
 target_compile_options(stage3d09a_models PRIVATE -O2 -Wall -Wextra -Wpedantic)
endif()
add_test(NAME P09A_constitutive_temperature_tangents COMMAND stage3d09a_models --selftest)
add_test(NAME P09A_dryrun COMMAND stage3d09a_models --dry-run)
# Stage 3D-09B local material-point adjoint preflight (not yet a global adjoint).
add_executable(stage3d09b_local_adjoint_preflight tests/stage3d09b_local_adjoint.cpp)
target_include_directories(stage3d09b_local_adjoint_preflight PRIVATE src)
if(MSVC)
 target_compile_options(stage3d09b_local_adjoint_preflight PRIVATE /O2 /W4)
else()
 target_compile_options(stage3d09b_local_adjoint_preflight PRIVATE -O2 -Wall -Wextra -Wpedantic)
endif()
add_test(NAME P09B_local_history_adjoint_test COMMAND stage3d09b_local_adjoint_preflight)

# Stage 3D-10A: independent full-history reverse-mode preflight for E/ED/EDV.
# No mesh or thermomechanical FEM trajectories required; local Jacobians use FD.
add_executable(stage3d10a_local_history_adjoint tests/stage3d10a_local_history_adjoint.cpp)
target_include_directories(stage3d10a_local_history_adjoint PRIVATE src)
if(MSVC)
 target_compile_options(stage3d10a_local_history_adjoint PRIVATE /O2 /W4)
else()
 target_compile_options(stage3d10a_local_history_adjoint PRIVATE -O2 -Wall -Wextra -Wpedantic)
endif()
add_test(NAME P10A_local_history_reverse_vs_FD COMMAND stage3d10a_local_history_adjoint)

# Stage 3D-10B: analytic JVP and Euclidean-Voigt VJP of E/ED/EDV update.
add_executable(stage3d10b_edv_linearization tests/stage3d10b_edv_linearization.cpp)
target_include_directories(stage3d10b_edv_linearization PRIVATE src)
if(MSVC)
 target_compile_options(stage3d10b_edv_linearization PRIVATE /O2 /W4)
else()
 target_compile_options(stage3d10b_edv_linearization PRIVATE -O2 -Wall -Wextra -Wpedantic)
endif()
add_test(NAME P10B_EDV_analytic_JVP_VJP COMMAND stage3d10b_edv_linearization)

# Stage 3D-09B: same FEM solve with three postprocessed observables.
add_executable(stage3d09b_three_functionals src/stage3d09b_three_functionals.cpp)
target_include_directories(stage3d09b_three_functionals PRIVATE "${CMAKE_CURRENT_BINARY_DIR}/generated" src)
add_dependencies(stage3d09b_three_functionals stage3d02_thermal stage3d06_spatial)
if(NOT STAGE3D06P_OPENMP OR NOT OpenMP_CXX_FOUND)
 target_compile_definitions(stage3d09b_three_functionals PRIVATE STAGE3D08_NO_OPENMP=1)
endif()
if(MSVC)
 target_compile_options(stage3d09b_three_functionals PRIVATE /O2 /W4)
else()
 target_compile_options(stage3d09b_three_functionals PRIVATE -O2 -Wall -Wextra -Wpedantic)
endif()
add_executable(stage3d09b_functionals_unit tests/stage3d09b_functionals.cpp)
target_include_directories(stage3d09b_functionals_unit PRIVATE src)
add_test(NAME P09B_three_functionals_unit COMMAND stage3d09b_functionals_unit)
add_test(NAME P09B_three_functionals_dryrun COMMAND stage3d09b_three_functionals --dry-run)

# Stage 3D-09C: three-functional shape FD & stochastic GH3 sensitivities.
add_executable(stage3d09c_shape_three src/stage3d09c_shape_three.cpp)
target_include_directories(stage3d09c_shape_three PRIVATE "${CMAKE_CURRENT_BINARY_DIR}/generated" src)
add_dependencies(stage3d09c_shape_three stage3d08_geometry stage3d02_thermal stage3d06_spatial)
if(STAGE3D08_NO_OPENMP)
  target_compile_definitions(stage3d09c_shape_three PRIVATE STAGE3D08_NO_OPENMP=1)
endif()
if(MSVC)
  target_compile_options(stage3d09c_shape_three PRIVATE /O2 /W4)
else()
  target_compile_options(stage3d09c_shape_three PRIVATE -O2 -Wall -Wextra -Wpedantic)
endif()
add_test(NAME P09C_GH3_shape_three_math COMMAND stage3d09c_shape_three --selftest)
add_test(NAME P09C_GH3_shape_three_dryrun COMMAND stage3d09c_shape_three --dry-run)

# Stage 3D-09D: final checkpoint spatial diagnostics, no new FEM trajectory.
add_executable(stage3d09d_diagnostics src/stage3d09d_diagnostics.cpp)
target_include_directories(stage3d09d_diagnostics PRIVATE "${CMAKE_CURRENT_BINARY_DIR}/generated" src)
add_dependencies(stage3d09d_diagnostics stage3d06_spatial)
if(MSVC)
 target_compile_options(stage3d09d_diagnostics PRIVATE /O2 /W4)
else()
 target_compile_options(stage3d09d_diagnostics PRIVATE -O2 -Wall -Wextra -Wpedantic)
endif()
add_test(NAME P09D_diagnostics_selftest COMMAND stage3d09d_diagnostics --selftest)
add_executable(stage3d09d_spatial_unit src/stage3d09d_spatial_unit.cpp)
target_include_directories(stage3d09d_spatial_unit PRIVATE src)
add_test(NAME P09D_shell_conservation_unit COMMAND stage3d09d_spatial_unit)

# Stage 3D-09D2: read-only checkpoint local shell + smooth partition diagnosis.
add_executable(stage3d09d2_diagnostics src/stage3d09d2_diagnostics.cpp)
target_include_directories(stage3d09d2_diagnostics PRIVATE "${CMAKE_CURRENT_BINARY_DIR}/generated" src)
add_dependencies(stage3d09d2_diagnostics stage3d06_spatial)
if(MSVC)
 target_compile_options(stage3d09d2_diagnostics PRIVATE /O2 /W4)
else()
 target_compile_options(stage3d09d2_diagnostics PRIVATE -O2 -Wall -Wextra -Wpedantic)
endif()
add_test(NAME P09D2_launcher_selftest COMMAND stage3d09d2_diagnostics --selftest)
add_executable(stage3d09d2_spatial_unit src/stage3d09d2_spatial_unit.cpp)
target_include_directories(stage3d09d2_spatial_unit PRIVATE src)
add_test(NAME P09D2_partition_conservation COMMAND stage3d09d2_spatial_unit)

# Stage3D09D3: paired quadrature finite-difference decomposition at final checkpoint.
add_executable(stage3d09d3_diagnostics src/stage3d09d3_diagnostics.cpp)
target_include_directories(stage3d09d3_diagnostics PRIVATE "${CMAKE_CURRENT_BINARY_DIR}/generated" src)
add_dependencies(stage3d09d3_diagnostics stage3d06_spatial)
if(MSVC)
 target_compile_options(stage3d09d3_diagnostics PRIVATE /O2 /W4)
else()
 target_compile_options(stage3d09d3_diagnostics PRIVATE -O2 -Wall -Wextra -Wpedantic)
endif()
add_test(NAME P09D3_launcher_selftest COMMAND stage3d09d3_diagnostics --selftest)
add_executable(stage3d09d3_spatial_unit src/stage3d09d3_spatial_unit.cpp)
target_include_directories(stage3d09d3_spatial_unit PRIVATE src)
add_test(NAME P09D3_pair_identity COMMAND stage3d09d3_spatial_unit)

# Stage 3D-09D4: additional independent pore-wall density checks.
# Meshes are optional at configure time: the generators can create HP8 later.
foreach(mesh_name IN ITEMS HP2 HP4 HP8)
  if(EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/meshes/${mesh_name}.msh")
    add_test(NAME P09D4_${mesh_name}_dryrun
      COMMAND stage3d09c_shape_three --mesh ${mesh_name} --modes y20
              --laws EDV --moduli VAR --reuse-p08d off --dry-run)
  endif()
endforeach()

# Stage 3D-09D5: lightweight test of bounded checkpoint I/O (no FEM solve).
add_executable(stage3d09d5_checkpoint_test src/stage3d09d5_checkpoint_test.cpp)
if(MSVC)
  target_compile_options(stage3d09d5_checkpoint_test PRIVATE /O2 /W4)
else()
  target_compile_options(stage3d09d5_checkpoint_test PRIVATE -O2 -Wall -Wextra -Wpedantic)
endif()
add_test(NAME P09D5_checkpoint_io_small COMMAND stage3d09d5_checkpoint_test --small)

# Stage 3D-09E: compact, lossless thermal histories with exact mesh/time validation.
add_executable(stage3d09e_io_test src/stage3d09e_io_test.cpp)
target_compile_features(stage3d09e_io_test PRIVATE cxx_std_20)
if(MSVC)
 target_compile_options(stage3d09e_io_test PRIVATE /O2 /W4)
else()
 target_compile_options(stage3d09e_io_test PRIVATE -O2 -Wall -Wextra -Wpedantic)
endif()
add_test(NAME P09E_binary_field_selftest COMMAND stage3d09e_io_test)

# Stage3D09E2: elapsed-wall-time checkpoint policy and CSV rollback unit tests.
add_executable(stage3d09e2_checkpoint_test src/stage3d09e2_checkpoint_test.cpp)
set_target_properties(stage3d09e2_checkpoint_test PROPERTIES CXX_STANDARD 20 CXX_STANDARD_REQUIRED ON)

# Append to the END of your existing CMakeLists.txt; DO NOT replace it.
# Stage 3D-10C: global Tet10 E/ED/EDV analytic transpose regression.
add_executable(stage3d10c_tet10_global_adjoint tests/stage3d10c_tet10_global_adjoint.cpp)
target_include_directories(stage3d10c_tet10_global_adjoint PRIVATE src)
if(MSVC)
 target_compile_options(stage3d10c_tet10_global_adjoint PRIVATE /O2 /W4)
else()
 target_compile_options(stage3d10c_tet10_global_adjoint PRIVATE -O2 -Wall -Wextra -Wpedantic)
endif()
add_test(NAME P10C_Tet10_global_EDV_JVP_VJP COMMAND stage3d10c_tet10_global_adjoint)

# Append once to the END of the CURRENT CMakeLists.txt.
# Do not replace CMakeLists.txt or remove Stage 3D-10A/B/C targets.
add_executable(stage3d10d_transient_adjoint tests/stage3d10d_transient_adjoint.cpp)
target_include_directories(stage3d10d_transient_adjoint PRIVATE src)
if(MSVC)
 target_compile_options(stage3d10d_transient_adjoint PRIVATE /O2 /W4)
else()
 target_compile_options(stage3d10d_transient_adjoint PRIVATE -O2 -Wall -Wextra -Wpedantic)
endif()
add_test(NAME P10D_transient_EDV_global_adjoint COMMAND stage3d10d_transient_adjoint)

# Append ONCE to the existing CMakeLists.txt.  Do NOT replace the file.
# Stage10D target remains available as independent dense-solver baseline.
add_executable(stage3d10e_bcsr_transient_adjoint tests/stage3d10d_transient_adjoint.cpp)
target_include_directories(stage3d10e_bcsr_transient_adjoint PRIVATE src)
target_compile_definitions(stage3d10e_bcsr_transient_adjoint PRIVATE STAGE3D10E_SPARSE_ADJOINT)
if(MSVC)
 target_compile_options(stage3d10e_bcsr_transient_adjoint PRIVATE /O2 /W4)
else()
 target_compile_options(stage3d10e_bcsr_transient_adjoint PRIVATE -O2 -Wall -Wextra -Wpedantic)
endif()
if(STAGE3D06P_OPENMP AND OpenMP_CXX_FOUND)
 target_link_libraries(stage3d10e_bcsr_transient_adjoint PRIVATE OpenMP::OpenMP_CXX)
endif()
add_test(NAME P10E_BCSR_transient_adjoint COMMAND stage3d10e_bcsr_transient_adjoint)

# Append this block ONCE at the end of the EXISTING CMakeLists.txt.
# Uses the updated Stage10D test source in both original and Stage10F modes.
add_executable(stage3d10f_functional_adjoint tests/stage3d10d_transient_adjoint.cpp)
target_include_directories(stage3d10f_functional_adjoint PRIVATE src)
target_compile_definitions(stage3d10f_functional_adjoint PRIVATE
 STAGE3D10E_SPARSE_ADJOINT STAGE3D10F_PHYSICAL_FUNCTIONALS)
if(MSVC)
 target_compile_options(stage3d10f_functional_adjoint PRIVATE /O2 /W4)
else()
 target_compile_options(stage3d10f_functional_adjoint PRIVATE -O2 -Wall -Wextra -Wpedantic)
endif()
if(STAGE3D06P_OPENMP AND OpenMP_CXX_FOUND)
 target_link_libraries(stage3d10f_functional_adjoint PRIVATE OpenMP::OpenMP_CXX)
endif()
add_test(NAME P10F_physical_functionals_full_history_adjoint
 COMMAND stage3d10f_functional_adjoint)

# Add this block ONCE to your existing CMakeLists.txt (do not replace it).
# Stage 3D-10G: four-step checkpoint replay of verified Stage 3D-10F adjoint.
add_executable(stage3d10g_checkpoint_replay tests/stage3d10d_transient_adjoint.cpp)
target_include_directories(stage3d10g_checkpoint_replay PRIVATE src)
target_compile_definitions(stage3d10g_checkpoint_replay PRIVATE
 STAGE3D10E_SPARSE_ADJOINT STAGE3D10F_PHYSICAL_FUNCTIONALS
 STAGE3D10G_CHECKPOINT_REPLAY)
if(MSVC)
 target_compile_options(stage3d10g_checkpoint_replay PRIVATE /O2 /W4)
else()
 target_compile_options(stage3d10g_checkpoint_replay PRIVATE -O2 -Wall -Wextra -Wpedantic)
endif()
if(STAGE3D06P_OPENMP AND OpenMP_CXX_FOUND)
 target_link_libraries(stage3d10g_checkpoint_replay PRIVATE OpenMP::OpenMP_CXX)
endif()
add_test(NAME P10G_checkpointed_history_adjoint
 COMMAND stage3d10g_checkpoint_replay)

# Stage 3D-10H: use the original production Tet10/EDV assembly from
# spatial_reology.cpp and verify time-history replay on the same code path.
add_executable(stage3d10h_production_replay tests/stage3d10h_production_preflight.cpp)
target_include_directories(stage3d10h_production_replay PRIVATE src)
if(MSVC)
 target_compile_options(stage3d10h_production_replay PRIVATE /O2 /W4)
else()
 target_compile_options(stage3d10h_production_replay PRIVATE -O2 -Wall -Wextra -Wpedantic)
endif()
if(STAGE3D06P_OPENMP AND OpenMP_CXX_FOUND)
 target_link_libraries(stage3d10h_production_replay PRIVATE OpenMP::OpenMP_CXX)
endif()
if(WIN32)
 target_sources(stage3d10h_production_replay PRIVATE src/win_process_memory.cpp)
 target_link_libraries(stage3d10h_production_replay PRIVATE Psapi)
endif()
add_test(NAME P10H_real_spatial_replay_preflight
 COMMAND stage3d10h_production_replay)

# Stage 3D-10I — production nonlinear_step, checkpointed full-history adjoint,
# independent nonlinear finite differences for all three real P09B objectives.
add_executable(stage3d10i_production_adjoint tests/stage3d10h_production_preflight.cpp)
target_include_directories(stage3d10i_production_adjoint PRIVATE src)
target_compile_definitions(stage3d10i_production_adjoint PRIVATE STAGE3D10I_PRODUCTION_ADJOINT)
if(MSVC)
 target_compile_options(stage3d10i_production_adjoint PRIVATE /O2 /W4)
else()
 target_compile_options(stage3d10i_production_adjoint PRIVATE -O2 -Wall -Wextra -Wpedantic)
endif()
if(STAGE3D06P_OPENMP AND OpenMP_CXX_FOUND)
 target_link_libraries(stage3d10i_production_adjoint PRIVATE OpenMP::OpenMP_CXX)
endif()
if(WIN32)
 target_sources(stage3d10i_production_adjoint PRIVATE src/win_process_memory.cpp)
 target_link_libraries(stage3d10i_production_adjoint PRIVATE Psapi)
endif()
add_test(NAME P10I_production_checkpoint_adjoint_vs_FD
 COMMAND stage3d10i_production_adjoint)

# Stage 3D-10J: read-only H0 geometry/memory gate after Stage 3D-10I.
# Add ONCE to the existing CMakeLists.txt, do not replace it.
add_executable(stage3d10j_h0_geometry_preflight src/stage3d10j_h0_geometry_preflight.cpp)
target_include_directories(stage3d10j_h0_geometry_preflight PRIVATE
 "${CMAKE_CURRENT_BINARY_DIR}/generated" src)
if(MSVC)
 target_compile_options(stage3d10j_h0_geometry_preflight PRIVATE /O2 /W4)
else()
 target_compile_options(stage3d10j_h0_geometry_preflight PRIVATE -O2 -Wall -Wextra -Wpedantic)
endif()
if(STAGE3D06P_OPENMP AND OpenMP_CXX_FOUND)
 target_link_libraries(stage3d10j_h0_geometry_preflight PRIVATE OpenMP::OpenMP_CXX)
endif()
add_test(NAME P10J_shape_transport_selftest
 COMMAND stage3d10j_h0_geometry_preflight --selftest)

# Append to the EXISTING project CMakeLists.txt (after the Stage 3D-10I/J targets).
# This target requires the previously installed 3D-10H and 3D-10I patches.
add_executable(stage3d10k_h0_coupled_pilot src/stage3d10k_h0_coupled_pilot.cpp)
target_include_directories(stage3d10k_h0_coupled_pilot PRIVATE
  src tests "${CMAKE_CURRENT_BINARY_DIR}/generated")
target_compile_definitions(stage3d10k_h0_coupled_pilot PRIVATE
  STAGE3D10K_SOURCE_ROOT="${CMAKE_CURRENT_SOURCE_DIR}")
if(MSVC)
  target_compile_options(stage3d10k_h0_coupled_pilot PRIVATE /O2 /W4)
else()
  target_compile_options(stage3d10k_h0_coupled_pilot PRIVATE -O2 -Wall -Wextra -Wpedantic)
endif()
if(STAGE3D06P_OPENMP AND OpenMP_CXX_FOUND)
  target_link_libraries(stage3d10k_h0_coupled_pilot PRIVATE OpenMP::OpenMP_CXX)
endif()
if(WIN32)
  target_sources(stage3d10k_h0_coupled_pilot PRIVATE src/win_process_memory.cpp)
  target_link_libraries(stage3d10k_h0_coupled_pilot PRIVATE Psapi)
endif()
add_dependencies(stage3d10k_h0_coupled_pilot
  stage3d08_geometry stage3d02_thermal)
add_test(NAME P10K_H0_coupled_pilot_synthetic_regression
  COMMAND stage3d10k_h0_coupled_pilot --selftest)

# Append to the existing project CMakeLists.txt AFTER Stage 3D-10K.
# P10L includes the P10K, P10I, P10H production source and test harness;
# therefore it uses the same build definitions and test/include paths.
add_executable(stage3d10l_h0_full_thermal_adjoint
  src/stage3d10l_h0_full_thermal_adjoint.cpp)
target_include_directories(stage3d10l_h0_full_thermal_adjoint PRIVATE
  src tests "${CMAKE_CURRENT_BINARY_DIR}/generated")
target_compile_definitions(stage3d10l_h0_full_thermal_adjoint PRIVATE
  STAGE3D10K_SOURCE_ROOT="${CMAKE_CURRENT_SOURCE_DIR}")
if(MSVC)
  target_compile_options(stage3d10l_h0_full_thermal_adjoint PRIVATE /O2 /W4)
else()
  target_compile_options(stage3d10l_h0_full_thermal_adjoint PRIVATE
    -O2 -Wall -Wextra -Wpedantic)
endif()
if(STAGE3D06P_OPENMP AND OpenMP_CXX_FOUND)
  target_link_libraries(stage3d10l_h0_full_thermal_adjoint PRIVATE
    OpenMP::OpenMP_CXX)
endif()
if(WIN32)
  target_sources(stage3d10l_h0_full_thermal_adjoint PRIVATE
    src/win_process_memory.cpp)
  target_link_libraries(stage3d10l_h0_full_thermal_adjoint PRIVATE Psapi)
endif()
add_dependencies(stage3d10l_h0_full_thermal_adjoint
  stage3d08_geometry stage3d02_thermal)
add_test(NAME P10L_thermal_adjoint_synthetic_regression
  COMMAND stage3d10l_h0_full_thermal_adjoint --selftest)

# Add AFTER the existing Stage 3D-10L target in CMakeLists.txt.
# This program uses one original coupled history; perturbed meshes are used
# only to evaluate the mechanical mesh-coordinate partial derivatives.
add_executable(stage3d10m_shape_convergence
  src/stage3d10m_shape_convergence.cpp)
target_include_directories(stage3d10m_shape_convergence PRIVATE
  src tests "${CMAKE_CURRENT_BINARY_DIR}/generated")
target_compile_definitions(stage3d10m_shape_convergence PRIVATE
  STAGE3D10K_SOURCE_ROOT="${CMAKE_CURRENT_SOURCE_DIR}")
if(MSVC)
  target_compile_options(stage3d10m_shape_convergence PRIVATE /O2 /W4)
else()
  target_compile_options(stage3d10m_shape_convergence PRIVATE
    -O2 -Wall -Wextra -Wpedantic)
endif()
if(STAGE3D06P_OPENMP AND OpenMP_CXX_FOUND)
  target_link_libraries(stage3d10m_shape_convergence PRIVATE OpenMP::OpenMP_CXX)
endif()
if(WIN32)
  target_sources(stage3d10m_shape_convergence PRIVATE src/win_process_memory.cpp)
  target_link_libraries(stage3d10m_shape_convergence PRIVATE Psapi)
endif()
add_dependencies(stage3d10m_shape_convergence stage3d08_geometry)
add_test(NAME P10M_convergence_synthetic_regression
  COMMAND stage3d10m_shape_convergence --selftest)

# Add once at the end of the existing Stage3D07 CMakeLists.txt.
# Requires previously installed Stage3D10K/10L/10M sources and headers.
add_executable(stage3d10n_delta_scan src/stage3d10n_delta_scan.cpp)
target_include_directories(stage3d10n_delta_scan PRIVATE
  src tests "${CMAKE_CURRENT_BINARY_DIR}/generated")
target_compile_definitions(stage3d10n_delta_scan PRIVATE
  STAGE3D10K_SOURCE_ROOT="${CMAKE_CURRENT_SOURCE_DIR}")
if(MSVC)
  target_compile_options(stage3d10n_delta_scan PRIVATE /O2 /W4)
else()
  target_compile_options(stage3d10n_delta_scan PRIVATE -O2 -Wall -Wextra -Wpedantic)
endif()
if(STAGE3D06P_OPENMP AND OpenMP_CXX_FOUND)
  target_link_libraries(stage3d10n_delta_scan PRIVATE OpenMP::OpenMP_CXX)
endif()
if(WIN32)
  target_sources(stage3d10n_delta_scan PRIVATE src/win_process_memory.cpp)
  target_link_libraries(stage3d10n_delta_scan PRIVATE Psapi)
endif()
add_dependencies(stage3d10n_delta_scan stage3d08_geometry)

# Append ONCE to the existing G:/ildar/Stage3D07/CMakeLists.txt.
# Standalone C++20 Gmsh mesh generator + volume-Tet10 density audit.
add_executable(stage3d10o_mesh_prepare src/stage3d10o_mesh_prepare.cpp)
if(MSVC)
  target_compile_options(stage3d10o_mesh_prepare PRIVATE /O2 /W4)
else()
  target_compile_options(stage3d10o_mesh_prepare PRIVATE
    -O2 -Wall -Wextra -Wpedantic)
endif()

# Append once to the Stage3D07 CMakeLists.txt; requires the existing P10N files.
add_executable(stage3d10p_partial_audit src/stage3d10p_partial_audit.cpp)
target_include_directories(stage3d10p_partial_audit PRIVATE
  src tests "${CMAKE_CURRENT_BINARY_DIR}/generated")
target_compile_definitions(stage3d10p_partial_audit PRIVATE
  STAGE3D10K_SOURCE_ROOT="${CMAKE_CURRENT_SOURCE_DIR}")
if(MSVC)
  target_compile_options(stage3d10p_partial_audit PRIVATE /O2 /W4)
else()
  target_compile_options(stage3d10p_partial_audit PRIVATE
    -O2 -Wall -Wextra -Wpedantic)
endif()
if(STAGE3D06P_OPENMP AND OpenMP_CXX_FOUND)
  target_link_libraries(stage3d10p_partial_audit PRIVATE OpenMP::OpenMP_CXX)
endif()
if(WIN32)
  target_sources(stage3d10p_partial_audit PRIVATE src/win_process_memory.cpp)
  target_link_libraries(stage3d10p_partial_audit PRIVATE Psapi)
endif()
add_dependencies(stage3d10p_partial_audit stage3d08_geometry)

# Append ONCE to the existing Stage3D07/CMakeLists.txt.
# Requires src/stage3d10p_partial_audit.cpp with main() protected by
# #ifndef STAGE3D10P_NO_MAIN / #endif.
add_executable(stage3d10r_wall_profile src/stage3d10r_wall_profile.cpp)
target_include_directories(stage3d10r_wall_profile PRIVATE
  src tests "${CMAKE_CURRENT_BINARY_DIR}/generated")
target_compile_definitions(stage3d10r_wall_profile PRIVATE
  STAGE3D10K_SOURCE_ROOT="${CMAKE_CURRENT_SOURCE_DIR}")
if(MSVC)
  target_compile_options(stage3d10r_wall_profile PRIVATE /O2 /W4)
else()
  target_compile_options(stage3d10r_wall_profile PRIVATE
    -O2 -Wall -Wextra -Wpedantic)
endif()
if(STAGE3D06P_OPENMP AND OpenMP_CXX_FOUND)
  target_link_libraries(stage3d10r_wall_profile PRIVATE OpenMP::OpenMP_CXX)
endif()
if(WIN32)
  target_sources(stage3d10r_wall_profile PRIVATE src/win_process_memory.cpp)
  target_link_libraries(stage3d10r_wall_profile PRIVATE Psapi)
endif()
add_test(NAME P10R_radial_shell_selftest
  COMMAND stage3d10r_wall_profile --selftest)

# Append once to the existing Stage3D07/CMakeLists.txt.
# The modified P10P source in this package enables optional shell diagnostics
# only when included by stage3d10s_spatial_partial.cpp.
set(STAGE3D10S_GIT_COMMIT_AT_CONFIGURE "UNKNOWN")
find_package(Git QUIET)
if(GIT_FOUND)
  execute_process(
    COMMAND "${GIT_EXECUTABLE}" -C "${CMAKE_CURRENT_SOURCE_DIR}" rev-parse --verify HEAD
    OUTPUT_VARIABLE STAGE3D10S_GIT_SHA_PROBE
    RESULT_VARIABLE STAGE3D10S_GIT_PROBE_STATUS
    OUTPUT_STRIP_TRAILING_WHITESPACE
    ERROR_QUIET)
  if(STAGE3D10S_GIT_PROBE_STATUS EQUAL 0)
    set(STAGE3D10S_GIT_COMMIT_AT_CONFIGURE "${STAGE3D10S_GIT_SHA_PROBE}")
  endif()
endif()
add_executable(stage3d10s_spatial_partial src/stage3d10s_spatial_partial.cpp)
target_include_directories(stage3d10s_spatial_partial PRIVATE
  src tests "${CMAKE_CURRENT_BINARY_DIR}/generated")
target_compile_definitions(stage3d10s_spatial_partial PRIVATE
  STAGE3D10K_SOURCE_ROOT="${CMAKE_CURRENT_SOURCE_DIR}"
  STAGE3D10S_GIT_COMMIT_AT_CONFIGURE="${STAGE3D10S_GIT_COMMIT_AT_CONFIGURE}")
if(MSVC)
  target_compile_options(stage3d10s_spatial_partial PRIVATE /O2 /W4)
else()
  target_compile_options(stage3d10s_spatial_partial PRIVATE
    -O2 -Wall -Wextra -Wpedantic)
endif()
if(STAGE3D06P_OPENMP AND OpenMP_CXX_FOUND)
  target_link_libraries(stage3d10s_spatial_partial PRIVATE OpenMP::OpenMP_CXX)
endif()
if(WIN32)
  target_sources(stage3d10s_spatial_partial PRIVATE src/win_process_memory.cpp)
  target_link_libraries(stage3d10s_spatial_partial PRIVATE Psapi)
endif()
add_dependencies(stage3d10s_spatial_partial stage3d08_geometry)
add_test(NAME P10S_spatial_bins_selftest
  COMMAND stage3d10s_spatial_partial --selftest)

# Lightweight standalone manifest/sha256 tests: no mesh or FEM solve needed.
add_executable(stage3d10s_manifest_unit tests/stage3d10s_manifest_unit.cpp)
target_include_directories(stage3d10s_manifest_unit PRIVATE src)
add_test(NAME P10S_manifest_unit COMMAND stage3d10s_manifest_unit)

# Stage3D10V: analytic curved-Tet10 geometry derivatives at fixed EDV state.
# This is an independent, tiny reference-element test, not a production solve.
add_executable(stage3d10v_analytic_shape_unit
  tests/stage3d10v_analytic_shape.cpp)
target_include_directories(stage3d10v_analytic_shape_unit PRIVATE src)
if(MSVC)
 target_compile_options(stage3d10v_analytic_shape_unit PRIVATE /O2 /W4)
else()
 target_compile_options(stage3d10v_analytic_shape_unit PRIVATE -O2 -Wall -Wextra -Wpedantic)
endif()
add_test(NAME P10V_Tet10_analytic_shape_derivatives
  COMMAND stage3d10v_analytic_shape_unit)

# Stage3D10W: one full EDV_VAR transient adjoint with analytic geometric
# partials. P10N/P/S retain their old finite-difference reference behavior.
add_executable(stage3d10w_analytic_adjoint
  src/stage3d10w_analytic_adjoint.cpp)
target_include_directories(stage3d10w_analytic_adjoint PRIVATE
  src tests "${CMAKE_CURRENT_BINARY_DIR}/generated")
target_compile_definitions(stage3d10w_analytic_adjoint PRIVATE
  STAGE3D10K_SOURCE_ROOT="${CMAKE_CURRENT_SOURCE_DIR}")
if(MSVC)
 target_compile_options(stage3d10w_analytic_adjoint PRIVATE /O2 /W4)
else()
 target_compile_options(stage3d10w_analytic_adjoint PRIVATE
   -O2 -Wall -Wextra -Wpedantic)
endif()
if(STAGE3D06P_OPENMP AND OpenMP_CXX_FOUND)
 target_link_libraries(stage3d10w_analytic_adjoint PRIVATE OpenMP::OpenMP_CXX)
endif()
if(WIN32)
 target_sources(stage3d10w_analytic_adjoint PRIVATE src/win_process_memory.cpp)
 target_link_libraries(stage3d10w_analytic_adjoint PRIVATE Psapi)
endif()
add_test(NAME P10W_analytic_adjoint_selftest
  COMMAND stage3d10w_analytic_adjoint --selftest)

# Stage3D10Y: the same exact P10W Tet10 geometric derivative, now apportioned
# by Gauss-point radius. The original P10W and the FD-based P10S are unchanged.
add_executable(stage3d10y_analytic_shell_audit
  src/stage3d10w_analytic_adjoint.cpp)
target_include_directories(stage3d10y_analytic_shell_audit PRIVATE
  src tests "${CMAKE_CURRENT_BINARY_DIR}/generated")
target_compile_definitions(stage3d10y_analytic_shell_audit PRIVATE
  STAGE3D10Y_ANALYTIC_SHELL_AUDIT STAGE3D10S_SPATIAL_AUDIT
  STAGE3D10K_SOURCE_ROOT="${CMAKE_CURRENT_SOURCE_DIR}")
if(MSVC)
 target_compile_options(stage3d10y_analytic_shell_audit PRIVATE /O2 /W4)
else()
 target_compile_options(stage3d10y_analytic_shell_audit PRIVATE
   -O2 -Wall -Wextra -Wpedantic)
endif()
if(STAGE3D06P_OPENMP AND OpenMP_CXX_FOUND)
 target_link_libraries(stage3d10y_analytic_shell_audit PRIVATE OpenMP::OpenMP_CXX)
endif()
if(WIN32)
 target_sources(stage3d10y_analytic_shell_audit PRIVATE src/win_process_memory.cpp)
 target_link_libraries(stage3d10y_analytic_shell_audit PRIVATE Psapi)
endif()
add_test(NAME P10Y_analytic_shell_selftest
  COMMAND stage3d10y_analytic_shell_audit --selftest)

# P10AZ: full P10Y math, additional targeted Q3/element diagnostic only.
# No changes to the original P10Y target or its outputs.
add_executable(stage3d10az_targeted_qp_probe
  src/stage3d10w_analytic_adjoint.cpp)
target_include_directories(stage3d10az_targeted_qp_probe PRIVATE
  src tests "${CMAKE_CURRENT_BINARY_DIR}/generated")
target_compile_definitions(stage3d10az_targeted_qp_probe PRIVATE
  STAGE3D10Y_ANALYTIC_SHELL_AUDIT STAGE3D10S_SPATIAL_AUDIT
  STAGE3D10AZ_QP_PROBE
  STAGE3D10K_SOURCE_ROOT="${CMAKE_CURRENT_SOURCE_DIR}")
if(MSVC)
  target_compile_options(stage3d10az_targeted_qp_probe PRIVATE /O2 /W4)
else()
  target_compile_options(stage3d10az_targeted_qp_probe PRIVATE
    -O2 -Wall -Wextra -Wpedantic)
endif()
if(STAGE3D06P_OPENMP AND OpenMP_CXX_FOUND)
  target_link_libraries(stage3d10az_targeted_qp_probe PRIVATE OpenMP::OpenMP_CXX)
endif()
if(WIN32)
  target_sources(stage3d10az_targeted_qp_probe PRIVATE src/win_process_memory.cpp)
  target_link_libraries(stage3d10az_targeted_qp_probe PRIVATE Psapi)
endif()
add_test(NAME P10AZ_probe_preflight
  COMMAND stage3d10az_targeted_qp_probe --selftest)

# Independent tiny reference-element check of the QP capture path.
add_executable(stage3d10az_qp_probe_unit
  tests/stage3d10v_analytic_shape.cpp)
target_include_directories(stage3d10az_qp_probe_unit PRIVATE src)
target_compile_definitions(stage3d10az_qp_probe_unit PRIVATE
  STAGE3D10Y_ANALYTIC_SHELL_AUDIT STAGE3D10AZ_QP_PROBE)
if(MSVC)
  target_compile_options(stage3d10az_qp_probe_unit PRIVATE /O2 /W4)
else()
  target_compile_options(stage3d10az_qp_probe_unit PRIVATE -O2 -Wall -Wextra -Wpedantic)
endif()
add_test(NAME P10AZ_qp_probe_analytic_unit COMMAND stage3d10az_qp_probe_unit)

# P10BA: independent target, retaining all P10AZ output and numerical paths.
# Adds only 10 equal-area polar bands per existing radial subbin.
add_executable(stage3d10ba_polar_radial_audit
  src/stage3d10w_analytic_adjoint.cpp)
target_include_directories(stage3d10ba_polar_radial_audit PRIVATE
  src tests "${CMAKE_CURRENT_BINARY_DIR}/generated")
target_compile_definitions(stage3d10ba_polar_radial_audit PRIVATE
  STAGE3D10Y_ANALYTIC_SHELL_AUDIT STAGE3D10S_SPATIAL_AUDIT
  STAGE3D10AZ_QP_PROBE STAGE3D10BA_POLAR_AUDIT
  STAGE3D10K_SOURCE_ROOT="${CMAKE_CURRENT_SOURCE_DIR}")
if(MSVC)
  target_compile_options(stage3d10ba_polar_radial_audit PRIVATE /O2 /W4)
else()
  target_compile_options(stage3d10ba_polar_radial_audit PRIVATE
    -O2 -Wall -Wextra -Wpedantic)
endif()
if(STAGE3D06P_OPENMP AND OpenMP_CXX_FOUND)
  target_link_libraries(stage3d10ba_polar_radial_audit PRIVATE OpenMP::OpenMP_CXX)
endif()
if(WIN32)
  target_sources(stage3d10ba_polar_radial_audit PRIVATE src/win_process_memory.cpp)
  target_link_libraries(stage3d10ba_polar_radial_audit PRIVATE Psapi)
endif()
add_test(NAME P10BA_polar_preflight
  COMMAND stage3d10ba_polar_radial_audit --selftest)

add_executable(stage3d10ba_polar_unit tests/stage3d10v_analytic_shape.cpp)
target_include_directories(stage3d10ba_polar_unit PRIVATE src)
target_compile_definitions(stage3d10ba_polar_unit PRIVATE
  STAGE3D10Y_ANALYTIC_SHELL_AUDIT STAGE3D10AZ_QP_PROBE
  STAGE3D10BA_POLAR_AUDIT)
if(MSVC)
  target_compile_options(stage3d10ba_polar_unit PRIVATE /O2 /W4)
else()
  target_compile_options(stage3d10ba_polar_unit PRIVATE -O2 -Wall -Wextra -Wpedantic)
endif()
add_test(NAME P10BA_polar_analytic_unit COMMAND stage3d10ba_polar_unit)

# P10BD: fixed H2 mesh, fixed 900 s horizon, full-time polar QP derivative.
# Kept independent from P10BA: its 5/6 step baseline stays bitwise unchanged.
add_executable(stage3d10bd_temporal_polar_audit
  src/stage3d10w_analytic_adjoint.cpp)
target_include_directories(stage3d10bd_temporal_polar_audit PRIVATE
  src tests "${CMAKE_CURRENT_BINARY_DIR}/generated")
target_compile_definitions(stage3d10bd_temporal_polar_audit PRIVATE
  STAGE3D10Y_ANALYTIC_SHELL_AUDIT STAGE3D10S_SPATIAL_AUDIT
  STAGE3D10AZ_QP_PROBE STAGE3D10BA_POLAR_AUDIT
  STAGE3D10BD_TEMPORAL_AUDIT
  STAGE3D10K_SOURCE_ROOT="${CMAKE_CURRENT_SOURCE_DIR}")
if(MSVC)
  target_compile_options(stage3d10bd_temporal_polar_audit PRIVATE /O2 /W4)
else()
  target_compile_options(stage3d10bd_temporal_polar_audit PRIVATE
    -O2 -Wall -Wextra -Wpedantic)
endif()
if(STAGE3D06P_OPENMP AND OpenMP_CXX_FOUND)
  target_link_libraries(stage3d10bd_temporal_polar_audit PRIVATE OpenMP::OpenMP_CXX)
endif()
if(WIN32)
  target_sources(stage3d10bd_temporal_polar_audit PRIVATE src/win_process_memory.cpp)
  target_link_libraries(stage3d10bd_temporal_polar_audit PRIVATE Psapi)
endif()
add_test(NAME P10BD_temporal_polar_preflight
  COMMAND stage3d10bd_temporal_polar_audit --selftest)
add_executable(stage3d10bd_temporal_unit tests/stage3d10v_analytic_shape.cpp)
target_include_directories(stage3d10bd_temporal_unit PRIVATE src)
target_compile_definitions(stage3d10bd_temporal_unit PRIVATE
  STAGE3D10Y_ANALYTIC_SHELL_AUDIT STAGE3D10AZ_QP_PROBE
  STAGE3D10BA_POLAR_AUDIT STAGE3D10BD_TEMPORAL_AUDIT)
if(MSVC)
  target_compile_options(stage3d10bd_temporal_unit PRIVATE /O2 /W4)
else()
  target_compile_options(stage3d10bd_temporal_unit PRIVATE -O2 -Wall -Wextra -Wpedantic)
endif()
add_test(NAME P10BD_temporal_polar_unit COMMAND stage3d10bd_temporal_unit)

# P10BE: one new H2 full forward+adjoint at dt=25 s (36 time steps).
# Separate executable, leaving the validated P10BD 150/75/50 targets intact.
add_executable(stage3d10be_temporal_polar_audit
  src/stage3d10w_analytic_adjoint.cpp)
target_include_directories(stage3d10be_temporal_polar_audit PRIVATE
  src tests "${CMAKE_CURRENT_BINARY_DIR}/generated")
target_compile_definitions(stage3d10be_temporal_polar_audit PRIVATE
  STAGE3D10Y_ANALYTIC_SHELL_AUDIT STAGE3D10S_SPATIAL_AUDIT
  STAGE3D10AZ_QP_PROBE STAGE3D10BA_POLAR_AUDIT
  STAGE3D10BD_TEMPORAL_AUDIT STAGE3D10BE_TEMPORAL_AUDIT
  STAGE3D10K_SOURCE_ROOT="${CMAKE_CURRENT_SOURCE_DIR}")
if(MSVC)
  target_compile_options(stage3d10be_temporal_polar_audit PRIVATE /O2 /W4)
else()
  target_compile_options(stage3d10be_temporal_polar_audit PRIVATE
    -O2 -Wall -Wextra -Wpedantic)
endif()
if(STAGE3D06P_OPENMP AND OpenMP_CXX_FOUND)
  target_link_libraries(stage3d10be_temporal_polar_audit PRIVATE OpenMP::OpenMP_CXX)
endif()
if(WIN32)
  target_sources(stage3d10be_temporal_polar_audit PRIVATE src/win_process_memory.cpp)
  target_link_libraries(stage3d10be_temporal_polar_audit PRIVATE Psapi)
endif()
add_test(NAME P10BE_temporal_polar_preflight
  COMMAND stage3d10be_temporal_polar_audit --selftest)
add_executable(stage3d10be_temporal_unit tests/stage3d10v_analytic_shape.cpp)
target_include_directories(stage3d10be_temporal_unit PRIVATE src)
target_compile_definitions(stage3d10be_temporal_unit PRIVATE
  STAGE3D10Y_ANALYTIC_SHELL_AUDIT STAGE3D10AZ_QP_PROBE
  STAGE3D10BA_POLAR_AUDIT STAGE3D10BD_TEMPORAL_AUDIT
  STAGE3D10BE_TEMPORAL_AUDIT)
if(MSVC)
  target_compile_options(stage3d10be_temporal_unit PRIVATE /O2 /W4)
else()
  target_compile_options(stage3d10be_temporal_unit PRIVATE -O2 -Wall -Wextra -Wpedantic)
endif()
add_test(NAME P10BE_temporal_polar_unit COMMAND stage3d10be_temporal_unit)

add_executable(stage3d10y_analytic_shell_unit
  tests/stage3d10v_analytic_shape.cpp)
target_include_directories(stage3d10y_analytic_shell_unit PRIVATE src)
target_compile_definitions(stage3d10y_analytic_shell_unit PRIVATE
  STAGE3D10Y_ANALYTIC_SHELL_AUDIT)
if(MSVC)
 target_compile_options(stage3d10y_analytic_shell_unit PRIVATE /O2 /W4)
else()
 target_compile_options(stage3d10y_analytic_shell_unit PRIVATE
   -O2 -Wall -Wextra -Wpedantic)
endif()
add_test(NAME P10Y_analytic_shell_partition_unit
  COMMAND stage3d10y_analytic_shell_unit)

# M02: explicit registration of completed Stage3D10S run manifests.
# This target does not read FEM meshes or run numerical solvers.
add_executable(ice3d_register_manifest tools/ice3d_register_manifest.cpp)
if(MSVC)
  target_compile_options(ice3d_register_manifest PRIVATE /O2 /W4)
else()
  target_compile_options(ice3d_register_manifest PRIVATE -O2 -Wall -Wextra -Wpedantic)
endif()
add_test(NAME ICE3D_registry_manifest_selftest
  COMMAND ice3d_register_manifest --selftest)

# P10AG: isolated step-6 operator diagnostics; no FEM forward or Krylov solve.
add_executable(stage3d10ag_step6_diagnostic src/stage3d10ag_step6_diagnostic.cpp)
target_include_directories(stage3d10ag_step6_diagnostic PRIVATE
  src tests "${CMAKE_CURRENT_BINARY_DIR}/generated")
target_compile_definitions(stage3d10ag_step6_diagnostic PRIVATE
  STAGE3D10K_SOURCE_ROOT="${CMAKE_CURRENT_SOURCE_DIR}")
if(MSVC)
  target_compile_options(stage3d10ag_step6_diagnostic PRIVATE /O2 /W4)
else()
  target_compile_options(stage3d10ag_step6_diagnostic PRIVATE
    -O2 -Wall -Wextra -Wpedantic)
endif()
if(STAGE3D06P_OPENMP AND OpenMP_CXX_FOUND)
  target_link_libraries(stage3d10ag_step6_diagnostic PRIVATE OpenMP::OpenMP_CXX)
endif()
if(WIN32)
  target_sources(stage3d10ag_step6_diagnostic PRIVATE src/win_process_memory.cpp)
  target_link_libraries(stage3d10ag_step6_diagnostic PRIVATE Psapi)
endif()

# Stage3D10AG / LIT08: frozen-history peak moment under fixed Q3, varied B6 masks.
add_executable(stage3d10ag_frozen_mask src/stage3d10ag_frozen_mask.cpp)
target_include_directories(stage3d10ag_frozen_mask PRIVATE
  src tests "${CMAKE_CURRENT_BINARY_DIR}/generated")
target_compile_definitions(stage3d10ag_frozen_mask PRIVATE
  STAGE3D10K_SOURCE_ROOT="${CMAKE_CURRENT_SOURCE_DIR}")
if(MSVC)
  target_compile_options(stage3d10ag_frozen_mask PRIVATE /O2 /W4)
else()
  target_compile_options(stage3d10ag_frozen_mask PRIVATE -O2 -Wall -Wextra -Wpedantic)
endif()
if(STAGE3D06P_OPENMP AND OpenMP_CXX_FOUND)
  target_link_libraries(stage3d10ag_frozen_mask PRIVATE OpenMP::OpenMP_CXX)
endif()
if(WIN32)
  target_sources(stage3d10ag_frozen_mask PRIVATE src/win_process_memory.cpp)
  target_link_libraries(stage3d10ag_frozen_mask PRIVATE Psapi)
endif()
add_test(NAME LIT08_frozen_history_mask_selftest
  COMMAND stage3d10ag_frozen_mask --selftest)
