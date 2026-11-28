#!/usr/bin/env python3
"""Package a read-only canonical Gmsh D031 check for real M11 R1."""
import ast,hashlib,json,shutil,zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
OLD=ROOT/'p10lx_package_r2'
NEW=ROOT/'p10md_package'
M11=ROOT/'p10mb_m11_evidence/P10MB_M11_R1_CANDIDATE_UNVERIFIED.msh'
SHA='244249fcc62d0b26877164dae1cc6a6528edd1d1e5973edad4dc79aad7872dab'
MESH='P10MB_M11_R1_CANDIDATE_UNVERIFIED.msh'
SCRIPT='p10md_readonly_gmsh_quality.py'
RESULT='P10MD_M11_R1_GMSH_QUALITY_RESULT.json'

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    if NEW.exists():raise RuntimeError('P10MD package already exists')
    if sha(M11)!=SHA:raise RuntimeError('accepted candidate M11 SHA drift')
    NEW.mkdir()
    shutil.copy2(M11,NEW/MESH)
    s=(OLD/'p10lx_readonly_gmsh_quality.py').read_text()
    s=s.replace('P10LX','P10MD').replace('p10lx','p10md')
    s=s.replace('M10_R1','M11_R1').replace('M10 R1','M11 R1')
    s=s.replace('P10LV_M11_R1_CANDIDATE_UNVERIFIED.msh',MESH)
    s=s.replace('022166c7fb9555a511cf2cd2479ceb949c6b809d05d124832d8d7644c0bebc9c',SHA)
    s=s.replace('13996','15191')
    assert f"M8=HERE/'{MESH}'" in s
    assert f"OUT=HERE/'{RESULT}'" in s
    assert f"EXPECTED='{SHA}'" in s
    ast.parse(s,filename=SCRIPT)
    (NEW/SCRIPT).write_text(s)
    cmd=(OLD/'01_P10LX_READONLY_QUALITY.cmd').read_text()
    cmd=cmd.replace('P10LX','P10MD').replace('p10lx','p10md').replace('M10','M11')
    assert SCRIPT in cmd
    (NEW/'01_P10MD_READONLY_QUALITY.cmd').write_text(cmd)
    (NEW/'README_P10MD_RU.md').write_text(
      '# P10MD — каноническая проверка качества принятого кандидата M11\n\n'
      'Распакуйте архив в новую папку и запустите `01_P10MD_READONLY_QUALITY.cmd`. '
      'Программа только читает точную M11 SHA256 '+SHA+', '
      'считает minSICN/minSJ/gamma/minDetJac средствами Gmsh Python API 4.15.2 '
      'и записывает один файл `'+RESULT+'`. '
      'Никакой генерации сетки, физического FEM или новых one-shot маркеров. '
      'Ожидаемое время 5–30 секунд.\n')
    archive=ROOT/'P10MD_M11_R1_READONLY_GMSH_D031_WINDOWS_20261125.zip'
    with zipfile.ZipFile(archive,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=8) as z:
        for p in sorted(NEW.iterdir()):z.write(p,arcname='P10MD_M11_R1/'+p.name)
    with zipfile.ZipFile(archive) as z:assert z.testzip() is None
    qa={'protocol':'P10MD_M11_READONLY_D031_PREPARED','status':'PREPARED_NO_GMSH_NO_MESH_NO_FEM',
        'M11_sha256':SHA,'archive_sha256':sha(archive),'archive_bytes':archive.stat().st_size,
        'source_file_count':4,'mesh_attempts':0,'FEM_attempts':0}
    (ROOT/'research/P10MD_M11_D031_READONLY_PREPARED_QA.json').write_text(json.dumps(qa,indent=2)+'\n')
    print(json.dumps(qa,indent=2))

if __name__=='__main__':main()
