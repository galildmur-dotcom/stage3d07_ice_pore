cmake_minimum_required(VERSION 3.20)
project(P10FN_ANY_APPROVED_MESH_FRESH_PHYSICS LANGUAGES CXX)
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
find_package(OpenMP REQUIRED COMPONENTS CXX)
add_executable(stage3d10fn_any_mesh_full4d stage3d10fn_any_mesh_full4d.cpp)
target_include_directories(stage3d10fn_any_mesh_full4d PRIVATE
  "${CMAKE_CURRENT_SOURCE_DIR}/src" "${CMAKE_CURRENT_SOURCE_DIR}/tests"
  "${CMAKE_CURRENT_SOURCE_DIR}")
target_compile_definitions(stage3d10fn_any_mesh_full4d PRIVATE
  STAGE3D10K_SOURCE_ROOT="${CMAKE_CURRENT_SOURCE_DIR}")
target_link_libraries(stage3d10fn_any_mesh_full4d PRIVATE OpenMP::OpenMP_CXX)
target_compile_options(stage3d10fn_any_mesh_full4d PRIVATE -O2)
if(WIN32)
  target_sources(stage3d10fn_any_mesh_full4d PRIVATE src/win_process_memory.cpp)
  target_link_libraries(stage3d10fn_any_mesh_full4d PRIVATE Psapi)
endif()
