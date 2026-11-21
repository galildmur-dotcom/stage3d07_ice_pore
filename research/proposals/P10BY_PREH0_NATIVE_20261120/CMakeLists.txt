cmake_minimum_required(VERSION 3.20)
project(P10BY_Optin_Readonly_Native_Preflight LANGUAGES CXX)
include(CTest)

# Paths refer only to three independently verified SOURCE trees. Never use
# the user's dirty G:/ildar/Stage3D07 worktree as P10BY_PINNED_ROOT.
set(P10BY_PINNED_ROOT "" CACHE PATH "Exact P10BM isolated src/tests root")
set(P10BY_P10BX_ROOT "" CACHE PATH "P10BX proposal root")
set(P10BY_P10BW_ROOT "" CACHE PATH "P10BW proposal root")
foreach(name P10BY_PINNED_ROOT P10BY_P10BX_ROOT P10BY_P10BW_ROOT)
  if(NOT IS_DIRECTORY "${${name}}")
    message(FATAL_ERROR "P10BY_STOP: set an existing clean ${name}")
  endif()
endforeach()
file(TO_CMAKE_PATH "${P10BY_PINNED_ROOT}" pinned_forward_path)
string(TOLOWER "${pinned_forward_path}" pinned_lower)
if(pinned_lower STREQUAL "g:/ildar/stage3d07" OR
   pinned_lower MATCHES "^g:/ildar/stage3d07/$")
  message(FATAL_ERROR "P10BY_STOP: refuse user's original dirty G: source root")
endif()

file(STRINGS "${CMAKE_CURRENT_LIST_DIR}/P10BY_PINNED_SHA256.txt" pinned_files)
set(validated 0)
foreach(row IN LISTS pinned_files)
  if(row MATCHES "^#" OR row STREQUAL "")
    continue()
  endif()
  string(REPLACE "|" ";" fields "${row}")
  list(LENGTH fields field_count)
  if(NOT field_count EQUAL 2)
    message(FATAL_ERROR "P10BY_STOP: malformed source manifest row ${row}")
  endif()
  list(GET fields 0 relative_path)
  list(GET fields 1 expected_sha256)
  set(source_file "${P10BY_PINNED_ROOT}/${relative_path}")
  if(NOT EXISTS "${source_file}")
    message(FATAL_ERROR "P10BY_STOP: source missing ${relative_path}")
  endif()
  file(SHA256 "${source_file}" actual_sha256)
  if(NOT actual_sha256 STREQUAL expected_sha256)
    message(FATAL_ERROR "P10BY_STOP: source SHA256 mismatch ${relative_path}")
  endif()
  math(EXPR validated "${validated}+1")
endforeach()
if(NOT validated EQUAL 35)
  message(FATAL_ERROR "P10BY_STOP: expected 35 original source blobs")
endif()

# Freeze the review proposals too. These values reflect the already
# published P10BW/P10BX Git blobs; no automatic patch application occurs.
function(check_component path expected)
  if(NOT EXISTS "${path}")
    message(FATAL_ERROR "P10BY_STOP: proposal component missing: ${path}")
  endif()
  file(SHA256 "${path}" actual)
  if(NOT actual STREQUAL expected)
    message(FATAL_ERROR "P10BY_STOP: proposal component SHA256 mismatch: ${path}")
  endif()
endfunction()
check_component("${P10BY_P10BX_ROOT}/src/stage3d10p_partial_audit.cpp"
 "57754cfaa031fddb391e6b211a6f083346475611d180676c0c4987926ea54b1b")
check_component("${P10BY_P10BX_ROOT}/src/stage3d10w_analytic_adjoint.cpp"
 "1d769e559aa561817685b56949bf649e6ceddb89da4cfc294cc18738d6d82df8")
check_component("${P10BY_P10BX_ROOT}/stage3d10bx_thermal_step_hook.hpp"
 "79b716c389a6a9dd466d65d795ad3a67bda206bdd636eec0fb03962dc3155574")
check_component("${P10BY_P10BW_ROOT}/stage3d10bw_thermal_qp_partition.hpp"
 "71992ba7e8c0b44d7832c5d8566ef8886517bbd87f953b119271746483f0fa23")
check_component("${P10BY_P10BW_ROOT}/P10BW_thermal_qp_native_unit.cpp"
 "719a9db9f3c3221acdfc096a88cfbb1cdb81307ba931463f3ff62726e10a03c6")
message(STATUS "P10BY_SHA256_35_PLUS_5_OK original_files=${validated}")

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
find_package(OpenMP COMPONENTS CXX)
set(shared_includes "${P10BY_PINNED_ROOT}/src" "${P10BY_PINNED_ROOT}/tests"
    "${P10BY_P10BX_ROOT}" "${P10BY_P10BW_ROOT}")

add_executable(p10by_temporal_native_unit P10BY_temporal_thermal_qp_native_unit.cpp)
target_include_directories(p10by_temporal_native_unit PRIVATE ${shared_includes})

add_executable(p10by_optin_dependency_selftest P10BY_unitonly_entry.cpp)
target_include_directories(p10by_optin_dependency_selftest PRIVATE ${shared_includes}
  "${P10BY_P10BX_ROOT}/src")
target_compile_definitions(p10by_optin_dependency_selftest PRIVATE
  STAGE3D10K_SOURCE_ROOT="${P10BY_PINNED_ROOT}")

foreach(target p10by_temporal_native_unit p10by_optin_dependency_selftest)
  if(MSVC)
    target_compile_options(${target} PRIVATE /O2 /W3)
  else()
    target_compile_options(${target} PRIVATE -O2 -Wall -Wextra -Wpedantic)
  endif()
  if(OpenMP_CXX_FOUND)
    target_link_libraries(${target} PRIVATE OpenMP::OpenMP_CXX)
  endif()
endforeach()

# Exactly two bounded native units. No executable here exposes a physical
# FEM CLI and no CTest entry loads a physical mesh or runs --preflight.
add_test(NAME P10BY_temporal_QP_operator_unit COMMAND p10by_temporal_native_unit)
add_test(NAME P10BY_optin_dependency_unit COMMAND p10by_optin_dependency_selftest)
