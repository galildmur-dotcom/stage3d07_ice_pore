cmake_minimum_required(VERSION 3.20)
project(P10DK_M1_FULL4D_SOURCE_ONLY LANGUAGES CXX)

# Standalone source ZIP, never configure within the historical G: source.
set(STAGE3D07_SOURCE_ROOT "${CMAKE_CURRENT_SOURCE_DIR}" CACHE PATH
    "Exact isolated P10DK source ZIP root")
file(TO_CMAKE_PATH "${STAGE3D07_SOURCE_ROOT}" source_normalized)
string(TOLOWER "${source_normalized}" source_lower)
if(source_lower STREQUAL "g:/ildar/stage3d07" OR
   source_lower MATCHES "^g:/ildar/stage3d07/")
  message(FATAL_ERROR "P10DK_STOP: source must be in a NEW isolated directory")
endif()
if(NOT EXISTS "${STAGE3D07_SOURCE_ROOT}/src/stage3d10p_partial_audit.cpp" OR
   NOT EXISTS "${STAGE3D07_SOURCE_ROOT}/src/stage3d10w_analytic_adjoint.cpp" OR
   NOT EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/stage3d10dd_4d_partition.hpp")
  message(FATAL_ERROR "P10DK_STOP: incomplete source-only bundle")
endif()

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
find_package(OpenMP REQUIRED COMPONENTS CXX)
option(P10DK_ENABLE_PHYSICAL "Physical FEM requires NEW explicit authorization" OFF)
if(P10DK_ENABLE_PHYSICAL)
  message(FATAL_ERROR
    "P10DK_SOURCE_ONLY_STOP: this R1 source bundle is NOT a physical-launch "
    "authorization. Prepare a separately approved bounded R2 runner.")
endif()

add_executable(stage3d10dk_m1_full4d stage3d10dk_m1_full4d.cpp)
add_executable(p10dk_4d_synthetic_unit p10dd_4d_synthetic_unit.cpp)
foreach(target stage3d10dk_m1_full4d p10dk_4d_synthetic_unit)
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
message(STATUS "P10DK_CONFIGURED_SOURCE_ONLY: PHYSICAL=OFF M1=9736_Tet10")
