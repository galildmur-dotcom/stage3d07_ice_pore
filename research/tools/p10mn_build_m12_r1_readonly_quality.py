#!/usr/bin/env python3
"""P10MN: read-only canonical Gmsh D031 quality for exactly M12 R1."""
import ast,hashlib,json,shutil,zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
OLD=ROOT/'p10mh_package'
NEW=ROOT/'p10mn_package'
SRC=ROOT/'p10ml_m12_evidence/P10ML_M12_R1_CANDIDATE_UNVERIFIED.msh'
SHA='e3c5c5dc9bbcae3d0b2649e7afd4af49b47f6cb6db63329492975fb920abbd13'
MESH='P10ML_M12_R1_CANDIDATE_UNVERIFIED.msh'
SCRIPT='p10mn_readonly_gmsh_quality.py'
OUT='P10MN_M12_R1_GMSH_QUALITY_RESULT.json'

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    if NEW.exists():raise RuntimeError('P10MN package exists; no overwrite')
    if sha(SRC)!=SHA:raise RuntimeError('M12 R1 SHA mismatch')
    d029=json.loads((ROOT/'p10ml_m12_evidence/P10MM_M12_R1_D029.json').read_text())
    if not d029['D029_PASS'] or d029['M12_R1']['mesh_sha256']!=SHA:
        raise RuntimeError('M12 R1 independent curved D029 not PASS')
    NEW.mkdir()
    shutil.copy2(SRC,NEW/MESH)
    s=(OLD/'p10mh_readonly_gmsh_quality.py').read_text()
    s=s.replace('P10MH','P10MN').replace('p10mh','p10mn')
    s=s.replace('M11_R2','M12_R1').replace('M11 R2','M12 R1')
    s=s.replace('P10MF_M12_R1_CANDIDATE_UNVERIFIED.msh',MESH)
    s=s.replace('b3ad647bf3ac295c87f388782447efd33f880e11e331f497402c6596aca6c726',SHA)
    s=s.replace('15055','16333')
    assert f"M8=HERE/'{MESH}'" in s
    assert f"OUT=HERE/'{OUT}'" in s
    assert f"EXPECTED='{SHA}'" in s
    ast.parse(s)
    (NEW/SCRIPT).write_text(s)
    cmd=(OLD/'01_P10MH_READONLY_QUALITY.cmd').read_text()
    cmd=cmd.replace('P10MH','P10MN').replace('p10mh','p10mn').replace('M11 R2','M12 R1')
    assert SCRIPT in cmd
    (NEW/'01_P10MN_READONLY_QUALITY.cmd').write_text(cmd)
    (NEW/'README_P10MN_RU.md').write_text(
      '# M12 R1: независимая D031, исключительно чтение существующей сетки\n\n'
      'D029 уже PASS. Запустите `01_P10MN_READONLY_QUALITY.cmd` '
      'с Gmsh Python API 4.15.2 на Windows. Вычисляются minSICN, '
      'minSJ, gamma и minDetJac для точной M12 R1, SHA256 '+SHA+'. '
      'Нет Gmsh generation, FEM или маркера. Примерно 5–30 секунд. '
      'Пришлите один `'+OUT+'`.\n')
    archive=ROOT/'P10MN_M12_R1_READONLY_GMSH_D031_WINDOWS_20261125.zip'
    with zipfile.ZipFile(archive,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=8) as z:
        for p in sorted(NEW.iterdir()):z.write(p,arcname='P10MN_M12_R1/'+p.name)
    with zipfile.ZipFile(archive) as z:assert z.testzip() is None
    report={'protocol':'P10MN_M12_R1_READONLY_PREPARED',
       'status':'PREPARED_NO_GMSH_NO_MESH_NO_FEM','M12_R1_sha256':SHA,
       'archive_sha256':sha(archive),'archive_bytes':archive.stat().st_size,
       'files':4,'FEM_attempts':0,'mesh_attempts':0}
    (ROOT/'research/P10MN_M12_R1_READONLY_QA.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
