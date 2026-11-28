#!/usr/bin/env python3
"""Build distinct P10KQ Windows M8 R2 mesh-only package, without Gmsh/FEM."""
from __future__ import annotations
import ast
import hashlib
import json
from pathlib import Path
import shutil
import zipfile

ROOT=Path(__file__).resolve().parents[2]
OLD=ROOT/'p10kp_inputs/p10kn_source'
NEW=ROOT/'p10kq_package'
ARCHIVE=ROOT/'P10KQ_R2_M8_GUARDED_MESH_ONLY_WINDOWS_20261125.zip'
PLATEAU=ROOT/'research/tools/p10kp_m8_r2_polar_plateau.py'
QA=ROOT/'p10kp_result/P10KP_REAL_FIELD_QA.json'

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def replace_once(s,old,new):
    if s.count(old)!=1:raise RuntimeError(f'expected exactly one source token: {old!r}, got {s.count(old)}')
    return s.replace(old,new)

def main():
    if NEW.exists() or ARCHIVE.exists():raise RuntimeError('previous delivery exists: refuse overwrite')
    oldguard=(OLD/'P10KN_guard.py').read_text(encoding='utf8')
    oldpins=ast.literal_eval(oldguard.split('PIN=',1)[1].split('\n\n',1)[0])
    for name,digest in oldpins.items():
        if sha(OLD/name)!=digest:raise RuntimeError('P10KN source drift: '+name)
    qa=json.loads(QA.read_text())
    if qa['status']!='PASS_SOURCE_ONLY_REAL_FIELD_NO_MESH_NO_FEM':
        raise RuntimeError('P10KP actual field not validated')
    if sha(OLD/'M7.msh')!='875c9177de24612d0078f7a792b4b7641a2e604973cb1353500710c87693bb3d':
        raise RuntimeError('accepted M7 R2 input SHA drift')
    NEW.mkdir()
    # Immutable upstream geometry, meshes and priority data; no R1 guard, worker,
    # markers or outputs are copied.
    for name in oldpins:
        if name not in ('P10KN_one_M8_R1_worker.py','p10kn_progress.py'):
            shutil.copy2(OLD/name,NEW/name)
    shutil.copy2(PLATEAU,NEW/'p10kp_m8_r2_polar_plateau.py')
    shutil.copy2(QA,NEW/'P10KP_REAL_FIELD_QA.json')
    progress=(OLD/'p10kn_progress.py').read_text(encoding='utf8').replace('P10KN','P10KQ')
    (NEW/'p10kq_progress.py').write_text(progress,encoding='utf8')
    worker=(OLD/'P10KN_one_M8_R1_worker.py').read_text(encoding='utf8')
    worker=replace_once(worker,'            kappa8=m8.kappa(position)',
                        '            kappa8=kappa_r2(m8.kappa(position),dmm,mu)')
    # Add the new field module once, keeping every old size factor unchanged.
    anchor='OUT=HERE/'
    pos=worker.index(anchor)
    worker=worker[:pos]+'from p10kp_m8_r2_polar_plateau import kappa_r2\n'+worker[pos:]
    worker=worker.replace('P10KN','P10KQ').replace('M8_R1','M8_R2').replace('M8 R1','M8 R2')
    worker=replace_once(worker,"'M8_additional_nominal_volume_reduction_max':.20,",
                        "'M8_additional_nominal_volume_reduction_max':.20,\n"
                        "                'P10KP_R2_polar_plateau_C2':True,\n"
                        "                'P10KP_R2_real_field_QA_sha256':hashlib.sha256((HERE/'P10KP_REAL_FIELD_QA.json').read_bytes()).hexdigest(),")
    (NEW/'P10KQ_one_M8_R2_worker.py').write_text(worker,encoding='utf8')
    pin={name:sha(NEW/name) for name in oldpins if name not in ('P10KN_one_M8_R1_worker.py','p10kn_progress.py')}
    for name in ('p10kp_m8_r2_polar_plateau.py','P10KP_REAL_FIELD_QA.json',
                 'p10kq_progress.py','P10KQ_one_M8_R2_worker.py'):
        pin[name]=sha(NEW/name)
    guard=oldguard.replace('P10KN','P10KQ').replace('M8_R1','M8_R2').replace('R1_M8','R2_M8').replace('M8 R1','M8 R2')
    guard=guard.replace('p10kn_progress','p10kq_progress')
    guard=guard.replace("'P10KQ_R1_ONE_M8_ATTEMPT_CONSUMED.marker'", "'P10KQ_R2_ONE_M8_ATTEMPT_CONSUMED.marker'")
    guard=guard.replace('P10KQ_R1_M8_875c9177de24612d_ONE_ATTEMPT.marker',
                        'P10KQ_R2_M8_875c9177de24612d_ONE_ATTEMPT.marker')
    guard=guard.replace('P10KQ_R1_M8_UNVERIFIED_EVIDENCE.zip','P10KQ_R2_M8_UNVERIFIED_EVIDENCE.zip')
    guard=guard.replace('P10KQ_R1_PREFLIGHT_PASS','P10KQ_R2_PREFLIGHT_PASS')
    guard=guard.replace('P10KQ_R1_DISTINCT_M8_MESH_ONLY_GUARD','P10KQ_R2_DISTINCT_M8_MESH_ONLY_GUARD')
    pin_start=guard.index('PIN=')
    pin_end=guard.index('\n\n',pin_start)
    guard=guard[:pin_start]+'PIN='+repr(pin)+guard[pin_end:]
    (NEW/'P10KQ_guard.py').write_text(guard,encoding='utf8')
    for src,dest in [('01_P10KN_M8_PREFLIGHT_AND_HEARTBEAT_TEST.cmd',
                      '01_P10KQ_M8_R2_PREFLIGHT_AND_HEARTBEAT_TEST.cmd'),
                     ('02_P10KN_ONE_M8_R1_MESH_ONLY.cmd',
                      '02_P10KQ_ONE_M8_R2_MESH_ONLY.cmd')]:
        cmd=(OLD/src).read_text(encoding='utf8').replace('P10KN','P10KQ').replace('M8 R1','M8 R2')
        cmd=cmd.replace('M8_R1','M8_R2')
        (NEW/dest).write_text(cmd,encoding='utf8')
    (NEW/'README_P10KQ_RU.md').write_text(
        '# P10KQ — M8 R2, отдельная mesh-only Windows попытка\n\n'
        'Новая попытка **не повторяет** остановленную M8 R1. FEM=0.\n'
        'Исходная M7 R2 CAD, 10 точек, вся накопленная M2…M7 размерная функция сохранены.\n'
        'Изменено только дополнительное M8 поле: C²-плато P10KP κ=1 при d≤0.5мм, |μ|≥0.8,\n'
        'плавный переход до d=1мм и |μ|=0.6. Номинальный масштаб h=(1−0.20κ)^(1/3);\n'
        'фактический Veff ещё НЕ известен.\n\n'
        '1. Распакуйте в НОВУЮ папку (старые one-shot папки не трогать).\n'
        '2. Запустите `01_P10KQ_M8_R2_PREFLIGHT_AND_HEARTBEAT_TEST.cmd`: ~65–80 секунд,\n'
        '   SHA preflight + реальная native silent child heartbeat проверка, без Gmsh/marker/FEM.\n'
        '3. ТОЛЬКО после `P10KQ_WATCHDOG_SELFTEST_PASS` запустите **ровно один раз**\n'
        '   `02_P10KQ_ONE_M8_R2_MESH_ONLY.cmd`: Gmsh 4.15.2, 4 потока, ожидание 15–180с,\n'
        '   верхняя граница 900с, RAM 8GiB, лог32MiB, mesh250MiB, heartbeat каждые15с.\n'
        '4. Верните только `P10KQ_R2_M8_UNVERIFIED_EVIDENCE.zip`.\n\n'
        'Сетка не считается принятой до независимых D031 curved+CAD/quality и D029 actual polar Veff\n'
        'N/S∈[0.75,0.85] по сравнению с принятой M7 R2. FEM не запускать.\n',encoding='utf8')
    with zipfile.ZipFile(ARCHIVE,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for path in sorted(NEW.iterdir()):z.write(path,path.name)
    with zipfile.ZipFile(ARCHIVE) as z:
        assert z.testzip() is None
    print(json.dumps({'status':'P10KQ_M8_R2_WINDOWS_MESH_ONLY_PREPARED_NOT_RUN',
                      'sha256':sha(ARCHIVE),'files':len(list(NEW.iterdir())),
                      'M8_R2_attempts':0,'FEM_attempts':0},indent=2))

if __name__=='__main__':main()
