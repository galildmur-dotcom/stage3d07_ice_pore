@echo off
setlocal EnableExtensions
rem Stage 3D-09D4: generate ONE mesh. Example: GENERATE_HP_LEVELS.cmd HP8
set LEVEL=%~1
if /I not "%LEVEL%"=="HP2" if /I not "%LEVEL%"=="HP4" if /I not "%LEVEL%"=="HP8" (
 echo Usage: GENERATE_HP_LEVELS.cmd HP2^|HP4^|HP8
 exit /b 2
)
set "PROJECT=%~dp0.."
if not defined GMSH_EXE set "GMSH_EXE=gmsh.exe"
if /I not "%GMSH_EXE%"=="gmsh.exe" (
 if not exist "%GMSH_EXE%" (echo GMSH_EXE not found: "%GMSH_EXE%" & exit /b 3)
) else (
 where /q gmsh.exe
 if errorlevel 1 (echo gmsh.exe is not in PATH. Set environment variable GMSH_EXE to its full path. & exit /b 3)
)
set "GEO=%~dp0sphere_pore_%LEVEL%_wall.geo"
set "MESH=%PROJECT%\meshes\%LEVEL%.msh"
set "LOG=%PROJECT%\meshes\%LEVEL%_gmsh.log"
if exist "%MESH%" (
 echo Mesh "%MESH%" already exists. Refusing to overwrite.
 echo Rename or move the old mesh if you intentionally want to regenerate it.
 exit /b 4
)
echo Generating %LEVEL% with Gmsh; logarithm: %LOG%
"%GMSH_EXE%" "%GEO%" -3 -nt 4 -format msh2 -o "%MESH%" -v 3 > "%LOG%" 2>&1
if errorlevel 1 (
 echo ERROR: Gmsh failed. See "%LOG%".
 if exist "%MESH%" del "%MESH%"
 exit /b 5
)
if not exist "%MESH%" (echo ERROR: output mesh missing & exit /b 6)
echo Created "%MESH%"
echo Validate with stage3d09c_shape_three --mesh %LEVEL% ... --dry-run before expensive FEM!
exit /b 0
