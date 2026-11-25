#!/usr/bin/env python3
"""Prepare a *distinct* P10KY M9 R1 Gmsh mesh-only Windows one-shot package.

Never imports Gmsh, generates a mesh, consumes markers, or runs the FEM solver.
"""
from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path
import shutil
import zipfile


ROOT=Path(__file__).resolve().parents[2]
OLD=ROOT/'p10kr_package'
NEW=ROOT/'p10ky_package'
ZIP=ROOT/'P10KY_M9_R1_GUARDED_MESH_ONLY_WINDOWS_20261125.zip'
M8=ROOT/'p10kv_package/P10KV_WORK/M8.msh'
SOURCE=ROOT/'p10kx_source'
M8_SHA='40949482ac74d80ae7ac44c88af527a705650d34c1ffcd0de7cd01dc2bd2fa8d'
M9_CSV_SHA='ddf7adeaeffffdab480c8bee5b234998236c53a1320aed511d6da20f0c09957f'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def replace_exact(source,old,new,expected=1):
    if source.count(old)!=expected:
        raise ValueError(f'{old!r}: expected {expected}, actual {source.count(old)}')
    return source.replace(old,new)


def main():
    if NEW.exists() or ZIP.exists():
        raise RuntimeError('P10KY package already present: do not overwrite')
    if sha(M8)!=M8_SHA or sha(SOURCE/'P10KX_M9_M8_MINUS_M7_SIGNED4D_1200_BINS.csv')!=M9_CSV_SHA:
        raise RuntimeError('source M8 mesh or P10KX field pin mismatch')
    oldguard=(OLD/'P10KR_guard.py').read_text(encoding='utf8')
    oldpins=ast.literal_eval(oldguard.split('PIN=',1)[1].split('\n\n',1)[0])
    assert all(sha(OLD/name)==digest for name,digest in oldpins.items())
    NEW.mkdir()
    skip={'P10KR_one_M8_R3_worker.py','p10kr_progress.py'}
    for name in oldpins:
        if name not in skip:
            shutil.copy2(OLD/name,NEW/name)
    for src,dst in [(M8,'M8.msh'),
                    (SOURCE/'P10KX_M9_M8_MINUS_M7_SIGNED4D_1200_BINS.csv',
                     'P10KX_M9_M8_MINUS_M7_SIGNED4D_1200_BINS.csv'),
                    (SOURCE/'P10KX_M9_SOURCE_ONLY_QA.json','P10KX_M9_SOURCE_ONLY_QA.json')]:
        shutil.copy2(src,NEW/dst)

    worker=(OLD/'P10KR_one_M8_R3_worker.py').read_text(encoding='utf8')
    worker=worker.replace('P10KR','P10KY').replace('M8_R3','M9_R1').replace('M8 R3','M9 R1')
    worker=replace_exact(worker,"ACCEPTED_M7_SHA='875c9177de24612d0078f7a792b4b7641a2e604973cb1353500710c87693bb3d'",
        "ACCEPTED_M7_SHA='875c9177de24612d0078f7a792b4b7641a2e604973cb1353500710c87693bb3d'\n"
        "ACCEPTED_M8_SHA='"+M8_SHA+"'\n"
        "M9_FIELD_SHA='"+M9_CSV_SHA+"'")
    worker=replace_exact(worker,"    km=json.loads((HERE/'P10KM_M8_SOURCE_ONLY_DESIGN_QA.json').read_text())",
        "    if hashlib.sha256((HERE/'M8.msh').read_bytes()).hexdigest()!=ACCEPTED_M8_SHA:\n"
        "        raise RuntimeError('accepted P10KU M8 R3 mesh SHA mismatch; no M9')\n"
        "    m9source=HERE/'P10KX_M9_M8_MINUS_M7_SIGNED4D_1200_BINS.csv'\n"
        "    if hashlib.sha256(m9source.read_bytes()).hexdigest()!=M9_FIELD_SHA:\n"
        "        raise RuntimeError('P10KX M9 field SHA mismatch; no mesh')\n"
        "    m9qa=json.loads((HERE/'P10KX_M9_SOURCE_ONLY_QA.json').read_text())\n"
        "    if (m9qa['status']!='PASS_SOURCE_ONLY_NO_GMSH_NO_MESH_NO_FEM'\n"
        "            or m9qa['source_csv_sha256']!=M9_FIELD_SHA or m9qa['bins']!=1200):\n"
        "        raise RuntimeError('P10KX M9 source-only QA mismatch; no mesh')\n"
        "    km=json.loads((HERE/'P10KM_M8_SOURCE_ONLY_DESIGN_QA.json').read_text())")
    worker=replace_exact(worker,
        "    m8=Field(rows(HERE/'P10HA_SPATIAL_KAPPA_1200_BINS.csv'),\n"
        "             rows(HERE/'P10KM_M8_LATE_TIME_SIGNED4D_1200_BINS.csv'),'0.1')",
        "    m8=Field(rows(HERE/'P10HA_SPATIAL_KAPPA_1200_BINS.csv'),\n"
        "             rows(HERE/'P10KM_M8_LATE_TIME_SIGNED4D_1200_BINS.csv'),'0.1')\n"
        "    m9=Field(rows(HERE/'P10HA_SPATIAL_KAPPA_1200_BINS.csv'),\n"
        "             rows(m9source),'0.1')\n"
        "    if abs(m9.center_kappa.max()-1)>1e-12:\n"
        "        raise RuntimeError('M9 source normalization mismatch; no mesh')")
    worker=replace_exact(worker,
        "            ratio=old_factor*new_factor*m4_factor*m5_factor*m6_factor*incremental_m7*incremental_m8",
        "            kappa9=polar_blend_m8(m9.kappa(position),dmm,mu)\n"
        "            incremental_m9=(1-.20*kappa9)**(1/3)\n"
        "            ratio=old_factor*new_factor*m4_factor*m5_factor*m6_factor*incremental_m7*incremental_m8*incremental_m9")
    worker=replace_exact(worker,"                'M8_additional_nominal_volume_reduction_max':.20,",
        "                'M8_additional_nominal_volume_reduction_max':.20,\n"
        "                'accepted_M8_R3_sha256':ACCEPTED_M8_SHA,\n"
        "                'M9_new_source_field_sha256':M9_FIELD_SHA,\n"
        "                'M9_additional_nominal_volume_reduction_max':.20,\n"
        "                'M9_polar_plateau_C2':True,")
    worker=replace_exact(worker,"                'candidate_mesh_sha256':hashlib.sha256(OUT.read_bytes()).hexdigest()}",
        "                'candidate_mesh_sha256':hashlib.sha256(OUT.read_bytes()).hexdigest(),\n"
        "                'accepted_M9':False,'FEM_attempts':0}")
    worker=worker.replace("'P10KY_M9_R1_DISTINCT_GMSH_3D_MESH_ONLY'",
                          "'P10KY_M9_R1_DISTINCT_GMSH_3D_MESH_ONLY'")
    tree=ast.parse(worker)
    assert not any(isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='polar_blend_m8'
                   for t in n.targets) for n in ast.walk(tree))
    assert worker.count('incremental_m9=')==1
    (NEW/'P10KY_one_M9_R1_worker.py').write_text(worker,encoding='utf8')

    progress=(OLD/'p10kr_progress.py').read_text(encoding='utf8').replace('P10KR','P10KY')
    (NEW/'p10ky_progress.py').write_text(progress,encoding='utf8')
    newpins={name:sha(NEW/name) for name in oldpins if name not in skip}
    for name in ('M8.msh','P10KX_M9_M8_MINUS_M7_SIGNED4D_1200_BINS.csv',
                 'P10KX_M9_SOURCE_ONLY_QA.json','P10KY_one_M9_R1_worker.py','p10ky_progress.py'):
        newpins[name]=sha(NEW/name)
    guard=oldguard.replace('P10KR','P10KY').replace('p10kr_progress','p10ky_progress')
    guard=guard.replace('M8_R3','M9_R1').replace('M8 R3','M9 R1')
    guard=guard.replace('R3_M8','R1_M9')
    guard=replace_exact(guard,'P10KY_R3_ONE_M8_ATTEMPT_CONSUMED.marker',
                        'P10KY_R1_ONE_M9_ATTEMPT_CONSUMED.marker') if 'P10KY_R3_ONE_M8_ATTEMPT_CONSUMED.marker' in guard else guard
    guard=guard.replace('P10KY_R3_M8_875c9177de24612d_ONE_ATTEMPT.marker',
                        'P10KY_R1_M9_40949482ac74d80a_ONE_ATTEMPT.marker')
    guard=guard.replace('P10KY_R3_M8_UNVERIFIED_EVIDENCE.zip',
                        'P10KY_R1_M9_UNVERIFIED_EVIDENCE.zip')
    guard=guard.replace('P10KY_M8_R3_CANDIDATE_UNVERIFIED.msh',
                        'P10KY_M9_R1_CANDIDATE_UNVERIFIED.msh')
    guard=guard.replace('P10KY_one_M8_R3_worker.py','P10KY_one_M9_R1_worker.py')
    guard=guard.replace('accepted_M8=False','accepted_M9=False')
    guard=guard.replace('new_mesh_3D_attempts=1','new_mesh_3D_attempts=1')
    guard=guard.replace('expected_mesh_s=15-180','expected_mesh_s=20-240')
    guard=guard.replace('MAX_WALL=900','MAX_WALL=1200')
    guard=guard.replace('max_wall_s=900','max_wall_s=1200')
    guard=guard.replace('wall_limit_s=900','wall_limit_s=1200')
    guard=guard.replace('profile_marker_consumed=user_mark.exists()','profile_marker_consumed=user_mark.exists()')
    # After mechanical substitutions, verify the safety-critical immutable names.
    guard=guard.replace('P10KY_R3_ONE_M9_ATTEMPT_CONSUMED.marker',
                        'P10KY_R1_ONE_M9_ATTEMPT_CONSUMED.marker')
    guard=guard.replace('P10KY_R3_M9_875c9177de24612d_ONE_ATTEMPT.marker',
                        'P10KY_R1_M9_40949482ac74d80a_ONE_ATTEMPT.marker')
    guard=guard.replace('P10KY_R1_M9_875c9177de24612d_ONE_ATTEMPT.marker',
                        'P10KY_R1_M9_40949482ac74d80a_ONE_ATTEMPT.marker')
    guard=guard.replace('P10KY_R3_PREFLIGHT_PASS','P10KY_R1_PREFLIGHT_PASS')
    guard=guard.replace('P10KY_R3_DISTINCT_M8_MESH_ONLY_GUARD',
                        'P10KY_R1_DISTINCT_M9_MESH_ONLY_GUARD')
    guard=guard.replace('one-shot P10KY M8 mesh marker','one-shot P10KY M9 mesh marker')
    guard=guard.replace('P10KY_R3_M9_UNVERIFIED_EVIDENCE.zip',
                        'P10KY_R1_M9_UNVERIFIED_EVIDENCE.zip')
    start=guard.index('PIN=');end=guard.index('\n\n',start)
    guard=guard[:start]+'PIN='+repr(newpins)+guard[end:]
    assert "PROFILE_MARK_NAME='P10KY_R1_M9_40949482ac74d80a_ONE_ATTEMPT.marker'" in guard
    assert "MARK=HERE/'P10KY_R1_ONE_M9_ATTEMPT_CONSUMED.marker'" in guard
    assert "EVIDENCE=HERE/'P10KY_R1_M9_UNVERIFIED_EVIDENCE.zip'" in guard
    assert "MESH=HERE/'P10KY_M9_R1_CANDIDATE_UNVERIFIED.msh'" in guard
    (NEW/'P10KY_guard.py').write_text(guard,encoding='utf8')

    for oldname,newname in [('01_P10KR_M8_R3_PREFLIGHT_AND_HEARTBEAT_TEST.cmd',
                              '01_P10KY_M9_R1_PREFLIGHT_AND_HEARTBEAT_TEST.cmd'),
                             ('02_P10KR_ONE_M8_R3_MESH_ONLY.cmd',
                              '02_P10KY_ONE_M9_R1_MESH_ONLY.cmd')]:
        s=(OLD/oldname).read_text(encoding='utf8').replace('P10KR','P10KY')
        s=s.replace('M8_R3','M9_R1').replace('M8 R3','M9 R1').replace('M8 ', 'M9 ')
        (NEW/newname).write_text(s,encoding='utf8')
    (NEW/'README_P10KY_RU.md').write_text(
        '# P10KY — отдельная M9 R1 попытка построения сетки (без FEM)\n\n'
        'Исходная принятая M8 R3 сетка SHA256 '+M8_SHA+'.\n'
        'Новый P10KX источник 4D абсолютной межсеточной разности SHA256 '+M9_CSV_SHA+'.\n'
        'CAD, все десять встроенных точек и полный M8 callback сохранены; добавлен только '
        'плавный M9 C² множитель (номинальное уменьшение объёма элемента не более 20%).\n\n'
        '1. В НОВОЙ папке выполнить `01_P10KY_M9_R1_PREFLIGHT_AND_HEARTBEAT_TEST.cmd` '
        '(65–80 секунд); дождаться `P10KY_WATCHDOG_SELFTEST_PASS` и exit0. '
        'Этот шаг не вызывает Gmsh generate, не запускает FEM и не расходует marker.\n'
        '2. После PASS выполнить РОВНО ОДИН РАЗ `02_P10KY_ONE_M9_R1_MESH_ONLY.cmd`. '
        'Оценка построения 20–240 секунд на i7-7700K, жёсткий предел 1200 секунд; '
        '4 потока, ≤8 GiB private bytes, 15-секундные независимые heartbeats, ≤250 MiB mesh. '
        'Маркер расходуется до запуска Gmsh. Если ошибка, НЕ ПОВТОРЯТЬ.\n'
        '3. Прислать ОДИН файл `P10KY_R1_M9_UNVERIFIED_EVIDENCE.zip`. '
        'M9 будет принята только после независимых D029 N/S [.75,.85] и D031 quality PASS. '
        'Никаких FEM в этом пакете.\n',encoding='utf8')
    assert len(newpins)==len(oldpins)+3
    ast.parse((NEW/'P10KY_guard.py').read_text(encoding='utf8'))
    ast.parse((NEW/'P10KY_one_M9_R1_worker.py').read_text(encoding='utf8'))
    for name,digest in newpins.items():
        assert sha(NEW/name)==digest
    with zipfile.ZipFile(ZIP,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as out:
        for path in sorted(NEW.iterdir()):out.write(path,path.name)
    with zipfile.ZipFile(ZIP) as z:assert z.testzip() is None
    print(json.dumps({'status':'P10KY_M9_R1_GUARDED_PREPARED_NOT_RUN',
                      'zip_sha256':sha(ZIP),'file_count':len(list(NEW.iterdir())),
                      'pins':len(newpins),'mesh_attempts':0,'FEM_attempts':0},indent=2))


if __name__=='__main__':main()
