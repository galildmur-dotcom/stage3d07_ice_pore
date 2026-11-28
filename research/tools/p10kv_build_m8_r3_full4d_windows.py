#!/usr/bin/env python3
"""Prepare a distinct P10KV M8 R3 guarded FEM package. Never run FEM here."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import shutil
import zipfile

ROOT=Path(__file__).resolve().parents[2]
OLD=ROOT/'p10kv_inputs/p10kj_source'
NEW=ROOT/'p10kv_package'
ZIP=ROOT/'P10KV_M8_R3_FULL4D_WINDOWS_ONE_SHOT_20261125.zip'
MESH=ROOT/'p10ks_inputs/P10KR_M8_R3_CANDIDATE_UNVERIFIED.msh'
PASSPORT=ROOT/'research/evidence/P10KU_M8_R3_GEOMETRY_ACCEPTANCE_PASSPORT_20261125.json'
M8_SHA='40949482ac74d80ae7ac44c88af527a705650d34c1ffcd0de7cd01dc2bd2fa8d'

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def change_once(s,a,b):
    if s.count(a)!=1:raise RuntimeError('source token mismatch '+repr(a))
    return s.replace(a,b)

def main():
    if NEW.exists() or ZIP.exists():raise RuntimeError('existing P10KV output: refuse overwrite')
    assert sha(MESH)==M8_SHA
    passport=json.loads(PASSPORT.read_text())
    assert passport['status']=='GEOMETRY_GO_ONLY_NO_FEM' and passport['mesh_sha256']==M8_SHA
    assert passport['D031_geometry_quality_GO'] and passport['D029_adaptation_target_GO']
    shutil.copytree(OLD/'P10KJ_WORK',NEW/'P10KV_WORK')
    shutil.copy2(MESH,NEW/'P10KV_WORK/M8.msh')
    shutil.copy2(PASSPORT,NEW/'P10KV_WORK/P10KU_M8_R3_GEOMETRY_ACCEPTANCE_PASSPORT_20261125.json')
    oldrunner=NEW/'P10KV_WORK/P10KJ_M7_FIRST_FULL4D.py'
    txt=oldrunner.read_text(encoding='utf8')
    txt=txt.replace('P10KJ','P10KV').replace('M7','M8')
    txt=change_once(txt,"P10KI_M8_R2_GEOMETRY_ACCEPTANCE_PASSPORT.json",
                    "P10KU_M8_R3_GEOMETRY_ACCEPTANCE_PASSPORT_20261125.json")
    txt=change_once(txt,"'87c08dbdae1e84b5d55cd5b72058743d34974f7c06252ded5309151590e257f7'",
                    "'"+sha(PASSPORT)+"'")
    txt=change_once(txt,"M8_SHA = '875c9177de24612d0078f7a792b4b7641a2e604973cb1353500710c87693bb3d'",
                    "M8_SHA = '"+M8_SHA+"'")
    for old,new in [('M8_TET10 = 12001','M8_TET10 = 12546'),
                    ('M8_NODES = 17558','M8_NODES = 18331'),
                    ('M8_PORE_TRI6 = 592','M8_PORE_TRI6 = 648'),
                    ('P10KI_D031_D029_REAL_M8_R2_GEOMETRY_GO_20261125',
                     'P10KU_D031_D029_REAL_M8_R3_GEOMETRY_GO_20261125')]:
        txt=change_once(txt,old,new)
    txt=txt.replace('M8_FIRST_FULL4D','M8_FIRST_FULL4D')
    newrunner=NEW/'P10KV_WORK/P10KV_M8_FIRST_FULL4D.py'
    newrunner.write_text(txt,encoding='utf8')
    oldrunner.unlink()
    heart=NEW/'P10KV_WORK/P10KJ_heartbeat.py'
    (NEW/'P10KV_WORK/P10KV_heartbeat.py').write_text(
        heart.read_text(encoding='utf8').replace('P10KJ','P10KV').replace('M7','M8'),encoding='utf8')
    heart.unlink()
    for src,dst in [('01_P10KJ_M7_PREFLIGHT_AND_WINDOWS_WATCHDOG_TEST.cmd',
                     '01_P10KV_M8_PREFLIGHT_AND_WINDOWS_WATCHDOG_TEST.cmd'),
                    ('02_P10KJ_ONE_M7_FIRST_FULL4D_FEM.cmd',
                     '02_P10KV_ONE_M8_FIRST_FULL4D_FEM.cmd')]:
        s=(OLD/src).read_text(encoding='utf8').replace('P10KJ','P10KV').replace('M7','M8')
        (NEW/dst).write_text(s,encoding='utf8')
    (NEW/'README_P10KV_RU.md').write_text(
        '# P10KV — отдельный M8 R3 FEM, 36×25с signed 4D\n\n'
        'Полностью сохранён solver SHA101 успешного M7 P10KJ, изменена только принятая сетка\n'
        'M8 R3 и отдельный one-shot marker FEM. Прямая и аналитическая сопряжённая на одной mesh,\n'
        'R/EDV_VAR/ξ0/B6 5мм, 4 threads, dt=25с, 36 шагов, полный signed4D.\n'
        'В новой папке сначала `01_P10KV_M8_PREFLIGHT_AND_WINDOWS_WATCHDOG_TEST.cmd`\n'
        '(около65–80с, без FEM и marker); обязательно PASS и exit0.\n'
        'Затем **ровно один раз** `02_P10KV_ONE_M8_FIRST_FULL4D_FEM.cmd`,\n'
        'оценка 20–35мин на i7-7700K, жёстко ≤40мин/8GiB/private и ≤2GiB output,\n'
        'независимый heartbeat каждые15с; не повторять после marker даже при STOP.\n'
        'Верните только `P10KV_M8_FIRST_FULL4D_EVIDENCE.zip` из LOCAL_RUNS/P10KV_M8_R_DT25_*;\n'
        'никаких огромных mesh/VTU/checkpoint и прежних результатов M7 повторно не присылать.\n',encoding='utf8')
    with zipfile.ZipFile(ZIP,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for p in sorted(NEW.rglob('*')):
            if p.is_file():z.write(p,p.relative_to(NEW).as_posix())
    with zipfile.ZipFile(ZIP) as z:assert z.testzip() is None
    print(json.dumps({'status':'P10KV_M8_R3_FULL4D_PREPARED_NOT_RUN','archive_sha256':sha(ZIP),
                      'source_files':sum(p.is_file() for p in NEW.rglob('*')),
                      'mesh_sha256':M8_SHA,'FEM_attempts':0},indent=2))

if __name__=='__main__':main()
