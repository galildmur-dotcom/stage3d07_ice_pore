cmake_minimum_required(VERSION 3.20)
project(P10DL_M1_FRESH_FORWARD_ONE_SHOT LANGUAGES CXX)
set(STAGE3D07_SOURCE_ROOT "${CMAKE_CURRENT_SOURCE_DIR}" CACHE PATH
    "Isolated P10DL source ZIP root")
file(TO_CMAKE_PATH "${STAGE3D07_SOURCE_ROOT}" source_normalized)
get_filename_component(root_real "${STAGE3D07_SOURCE_ROOT}" REALPATH)
get_filename_component(here_real "${CMAKE_CURRENT_SOURCE_DIR}" REALPATH)
if(NOT root_real STREQUAL here_real)
  message(FATAL_ERROR "P10DL_STOP: source root must equal exact isolated ZIP directory")
endif()
string(TOLOWER "${source_normalized}" source_lower)
if(source_lower STREQUAL "g:/ildar/stage3d07" OR
   source_lower MATCHES "^g:/ildar/stage3d07/")
  message(FATAL_ERROR "P10DL_STOP: DO NOT build within original source tree")
endif()
if(NOT EXISTS "${STAGE3D07_SOURCE_ROOT}/src/stage3d10p_partial_audit.cpp" OR
   NOT EXISTS "${STAGE3D07_SOURCE_ROOT}/src/stage3d10w_analytic_adjoint.cpp" OR
   NOT EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/stage3d10dd_4d_partition.hpp")
  message(FATAL_ERROR "P10DL_STOP: standalone source bundle incomplete")
endif()
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
find_package(OpenMP REQUIRED COMPONENTS CXX)
add_executable(stage3d10dl_m1_full4d stage3d10dl_m1_full4d.cpp)
add_executable(p10dl_4d_synthetic_unit p10dd_4d_synthetic_unit.cpp)
foreach(target stage3d10dl_m1_full4d p10dl_4d_synthetic_unit)
  target_include_directories(${target} PRIVATE
    "${STAGE3D07_SOURCE_ROOT}/src"
    "${STAGE3D07_SOURCE_ROOT}/tests"
    "${CMAKE_CURRENT_SOURCE_DIR}")
  target_compile_definitions(${target} PRIVATE
    STAGE3D10K_SOURCE_ROOT="${source_normalized}")
  target_compile_options(${target} PRIVATE -O2 -Wall -Wextra -Wpedantic)
  target_link_libraries(${target} PRIVATE OpenMP::OpenMP_CXX)
  if(WIN32)
    target_sources(${target} PRIVATE
      "${STAGE3D07_SOURCE_ROOT}/src/win_process_memory.cpp")
    target_link_libraries(${target} PRIVATE Psapi)
  endif()
endforeach()
message(STATUS "P10DL_CONFIGURED: physical executable HAS guard; Python one-shot launcher required")
