#!/usr/bin/env python3
"""Pack independent read-only Gmsh 4.15.2 canonical quality audit for M9 R1."""
from pathlib import Path
import hashlib
import zipfile

ROOT=Path(__file__).resolve().parents[2]
OLD=ROOT/'p10kt_package'
MESH=ROOT/'p10kz_inputs/P10KY_M9_R1_CANDIDATE_UNVERIFIED.msh'
NEW=ROOT/'p10la_package'
ZIP=ROOT/'P10LA_M9_R1_READONLY_D031_WINDOWS_20261125.zip'
SHA='a40aca54636a752afe4d7babe9d03e741b2e988b9ad3dbb6f356728bff035a58'

def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    if NEW.exists() or ZIP.exists():raise RuntimeError('output already exists; no overwrite')
    assert digest(MESH)==SHA
    NEW.mkdir()
    import shutil
    shutil.copy2(MESH,NEW/'P10KY_M9_R1_CANDIDATE_UNVERIFIED.msh')
    source=(OLD/'p10kt_readonly_gmsh_quality.py').read_text(encoding='utf8')
    source=source.replace('P10KT','P10LA').replace('p10kt','p10la').replace('M8 R3','M9 R1').replace('M8_R3','M9_R1')
    source=source.replace('P10KR_M9_R1_CANDIDATE_UNVERIFIED.msh','P10KY_M9_R1_CANDIDATE_UNVERIFIED.msh')
    source=source.replace('40949482ac74d80ae7ac44c88af527a705650d34c1ffcd0de7cd01dc2bd2fa8d',SHA)
    source=source.replace('if len(tags)!=12546','if len(tags)!=13166')
    (NEW/'p10la_readonly_gmsh_quality.py').write_text(source,encoding='utf8')
    cmd=(OLD/'01_P10KT_READONLY_QUALITY.cmd').read_text(encoding='utf8')
    cmd=cmd.replace('P10KT','P10LA').replace('p10kt','p10la').replace('M8 R3','M9 R1')
    (NEW/'01_P10LA_READONLY_QUALITY.cmd').write_text(cmd,encoding='utf8')
    readme=('# P10LA — M9 R1 canonical Gmsh quality read-only\n\n'
            '1. Распакуйте архив в новую папку.\n'
            '2. Запустите `01_P10LA_READONLY_QUALITY.cmd` (ориентир 5–30 с).\n'
            '3. Верните только `P10LA_M9_R1_GMSH_QUALITY_RESULT.json`.\n\n'
            'Внутри: только чтение уже готовой M9 сетки SHA256 '+SHA+'; '
            'никакого generate, FEM, маркеров или перезапуска P10KY.\n'
            'Нужен Gmsh Python 4.15.2, как в P10KY. '
            'Критерии minSICN ≥ 0.20, minSJ ≥ 0.40, gamma ≥ 0.15, minDetJac > 0.\n')
    (NEW/'README_P10LA_RU.md').write_text(readme,encoding='utf8')
    assert 'gmsh.model.mesh.generate' not in source
    import ast
    ast.parse(source)
    with zipfile.ZipFile(ZIP,'x',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for file in sorted(NEW.iterdir()):z.write(file,file.name)
    with zipfile.ZipFile(ZIP) as z:assert z.testzip() is None
    print('PASS_NO_GMSH_NO_MESH_NO_FEM',ZIP,digest(ZIP),ZIP.stat().st_size)

if __name__=='__main__':main()
