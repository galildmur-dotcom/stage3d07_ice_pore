#!/usr/bin/env python3
"""Read-only Gmsh D031 quality gate for exact M11 R2 candidate."""
import ast,hashlib,json,shutil,zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
OLD=ROOT/'p10md_package'
NEW=ROOT/'p10mh_package'
SRC=ROOT/'p10mf_m11_r2_evidence/P10MF_M11_R2_CANDIDATE_UNVERIFIED.msh'
SHA='b3ad647bf3ac295c87f388782447efd33f880e11e331f497402c6596aca6c726'
MESH='P10MF_M11_R2_CANDIDATE_UNVERIFIED.msh'
SCRIPT='p10mh_readonly_gmsh_quality.py'
OUT='P10MH_M11_R2_GMSH_QUALITY_RESULT.json'

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    if NEW.exists():raise RuntimeError('P10MH package exists; no overwrite')
    if sha(SRC)!=SHA:raise RuntimeError('M11 R2 SHA mismatch')
    NEW.mkdir()
    shutil.copy2(SRC,NEW/MESH)
    s=(OLD/'p10md_readonly_gmsh_quality.py').read_text()
    s=s.replace('P10MD','P10MH').replace('p10md','p10mh')
    s=s.replace('M11_R1','M11_R2').replace('M11 R1','M11 R2')
    s=s.replace('P10MB_M11_R2_CANDIDATE_UNVERIFIED.msh',MESH)
    s=s.replace('244249fcc62d0b26877164dae1cc6a6528edd1d1e5973edad4dc79aad7872dab',SHA)
    s=s.replace('15191','15055')
    assert f"M8=HERE/'{MESH}'" in s
    assert f"OUT=HERE/'{OUT}'" in s
    assert f"EXPECTED='{SHA}'" in s
    ast.parse(s)
    (NEW/SCRIPT).write_text(s)
    cmd=(OLD/'01_P10MD_READONLY_QUALITY.cmd').read_text()
    cmd=cmd.replace('P10MD','P10MH').replace('p10md','p10mh').replace('M11 R1','M11 R2')
    assert SCRIPT in cmd
    (NEW/'01_P10MH_READONLY_QUALITY.cmd').write_text(cmd)
    (NEW/'README_P10MH_RU.md').write_text(
       '# M11 R2: только чтение канонических качеств Gmsh D031\n\n'
       'Запустить `01_P10MH_READONLY_QUALITY.cmd` в новой папке Windows '
       'с Python API Gmsh 4.15.2. Измеряются minSICN, minSJ, gamma, minDetJac '
       'для точной R2 сетки SHA256 '+SHA+'. Ничего не перестраивается, '
       'FEM и маркеры отсутствуют. Ожидание 5–30 секунд. '
       'Вернуть один файл `'+OUT+'`.\n')
    archive=ROOT/'P10MH_M11_R2_READONLY_GMSH_D031_WINDOWS_20261125.zip'
    with zipfile.ZipFile(archive,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=8) as z:
        for p in sorted(NEW.iterdir()):z.write(p,arcname='P10MH_M11_R2/'+p.name)
    with zipfile.ZipFile(archive) as z:assert z.testzip() is None
    report={'protocol':'P10MH_M11_R2_READONLY_PREPARED',
       'status':'PREPARED_NO_GMSH_NO_MESH_NO_FEM','M11_R2_sha256':SHA,
       'archive_sha256':sha(archive),'archive_bytes':archive.stat().st_size,
       'files':4,'FEM_attempts':0,'mesh_attempts':0}
    (ROOT/'research/P10MH_M11_R2_READONLY_QA.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
