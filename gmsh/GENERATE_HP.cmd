@echo off
setlocal EnableExtensions
set "PROJECT=%~dp0.."
set "GMSH=gmsh"
if not "%~1"=="" set "GMSH=%~1"
if not exist "%PROJECT%\meshes" mkdir "%PROJECT%\meshes"
if exist "%PROJECT%\meshes\HP.msh" (
 echo HP.msh already exists. Will not overwrite a research mesh.
 echo Rename it manually only after saving all results dependent on this file.
 exit /b 3
)
echo Generating HP locally refined pore wall mesh...
"%GMSH%" "%~dp0sphere_pore_HP_local.geo" -3 -nt 4 -format msh2 -o "%PROJECT%\meshes\HP.msh" > "%PROJECT%\meshes\HP_gmsh.log" 2>&1
if errorlevel 1 (
 echo Gmsh failed. Check meshes\HP_gmsh.log. Supply full gmsh.exe path as argument.
 exit /b 2
)
if not exist "%PROJECT%\meshes\HP.msh" (
 echo Gmsh returned without HP.msh. Check log.
 exit /b 2
)
echo HP.msh created. Check pore mesh using Python before FEM.
exit /b 0
