#!/usr/bin/env python3
"""P10ND: prepare read-only canonical M13 R2 bad Tet10 locator package."""
import ast,hashlib,json,shutil,zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
DEST=ROOT/'p10nd_m13_r2_bad_tet_readonly'
MESH=ROOT/'p10na_m13_r2_evidence/P10NA_M13_R2_CANDIDATE_UNVERIFIED.msh'
QUALITY=ROOT/'upload/P10NC_M13_R2_GMSH_QUALITY_RESULT.json'
SHA='57403ba43fa299417d519046cebdf50fa4968b670c071a8b7882748b50f51e9c'
ZIP=ROOT/'P10ND_M13_R2_READONLY_BAD_TET10_WINDOWS_20261125.zip'

def main():
    if DEST.exists() or ZIP.exists():raise RuntimeError('P10ND output exists; no overwrite')
    assert hashlib.sha256(MESH.read_bytes()).hexdigest()==SHA
    q=json.loads(QUALITY.read_text(encoding='utf-8-sig'))
    assert q['status']=='D031_QUALITY_HOLD' and not q['quality_gate_pass']
    assert q['mesh_sha256']==SHA and q['Tet10']==18004 and q['gmsh_version']=='4.15.2'
    assert q['qualities']['minSICN']['min']<.20 and q['qualities']['minSJ']['min']<.40
    template=(ROOT/'p10me_package/p10me_readonly_bad_tet10.py').read_text()
    script=(template.replace('P10ME','P10ND').replace('P10MD','P10NC')
         .replace('P10MB_M11_R1','P10NA_M13_R2')
         .replace('M11_R1','M13_R2').replace('M11','M13')
         .replace('244249fcc62d0b26877164dae1cc6a6528edd1d1e5973edad4dc79aad7872dab',SHA)
         .replace('15191','18004'))
    assert "MESH=HERE/'P10NA_M13_R2_CANDIDATE_UNVERIFIED.msh'" in script
    assert "QUAL=HERE/'P10NC_M13_R2_GMSH_QUALITY_RESULT.json'" in script
    assert "OUT=HERE/'P10ND_M13_R2_BAD_TET10_LOCATIONS.json'" in script
    ast.parse(script)
    DEST.mkdir()
    shutil.copy2(MESH,DEST/MESH.name)
    shutil.copy2(QUALITY,DEST/QUALITY.name)
    (DEST/'p10nd_readonly_bad_tet10.py').write_text(script)
    (DEST/'01_P10ND_M13_R2_READONLY_BAD_TET10.cmd').write_text(
      '@echo off\nif /I "%~1"=="--visible" goto RUN\n'
      'start "P10ND M13 R2 BAD TET10 READONLY" cmd.exe /K call "%~f0" --visible\n'
      'exit /b %ERRORLEVEL%\n:RUN\ncd /d "%~dp0"\n'
      'echo P10ND_M13_R2_READONLY_NO_MESH_NO_FEM_NO_MARKER\n'
      'where py >nul 2>nul\nif not errorlevel 1 (\n'
      '    py -3 -u p10nd_readonly_bad_tet10.py\n'
      ') else (\n    python -u p10nd_readonly_bad_tet10.py\n)\n'
      'set "P10ND_RC=%ERRORLEVEL%"\necho P10ND_END=%P10ND_RC%\nexit /b %P10ND_RC%\n',
      newline='\r\n')
    (DEST/'README_P10ND_RU.md').write_text(
      '# P10ND — адреса низкокачественных Tet10 сетки M13 R2\n\n'
      'M13 R2 D029 PASS, D031 HOLD: minSICN=0.162944789, minSJ=0.281159374. '
      'Не повторять попытку M13 R2 и не запускать FEM.\n\n'
      'Распаковать ZIP в новую папку, запустить `01_P10ND_M13_R2_READONLY_BAD_TET10.cmd` '
      '(Python, numpy, Gmsh Python API 4.15.2). Проверяется точная SHA сетки и D031. '
      'Программа выводит все Tet10 ниже порогов и топ-20 по каждому показателю, '
      'их центроиды, расстояния до стенки и полярную принадлежность. '
      'Только чтение: Gmsh generate, FEM и маркеры не используются.\n\n'
      'Вернуть **один** файл `P10ND_M13_R2_BAD_TET10_LOCATIONS.json`. '
      'Только после него сравним реальные дефекты R1 и R2 и выберем принцип коррекции.\n')
    with zipfile.ZipFile(ZIP,'x',zipfile.ZIP_DEFLATED,compresslevel=8) as z:
        for p in sorted(DEST.iterdir()):z.write(p,p.name)
    with zipfile.ZipFile(ZIP) as z:assert z.testzip() is None
    print(json.dumps({'protocol':'P10ND_M13_R2_BAD_TET10_READONLY_PACKAGE',
      'status':'READY_NO_NATIVE_GMSH_NO_MESH_NO_FEM_NO_MARKER',
      'archive_sha256':hashlib.sha256(ZIP.read_bytes()).hexdigest(),
      'archive_bytes':ZIP.stat().st_size,'mesh_sha256':SHA},indent=2))

if __name__=='__main__':main()
