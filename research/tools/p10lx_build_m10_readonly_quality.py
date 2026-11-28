#!/usr/bin/env python3
"""Build P10LX readonly Gmsh 4.15.2 M10 quality check (no meshing/FEM)."""
import ast,hashlib,json,shutil,zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
OLD=ROOT/'p10la_package'
DEST=ROOT/'p10lx_package_r2'
M10=ROOT/'p10lv_m10_evidence/P10LV_M10_R1_CANDIDATE_UNVERIFIED.msh'
SHA='022166c7fb9555a511cf2cd2479ceb949c6b809d05d124832d8d7644c0bebc9c'

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    if DEST.exists():raise RuntimeError('P10LX package exists')
    assert sha(M10)==SHA
    DEST.mkdir()
    shutil.copy2(M10,DEST/'P10LV_M10_R1_CANDIDATE_UNVERIFIED.msh')
    source=(OLD/'p10la_readonly_gmsh_quality.py').read_text()
    source=source.replace('P10LA','P10LX').replace('p10la','p10lx')
    source=source.replace('M9_R1','M10_R1').replace('M9 R1','M10 R1')
    source=source.replace('P10KY_M10_R1_CANDIDATE_UNVERIFIED.msh',
                          'P10LV_M10_R1_CANDIDATE_UNVERIFIED.msh')
    source=source.replace('a40aca54636a752afe4d7babe9d03e741b2e988b9ad3dbb6f356728bff035a58',SHA)
    source=source.replace('13166','13996')
    (DEST/'p10lx_readonly_gmsh_quality.py').write_text(source)
    cmd=(OLD/'01_P10LA_READONLY_QUALITY.cmd').read_text().replace('P10LA','P10LX').replace('p10la','p10lx').replace('M9','M10')
    (DEST/'01_P10LX_READONLY_QUALITY.cmd').write_text(cmd)
    (DEST/'README_P10LX_RU.md').write_text(
        '# P10LX — канонические показатели Gmsh для уже построенной M10\n\n'
        'Запустите один файл `01_P10LX_READONLY_QUALITY.cmd` на Windows с Gmsh Python 4.15.2. '
        'Программа только читает закреплённую M10, вычисляет minSICN/minSJ/gamma/minDetJac '
        'и записывает `P10LX_M10_R1_GMSH_QUALITY_RESULT.json`. '
        'Не строит сетку, не запускает FEM, не использует однократный маркер. '
        'Пришлите только результат JSON. Ожидаемо 5–30 с.\n')
    ast.parse(source)
    assert "M8=HERE/'P10LV_M10_R1_CANDIDATE_UNVERIFIED.msh'" in source
    assert sha(DEST/'P10LV_M10_R1_CANDIDATE_UNVERIFIED.msh')==SHA
    archive=ROOT/'P10LX_M10_R1_READONLY_QUALITY_WINDOWS_R2_20261125.zip'
    with zipfile.ZipFile(archive,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=8) as z:
        for p in sorted(DEST.iterdir()):z.write(p,arcname='P10LX_M10_R1/'+p.name)
    with zipfile.ZipFile(archive) as z:assert z.testzip() is None
    qa={'status':'PREPARED_NO_GMSH_NO_MESH_NO_FEM','P10LX_archive_sha256':sha(archive),
        'M10_sha256':SHA,'files':4,'mesh_generation_attempts':0,'FEM_attempts':0}
    (ROOT/'research/P10LX_M10_READONLY_QA.json').write_text(json.dumps(qa,indent=2)+'\n')
    print(json.dumps(qa,indent=2))

if __name__=='__main__':main()
