cmake_minimum_required(VERSION 3.20)
project(P10CA_One_H0_Analytic_Thermal_QP LANGUAGES CXX)

# Build-only project: configure/build MUST NOT start a physical H0 or preflight.
# The sole target wraps the exact P10BX proposal of P10W analytic adjoint.
set(P10CA_PINNED_ROOT "" CACHE PATH "P10BM exact isolated src/tests root")
set(P10CA_P10BX_ROOT "" CACHE PATH "P10BX exact opt-in proposal root")
set(P10CA_P10BW_ROOT "" CACHE PATH "P10BW exact thermal QP unit root")
set(P10CA_P10BY_ROOT "" CACHE PATH "P10BY and P10BZ R2 unit provenance root")
foreach(name P10CA_PINNED_ROOT P10CA_P10BX_ROOT P10CA_P10BW_ROOT P10CA_P10BY_ROOT)
  if(NOT IS_DIRECTORY "${${name}}")
    message(FATAL_ERROR "P10CA_STOP: missing exact clean bundle ${name}")
  endif()
endforeach()
file(TO_CMAKE_PATH "${P10CA_PINNED_ROOT}" pinned_forward_path)
string(TOLOWER "${pinned_forward_path}" pinned_lower)
if(pinned_lower STREQUAL "g:/ildar/stage3d07" OR
   pinned_lower MATCHES "^g:/ildar/stage3d07/")
  message(FATAL_ERROR "P10CA_STOP: original dirty source must never be the CMake input")
endif()

file(SHA256 "${P10CA_P10BY_ROOT}/P10BY_PINNED_SHA256.txt" manifest_hash)
if(NOT manifest_hash STREQUAL
   "bce45c5757796ecc505ca6e0899de912c4ad4441fb05d007f1d2c41192d2f2ce")
  message(FATAL_ERROR "P10CA_STOP: original pinned manifest changed")
endif()
file(STRINGS "${P10CA_P10BY_ROOT}/P10BY_PINNED_SHA256.txt" source_lines)
set(original_count 0)
foreach(line IN LISTS source_lines)
  if(line MATCHES "^#" OR line STREQUAL "")
    continue()
  endif()
  string(REPLACE "|" ";" columns "${line}")
  list(LENGTH columns ncols)
  if(NOT ncols EQUAL 2)
    message(FATAL_ERROR "P10CA_STOP: invalid historical manifest row")
  endif()
  list(GET columns 0 rel)
  list(GET columns 1 expected)
  if(NOT EXISTS "${P10CA_PINNED_ROOT}/${rel}")
    message(FATAL_ERROR "P10CA_STOP: missing original ${rel}")
  endif()
  file(SHA256 "${P10CA_PINNED_ROOT}/${rel}" actual)
  if(NOT actual STREQUAL expected)
    message(FATAL_ERROR "P10CA_STOP: original source SHA mismatch ${rel}")
  endif()
  math(EXPR original_count "${original_count}+1")
endforeach()
if(NOT original_count EQUAL 35)
  message(FATAL_ERROR "P10CA_STOP: expected exactly 35 historical manifest entries")
endif()

function(require_component rel expected)
  if(NOT EXISTS "${rel}")
    message(FATAL_ERROR "P10CA_STOP: missing exact proposal component ${rel}")
  endif()
  file(SHA256 "${rel}" actual)
  if(NOT actual STREQUAL expected)
    message(FATAL_ERROR "P10CA_STOP: SHA mismatch in proposal component ${rel}")
  endif()
endfunction()
require_component("${P10CA_PINNED_ROOT}/src/win_process_memory.cpp"
 "c299d890b0f3a04f86974fb664120a36681eef464ffbb617eabc8e57e07a5e09")
require_component("${P10CA_P10BX_ROOT}/src/stage3d10p_partial_audit.cpp"
 "57754cfaa031fddb391e6b211a6f083346475611d180676c0c4987926ea54b1b")
require_component("${P10CA_P10BX_ROOT}/src/stage3d10w_analytic_adjoint.cpp"
 "1d769e559aa561817685b56949bf649e6ceddb89da4cfc294cc18738d6d82df8")
require_component("${P10CA_P10BX_ROOT}/stage3d10bx_thermal_step_hook.hpp"
 "79b716c389a6a9dd466d65d795ad3a67bda206bdd636eec0fb03962dc3155574")
require_component("${P10CA_P10BW_ROOT}/stage3d10bw_thermal_qp_partition.hpp"
 "71992ba7e8c0b44d7832c5d8566ef8886517bbd87f953b119271746483f0fa23")
require_component("${P10CA_P10BW_ROOT}/P10BW_thermal_qp_native_unit.cpp"
 "719a9db9f3c3221acdfc096a88cfbb1cdb81307ba931463f3ff62726e10a03c6")
require_component("${P10CA_P10BY_ROOT}/P10BY_temporal_thermal_qp_native_unit.cpp"
 "c06b7245212d7e6d2e1ded93bf4695245b61e51845d882330c73107fb68825ee")
require_component("${P10CA_P10BY_ROOT}/P10BY_unitonly_entry.cpp"
 "080a27aca4bf9d27ba5c245c2dfdd4730a30f185a25df978a3ee3e9c0dfb8024")
require_component("${P10CA_P10BY_ROOT}/CMakeLists.txt"
 "bbf5f43f17f2c607edf4cb12550058d519fc1668354c7b28d57ef6cfee483239")
message(STATUS "P10CA_BUNDLED_SOURCE_SHA256_OK original=36 proposals=8 total=44")

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
find_package(OpenMP REQUIRED COMPONENTS CXX)

# The P10BX/src W file includes its sibling diagnostic P10P by quotation,
# which prevents the unmodified pinned/src P10P from shadowing this proposal.
add_executable(p10ca_h0_analytic_qp
 "${P10CA_P10BX_ROOT}/src/stage3d10w_analytic_adjoint.cpp")
target_include_directories(p10ca_h0_analytic_qp PRIVATE
 "${P10CA_PINNED_ROOT}/src" "${P10CA_PINNED_ROOT}/tests"
 "${P10CA_P10BX_ROOT}/src" "${P10CA_P10BX_ROOT}" "${P10CA_P10BW_ROOT}")
target_compile_definitions(p10ca_h0_analytic_qp PRIVATE
 STAGE3D10BX_THERMAL_QP_DIAGNOSTIC=1
 STAGE3D10K_SOURCE_ROOT="${pinned_forward_path}")
target_compile_options(p10ca_h0_analytic_qp PRIVATE -O2 -Wall -Wextra -Wpedantic)
target_link_libraries(p10ca_h0_analytic_qp PRIVATE OpenMP::OpenMP_CXX)
if(WIN32)
  target_sources(p10ca_h0_analytic_qp PRIVATE
    "${P10CA_PINNED_ROOT}/src/win_process_memory.cpp")
  target_link_libraries(p10ca_h0_analytic_qp PRIVATE Psapi)
endif()

message(STATUS "P10CA_CONFIGURE_BUILD_ONLY_NO_FEM")
# Deliberately NO add_test, custom RUN target, or --preflight call here.
