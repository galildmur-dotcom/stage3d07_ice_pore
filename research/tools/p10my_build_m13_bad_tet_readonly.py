#!/usr/bin/env python3
"""P10MY: package canonical read-only locator of M13 R1 D031 failures."""
import hashlib,json,shutil,zipfile,ast
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
DEST=ROOT/'p10my_m13_bad_tet_readonly'
MESH=ROOT/'p10mv_m13_evidence/P10MV_M13_R1_CANDIDATE_UNVERIFIED.msh'
QUALITY=ROOT/'upload/P10MX_M13_R1_GMSH_QUALITY_RESULT.json'
SHA='3c0b292007dce69cb70559a215ce7367b6c33fc1f7c46a6ca3396041481a1b1e'
ZIP=ROOT/'P10MY_M13_R1_READONLY_BAD_TET10_WINDOWS_20261125.zip'

def main():
    if DEST.exists() or ZIP.exists():raise RuntimeError('P10MY output exists: no overwrite')
    assert hashlib.sha256(MESH.read_bytes()).hexdigest()==SHA
    q=json.loads(QUALITY.read_text(encoding='utf-8-sig'))
    assert q['status']=='D031_QUALITY_HOLD' and q['mesh_sha256']==SHA and q['Tet10']==18048
    assert q['qualities']['minSICN']['min']<.2 and q['qualities']['minSJ']['min']<.4
    original=(ROOT/'p10me_package/p10me_readonly_bad_tet10.py').read_text()
    script=(original.replace('P10ME','P10MY').replace('P10MD','P10MX')
            .replace('P10MB_M11_R1','P10MV_M13_R1')
            .replace('M11_R1','M13_R1').replace('M11','M13')
            .replace('244249fcc62d0b26877164dae1cc6a6528edd1d1e5973edad4dc79aad7872dab',SHA)
            .replace('15191','18048'))
    # The original P10ME locator uses the canonical Gmsh element-quality API,
    # returns all failures and top-20 per metric with centroids and wall location.
    assert "MESH=HERE/'P10MV_M13_R1_CANDIDATE_UNVERIFIED.msh'" in script
    assert "QUAL=HERE/'P10MX_M13_R1_GMSH_QUALITY_RESULT.json'" in script
    assert "OUT=HERE/'P10MY_M13_R1_BAD_TET10_LOCATIONS.json'" in script
    assert SHA in script and '18048' in script
    ast.parse(script)
    DEST.mkdir()
    shutil.copy2(MESH,DEST/MESH.name)
    shutil.copy2(QUALITY,DEST/QUALITY.name)
    (DEST/'p10my_readonly_bad_tet10.py').write_text(script)
    (DEST/'01_P10MY_READONLY_BAD_TET10.cmd').write_text(
        '@echo off\nif /I "%~1"=="--visible" goto RUN\n'
        'start "P10MY M13 BAD TET10 READONLY" cmd.exe /K call "%~f0" --visible\n'
        'exit /b %ERRORLEVEL%\n:RUN\ncd /d "%~dp0"\n'
        'echo P10MY_READONLY_M13_NO_MESH_NO_FEM_NO_MARKER\n'
        'where py >nul 2>nul\nif not errorlevel 1 (\n'
        '    py -3 -u p10my_readonly_bad_tet10.py\n'
        ') else (\n    python -u p10my_readonly_bad_tet10.py\n)\n'
        'set "P10MY_RC=%ERRORLEVEL%"\necho P10MY_READONLY_END=%P10MY_RC%\nexit /b %P10MY_RC%\n',
        newline='\r\n')
    (DEST/'README_P10MY_RU.md').write_text(
        '# P10MY — поиск низкокачественных элементов M13 R1\n\n'
        'D029 PASS, но D031 HOLD: minSICN=0.1777656211 <0.20; '
        'minSJ=0.3221630762 <0.40. Повторное построение M13 R1 запрещено.\n\n'
        'Распаковать архив в новую папку Windows и запустить '
        '`01_P10MY_READONLY_BAD_TET10.cmd`. Требуются Gmsh Python API 4.15.2 и numpy. '
        'Скрипт сверит SHA сетки и D031, найдёт все Tet10 ниже порогов и '
        '20 худших по каждой метрике, определит центроиды, расстояние до поры и полярную принадлежность. '
        'Только чтение: без Gmsh generate, FEM и маркеров.\n\n'
        'Вернуть **один** `P10MY_M13_R1_BAD_TET10_LOCATIONS.json`; '
        'по нему будет спроектирована независимая M13 R2 локальная C2-коррекция.\n')
    with zipfile.ZipFile(ZIP,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=8) as z:
        for p in sorted(DEST.iterdir()):z.write(p,p.name)
    with zipfile.ZipFile(ZIP) as z:assert z.testzip() is None
    print(json.dumps({'protocol':'P10MY_M13_R1_BAD_TET10_READONLY_PACKAGE',
        'status':'READY_NO_NATIVE_GMSH_NO_MESH_NO_FEM_NO_MARKER',
        'archive_sha256':hashlib.sha256(ZIP.read_bytes()).hexdigest(),
        'archive_bytes':ZIP.stat().st_size,'exact_mesh_sha256':SHA},indent=2))

if __name__=='__main__':main()
