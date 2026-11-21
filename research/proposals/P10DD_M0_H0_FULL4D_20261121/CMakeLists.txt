cmake_minimum_required(VERSION 3.20)
project(P10DD_M0_H0_Complete_4D_QP LANGUAGES CXX)

set(STAGE3D07_SOURCE_ROOT "" CACHE PATH "Clean Stage3D07 GitHub checkout root, NOT G:/ildar/Stage3D07")
if(STAGE3D07_SOURCE_ROOT STREQUAL "")
  set(STAGE3D07_SOURCE_ROOT "${CMAKE_CURRENT_SOURCE_DIR}" CACHE PATH
      "Isolated source bundle root" FORCE)
endif()
if(NOT EXISTS "${STAGE3D07_SOURCE_ROOT}/src/stage3d10p_partial_audit.cpp" OR
   NOT EXISTS "${STAGE3D07_SOURCE_ROOT}/src/stage3d10w_analytic_adjoint.cpp")
  message(FATAL_ERROR "P10DD_STOP: exact source checkout is missing")
endif()
file(TO_CMAKE_PATH "${STAGE3D07_SOURCE_ROOT}" normalized_source)
string(TOLOWER "${normalized_source}" normalized_lower)
if(normalized_lower STREQUAL "g:/ildar/stage3d07" OR
   normalized_lower MATCHES "^g:/ildar/stage3d07/")
  message(FATAL_ERROR "P10DD_STOP: do not configure from the user's dirty working tree")
endif()
file(READ "${STAGE3D07_SOURCE_ROOT}/src/stage3d10p_partial_audit.cpp" base_source)
if(NOT base_source MATCHES "STAGE3D10DD_FULL4D")
  message(FATAL_ERROR "P10DD_STOP: the source checkout lacks the P10DD integration")
endif()
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
find_package(OpenMP REQUIRED COMPONENTS CXX)

add_executable(stage3d10dd_m0_h0_full4d stage3d10dd_m0_full4d.cpp)
target_include_directories(stage3d10dd_m0_h0_full4d PRIVATE
 "${STAGE3D07_SOURCE_ROOT}/src" "${STAGE3D07_SOURCE_ROOT}/tests"
 "${CMAKE_CURRENT_SOURCE_DIR}")
target_compile_definitions(stage3d10dd_m0_h0_full4d PRIVATE
 STAGE3D10K_SOURCE_ROOT="${normalized_source}")
target_compile_options(stage3d10dd_m0_h0_full4d PRIVATE -O2 -Wall -Wextra -Wpedantic)
target_link_libraries(stage3d10dd_m0_h0_full4d PRIVATE OpenMP::OpenMP_CXX)

add_executable(p10dd_4d_synthetic_unit p10dd_4d_synthetic_unit.cpp)
target_include_directories(p10dd_4d_synthetic_unit PRIVATE
 "${STAGE3D07_SOURCE_ROOT}/src" "${STAGE3D07_SOURCE_ROOT}/tests"
 "${CMAKE_CURRENT_SOURCE_DIR}")
# The synthetic TU includes the legacy P10K harness, whose Config default
# needs a concrete source root.  Without this definition Windows MinGW stops
# at STAGE3D06_ROOT_DIR (which is not defined in the isolated P10DD bundle).
target_compile_definitions(p10dd_4d_synthetic_unit PRIVATE
 STAGE3D10K_SOURCE_ROOT="${normalized_source}")
target_compile_options(p10dd_4d_synthetic_unit PRIVATE -O2 -Wall -Wextra -Wpedantic)
target_link_libraries(p10dd_4d_synthetic_unit PRIVATE OpenMP::OpenMP_CXX)

if(WIN32)
 target_sources(stage3d10dd_m0_h0_full4d PRIVATE
   "${STAGE3D07_SOURCE_ROOT}/src/win_process_memory.cpp")
 target_sources(p10dd_4d_synthetic_unit PRIVATE
   "${STAGE3D07_SOURCE_ROOT}/src/win_process_memory.cpp")
 target_link_libraries(stage3d10dd_m0_h0_full4d PRIVATE Psapi)
 target_link_libraries(p10dd_4d_synthetic_unit PRIVATE Psapi)
endif()
message(STATUS "P10DD_CONFIGURE_ONLY_NO_FEM source=${normalized_source}")
