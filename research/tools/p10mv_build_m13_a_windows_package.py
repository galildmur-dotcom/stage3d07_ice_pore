#!/usr/bin/env python3
"""Build a distinct M13 A Windows Gmsh-only one-shot package from pinned M12 sources.

Builder is source/packaging only. It never imports gmsh or executes FEM.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import re
import shutil
import zipfile

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT/'p10ml_package'
DST = ROOT/'p10mv_m13_a_package'
ZIP = ROOT/'P10MV_M13_A_R1_GUARDED_MESH_ONLY_WINDOWS_20261125.zip'
M12 = ROOT/'p10mn_package/P10ML_M12_R1_CANDIDATE_UNVERIFIED.msh'
M12Q = ROOT/'upload/P10MN_M12_R1_GMSH_QUALITY_RESULT.json'
M13 = ROOT/'p10mt_m13_source_only/P10MT_M13_A_existing_residual_1200_BINS.csv'
M13QA = ROOT/'p10mt_m13_source_only/P10MT_THREE_FIELDS_SOURCE_ONLY_QA.json'
M12_SHA = 'e3c5c5dc9bbcae3d0b2649e7afd4af49b47f6cb6db63329492975fb920abbd13'
M13_SHA = '5c63f14eb16ae9b2e5eb35b9257fcb17e401e82d53e17e29a787fbfd0ac73383'


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def replace_once(text, before, after):
    if text.count(before) != 1:
        raise RuntimeError('builder template expected once: '+before[:95])
    return text.replace(before, after)


def main():
    if DST.exists() or ZIP.exists():
        raise RuntimeError('existing M13 package/archive: never overwrite')
    assert sha(M12)==M12_SHA and sha(M13)==M13_SHA
    quality=json.loads(M12Q.read_text(encoding='utf-8-sig'))
    assert quality['mesh_sha256']==M12_SHA and quality['quality_gate_pass'] and quality['Tet10']==16333
    assert json.loads(M13QA.read_text())['variants']['A_existing_residual']['csv_sha256']==M13_SHA
    files = [p for p in SRC.iterdir() if p.is_file() and p.suffix in ('.geo','.msh','.csv','.json','.py')]
    existing={p.name for p in files}
    needed={'P10ML_one_M12_R1_worker.py','P10ML_guard.py','p10ml_progress.py'}
    assert needed<=existing
    DST.mkdir()
    for p in files:
        # Eliminate old M12 runner/guard and runtime outputs; retain all transitive inputs.
        if p.name in needed or p.name.startswith('P10ML_'):
            continue
        shutil.copy2(p,DST/p.name)
    for src,dest in ((M12,'M12_R1_ACCEPTED.msh'),(M12Q,'P10MN_M12_R1_GMSH_QUALITY_RESULT.json'),
                     (M13,'P10MT_M13_A_existing_residual_1200_BINS.csv'),
                     (M13QA,'P10MT_THREE_FIELDS_SOURCE_ONLY_QA.json')):
        shutil.copy2(src,DST/dest)

    worker=(SRC/'P10ML_one_M12_R1_worker.py').read_text()
    worker=worker.replace('P10ML','P10MV').replace('M12_R1_CANDIDATE_UNVERIFIED','M13_R1_CANDIDATE_UNVERIFIED')
    worker=replace_once(worker,
        "M12_FIELD_SHA='e779145ae4ffd37677b3d05c2b214d4b2f09520504c20bd4e8271f96e4b3c03f'",
        "M12_FIELD_SHA='e779145ae4ffd37677b3d05c2b214d4b2f09520504c20bd4e8271f96e4b3c03f'\n"
        f"M12_ACCEPTED_SHA='{M12_SHA}'\nM13_FIELD_SHA='{M13_SHA}'")
    worker=replace_once(worker,
        "    km=json.loads((HERE/'P10KM_M8_SOURCE_ONLY_DESIGN_QA.json').read_text())",
        "    if hashlib.sha256((HERE/'M12_R1_ACCEPTED.msh').read_bytes()).hexdigest()!=M12_ACCEPTED_SHA:\n"
        "        raise RuntimeError('accepted M12 physical parent mesh SHA drift; no M13')\n"
        "    q12=json.loads((HERE/'P10MN_M12_R1_GMSH_QUALITY_RESULT.json').read_text(encoding='utf-8-sig'))\n"
        "    if q12['mesh_sha256']!=M12_ACCEPTED_SHA or not q12['quality_gate_pass'] or q12['Tet10']!=16333:\n"
        "        raise RuntimeError('M12 D031 physical quality gate drift; no M13')\n"
        "    src13=HERE/'P10MT_M13_A_existing_residual_1200_BINS.csv'\n"
        "    if hashlib.sha256(src13.read_bytes()).hexdigest()!=M13_FIELD_SHA:\n"
        "        raise RuntimeError('M13 A source SHA drift; no mesh')\n"
        "    qa13=json.loads((HERE/'P10MT_THREE_FIELDS_SOURCE_ONLY_QA.json').read_text())\n"
        "    if qa13['status']!='PASS_SOURCE_ONLY_NO_GMSH_NO_MESH_NO_FEM' or qa13['bins']!=1200 or qa13['variants']['A_existing_residual']['csv_sha256']!=M13_FIELD_SHA:\n"
        "        raise RuntimeError('M13 A source QA mismatch; no mesh')\n"
        "    km=json.loads((HERE/'P10KM_M8_SOURCE_ONLY_DESIGN_QA.json').read_text())")
    worker=replace_once(worker,
        "    if abs(m12.center_kappa.max()-1)>1e-12:",
        "    m13=Field(rows(HERE/'P10HA_SPATIAL_KAPPA_1200_BINS.csv'),\n"
        "              rows(src13),'0.1')\n"
        "    if abs(m13.center_kappa.max()-1)>1e-12:\n"
        "        raise RuntimeError('M13 A normalization mismatch; no mesh')\n"
        "    if abs(m12.center_kappa.max()-1)>1e-12:")
    worker=replace_once(worker,
        "            ratio=old_factor*new_factor*m4_factor*m5_factor*m6_factor*incremental_m7*incremental_m8*incremental_m9*incremental_m10*incremental_m11*repair_factor*incremental_m12",
        "            kappa13=polar_blend_m8(m13.kappa(position),dmm,mu)\n"
        "            incremental_m13=(1-.20*kappa13)**(1/3)\n"
        "            ratio=old_factor*new_factor*m4_factor*m5_factor*m6_factor*incremental_m7*incremental_m8*incremental_m9*incremental_m10*incremental_m11*repair_factor*incremental_m12*incremental_m13")
    worker=replace_once(worker,
        "                'M12_new_source_field_sha256':M12_FIELD_SHA,",
        "                'M12_new_source_field_sha256':M12_FIELD_SHA,\n"
        "                'accepted_M12_R1_sha256':M12_ACCEPTED_SHA,\n"
        "                'M13_new_source_field_sha256':M13_FIELD_SHA,\n"
        "                'M13_variant':'A_existing_residual',\n"
        "                'M13_incremental_nominal_volume_reduction_max':.20,\n"
        "                'M13_polar_plateau_C2':True,")
    worker=worker.replace("'accepted_M12_R1':False", "'accepted_M13_R1':False")
    worker=worker.replace('M12 R1','M13 R1').replace('M12_R1_DISTINCT','M13_R1_DISTINCT')
    (DST/'P10MV_one_M13_R1_worker.py').write_text(worker)

    guard=(SRC/'P10ML_guard.py').read_text().replace('P10ML','P10MV')
    guard=guard.replace('M12_R1_CANDIDATE_UNVERIFIED','M13_R1_CANDIDATE_UNVERIFIED')
    guard=guard.replace('P10MV_one_M12_R1_worker.py','P10MV_one_M13_R1_worker.py')
    guard=guard.replace('ONE_M12_ATTEMPT','ONE_M13_ATTEMPT').replace('M12_b3ad647bf3ac295c','M13_e3c5c5dc9bbcae3d0b2_A')
    guard=guard.replace('M12_UNVERIFIED','M13_UNVERIFIED').replace('M12_R1','M13_R1')
    guard=guard.replace('accepted_M12_R1=False','accepted_M13_R1=False')
    guard=guard.replace('M12 R1','M13 R1').replace('M12 C2','M13 C2')
    guard=guard.replace('P10MV_R1_DISTINCT_M12_C2_MESH_ONLY_GUARD',
                        'P10MV_R1_DISTINCT_M13_A_C2_MESH_ONLY_GUARD')
    guard=replace_once(guard,
        "'p10ml_progress.py': '7e01c155dc19775bc4984b69a21264f4c7724273c8cf5d5ebbe598f7e67ad041'}",
        "'p10mv_progress.py': 'PENDING_WORKER_PIN'}")
    # The inherited PIN table remains fixed; patch only the generated worker,
    # progress reporter, accepted M12 evidence and M13 A source/QA hashes.
    progress=(SRC/'p10ml_progress.py').read_text().replace('P10ML','P10MV')
    (DST/'p10mv_progress.py').write_text(progress)
    guard=guard.replace('from p10ml_progress import Watchdog','from p10mv_progress import Watchdog')
    worker_pin=sha(DST/'P10MV_one_M13_R1_worker.py')
    progress_pin=sha(DST/'p10mv_progress.py')
    guard=guard.replace("'P10MV_one_M12_R1_worker.py': 'f5ac37f09941f6d4e2a538edf6d74e29dd30462a760265a467de3627052282e3', ", '')
    guard=guard.replace("'p10mv_progress.py': 'PENDING_WORKER_PIN'", 
        "'P10MV_one_M13_R1_worker.py': '"+worker_pin+"', "
        "'p10mv_progress.py': '"+progress_pin+"', "
        "'M12_R1_ACCEPTED.msh': '"+M12_SHA+"', "
        "'P10MN_M12_R1_GMSH_QUALITY_RESULT.json': '"+sha(DST/'P10MN_M12_R1_GMSH_QUALITY_RESULT.json')+"', "
        "'P10MT_M13_A_existing_residual_1200_BINS.csv': '"+M13_SHA+"', "
        "'P10MT_THREE_FIELDS_SOURCE_ONLY_QA.json': '"+sha(DST/'P10MT_THREE_FIELDS_SOURCE_ONLY_QA.json')+"'")
    assert 'P10ML_' not in guard and 'P10ML_' not in worker or 'P10ML_M12' in worker
    (DST/'P10MV_guard.py').write_text(guard)

    (DST/'01_P10MV_M13_A_PREFLIGHT_NO_GMSH.cmd').write_text(
        '@echo off\nif /I "%~1"=="--visible" goto RUN\n'
        'start "P10MV M13 PREFLIGHT ONLY" cmd.exe /K call "%~f0" --visible\nexit /b %ERRORLEVEL%\n'
        ':RUN\ncd /d "%~dp0"\necho P10MV_SOURCE_PREFLIGHT_NO_GMSH_NO_FEM_NO_MARKER\n'
        'where py >nul 2>nul\nif not errorlevel 1 (py -3 -u P10MV_guard.py --source-only) '
        'else (python -u P10MV_guard.py --source-only)\n'
        'echo P10MV_PREFLIGHT_EXIT=%ERRORLEVEL%\n',newline='\r\n')
    (DST/'02_P10MV_ONE_M13_A_R1_MESH_ONLY.cmd').write_text(
        '@echo off\nif /I "%~1"=="--visible" goto RUN\n'
        'start "P10MV M13 A ONE MESH - NO FEM" cmd.exe /K call "%~f0" --visible\nexit /b %ERRORLEVEL%\n'
        ':RUN\ncd /d "%~dp0"\necho P10MV_ONE_M13_A_3D_MESH_ONLY\n'
        'where py >nul 2>nul\nif not errorlevel 1 (py -3 -u P10MV_guard.py --run) '
        'else (python -u P10MV_guard.py --run)\n'
        'echo P10MV_MESH_EXIT=%ERRORLEVEL%\n',newline='\r\n')
    (DST/'README_P10MV_RU.md').write_text(
        '# P10MV: M13 R1, вариант A, только одна попытка построения 3D-сетки\n\n'
        '1. Распакуйте архив в **новую** пустую папку Windows 11. Нужны Python 3, numpy, gmsh Python API **4.15.2**.\n'
        '2. Запустите `01_P10MV_M13_A_PREFLIGHT_NO_GMSH.cmd` (SHA без Gmsh, FEM и маркеров).\n'
        '3. Если PASS, запустите **один раз** `02_P10MV_ONE_M13_A_R1_MESH_ONLY.cmd`. '
        'До расходования маркера программа снова проверит API Gmsh 4.15.2. Никакого FEM.\n'
        '4. Ожидайте независимый вывод раз в 15 секунд; максимум 20 минут, 8 GiB памяти.\n'
        '5. При любом исходе верните `P10MV_R1_M13_UNVERIFIED_EVIDENCE.zip`; не повторяйте попытку.\n\n'
        'Это ещё не принятая сетка: после получения архива нужны отдельные D029/D031. '
        'Исходная принятая M12 имеет 16333 Tet10, SHA '+M12_SHA+'.\n'
        'В поле добавлен **только** множитель M13 A: `(1-0.20*kappa13)**(1/3)`; '
        'варианты B/C не используются.\n')

    # Verify offline SHA closure and optional source-only mode after producing files.
    names=set(re.findall(r"'([^']+)': '[0-9a-f]{64}'",guard.split('PIN=',1)[1].split('}\n',1)[0]))
    assert all((DST/name).is_file() for name in names),sorted(name for name in names if not (DST/name).is_file())
    with zipfile.ZipFile(ZIP,'x',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for p in sorted(DST.iterdir()):
            if p.is_file(): z.write(p,p.name)
    print(json.dumps({'protocol':'P10MV_M13_A_PACKAGE_BUILDER',
        'status':'BUILT_UNEXECUTED_NO_GMSH_NO_FEM_NO_MARKER',
        'archive':str(ZIP),'files':len(list(DST.iterdir())),
        'archive_sha256':sha(ZIP),'worker_sha256':worker_pin,
        'source_M13_A_sha256':M13_SHA,'parent_M12_mesh_sha256':M12_SHA},indent=2))


if __name__=='__main__': main()
