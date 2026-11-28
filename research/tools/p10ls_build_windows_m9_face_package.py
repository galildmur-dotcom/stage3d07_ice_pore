#!/usr/bin/env python3
"""Build a separately guarded P10LS Windows M9 experiment without running FEM."""
from pathlib import Path
import ast
import hashlib
import json
import shutil
import zipfile

ROOT=Path(__file__).resolve().parents[2]
SRC=ROOT/'p10ls_source_only/P10LS_WORK'
OLD=ROOT/'p10lm_package/P10LM_WORK'
OUT=ROOT/'p10ls_package_r2/P10LS_WORK'
PKG=OUT.parent
REV='P10LS_M9_EDV_P1_P2_FACE_JUMP_PHYSICAL_DIAGNOSTIC_V1'

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    if OUT.exists():raise RuntimeError('P10LS package already exists: refusing overwrite')
    pins=json.loads((SRC/'P10FN_SOURCE_SHA256.json').read_text())
    assert pins['revision']==REV and len(pins['files'])==101
    for name,h in pins['files'].items():
        if sha(SRC/name)!=h:raise RuntimeError('source pin changed: '+name)
    shutil.copytree(SRC,OUT,ignore=shutil.ignore_patterns('__pycache__','build','*.exe'))
    for name in ('P10LM_M9_TWO_TERM.py','P10LM_heartbeat.py','P10LM_split_audit.py'):
        (OUT/name).unlink()
    runner=(OLD/'P10LM_M9_TWO_TERM.py').read_text()
    runner=runner.replace('P10LM','P10LS')
    runner=runner.replace('P10LS_M9_TWO_TERM_EXPLICIT_INSTRUMENTED_P10LG_V1',REV)
    assert f"SOURCE_REVISION = '{REV}'" in runner
    runner=runner.replace('20e38ffc44f4499d5114f9d0e714246f93f28d5ca1d14adb1c94bb1552dc940f',sha(OUT/'P10FN_SOURCE_SHA256.json'))
    runner=runner.replace('0a470e43668a751dc0514f94e8e33ad2b8615c9d56c633579dd7112fafcec2b3',sha(OUT/'stage3d10dd_4d_partition.hpp'))
    runner=runner.replace('from P10LS_split_audit import audit_split, NAME as SPLIT_CSV',
        'from P10LS_split_audit import audit_split, NAME as SPLIT_CSV\n'
        'from P10LS_face_jump_independent_audit import audit as audit_face, NAME as FACE_CSV')
    anchor="        history=result/'forward_history.bin'"
    assert runner.count(anchor)==1
    runner=runner.replace(anchor,
        "        manifest['face_jump']=phase_with_heartbeat('P10LS_FACE_JUMP_QA',\n"
        "            lambda: audit_face(result,'M9',STEPS,DT))\n"+anchor)
    anchor='                        (result/SPLIT_CSV,SPLIT_CSV)]'
    assert runner.count(anchor)==1
    runner=runner.replace(anchor,'                        (result/SPLIT_CSV,SPLIT_CSV),\n'
        '                        (result/FACE_CSV,FACE_CSV)]')
    runner=runner.replace("'P10LS_M9_FIRST_FULL4D_EVIDENCE.zip'", "'P10LS_M9_FACE_JUMP_EVIDENCE.zip'")
    runner=runner.replace("'P10LS_M9_REAL_FULL4D_PASS'", "'P10LS_M9_FACE_JUMP_PASS'")
    runner=runner.replace("'P10LS_FIRST_REAL_M9_FULL4D_V1'", "'P10LS_M9_EDV_FACE_JUMP_FIRST_RUN_V1'")
    (OUT/'P10LS_M9_FACE_JUMPS.py').write_text(runner)
    heartbeat=(OLD/'P10LM_heartbeat.py').read_text().replace('P10LM','P10LS')
    (OUT/'P10LS_heartbeat.py').write_text(heartbeat)
    shutil.copy2(OLD/'P10LM_split_audit.py',OUT/'P10LS_split_audit.py')
    shutil.copy2(ROOT/'research/tools/p10ls_face_jump_independent_audit.py',OUT/'P10LS_face_jump_independent_audit.py')
    cmd=[]
    for p in sorted(OLD.parent.glob('*.cmd')):
        s=p.read_text().replace('P10LM','P10LS').replace('P10LS_M9_TWO_TERM.py','P10LS_M9_FACE_JUMPS.py')
        dst=PKG/p.name.replace('P10LM','P10LS')
        dst.write_text(s)
        cmd.append(dst.name)
    for name in ('P10LS_M9_FACE_JUMPS.py','P10LS_heartbeat.py',
                 'P10LS_split_audit.py','P10LS_face_jump_independent_audit.py'):
        ast.parse((OUT/name).read_text(),filename=name)
    assert len(cmd)==2,cmd
    for name in cmd:assert 'P10LS_M9_FACE_JUMPS.py' in (PKG/name).read_text(),name
    readme=(OLD.parent/'README_P10LM_RU.md').read_text().replace('P10LM','P10LS')
    readme=readme.replace('P10LS_M9_TWO_TERM.py','P10LS_M9_FACE_JUMPS.py')
    readme+='\nP10LS: дополнительно P1/P2 восстановленные скачки напряжений, тяги и геометрической производной на внутренних гранях, 36×2×1200 строк. Нет данных в bin0 — нет граней, а не нулевой скачок. Отдельный маркер P10LS.\n'
    (PKG/'README_P10LS_RU.md').write_text(readme)
    archive=ROOT/'p10ls_package_r2/P10LS_M9_FACE_JUMP_WINDOWS_PREPARED_R2.zip'
    with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for file in sorted(PKG.rglob('*')):
            if file.is_file() and file!=archive:z.write(file,arcname=str(file.relative_to(PKG)))
    with zipfile.ZipFile(archive) as z:assert z.testzip() is None
    report={'protocol':'P10LS_WINDOWS_PREPARED','status':'SOURCE_QA_PASS_NO_FEM',
            'revision':REV,'archive_sha256':sha(archive),'bytes':archive.stat().st_size,
            'source_manifest_sha256':sha(OUT/'P10FN_SOURCE_SHA256.json'),
            'source_count':101,'entrypoints':cmd,'face_rows_expected':36*2*1200,
            'FEM_attempts':0,'mesh_generation_attempts':0,'marker_consumed':False}
    (ROOT/'research/P10LS_WINDOWS_PREPARATION_QA.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
