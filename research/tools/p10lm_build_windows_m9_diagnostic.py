#!/usr/bin/env python3
"""Build a distinct M9 guarded physical package; NEVER execute the physics.

Uses accepted P10LC launcher + P10LG instrumented source. Refuses overwrite.
No Gmsh, no FEM, no writes to Windows run roots or consumed markers.
"""
from __future__ import annotations

import hashlib
import ast
import json
from pathlib import Path
import shutil
import zipfile

ROOT=Path(__file__).resolve().parents[2]
OLD=ROOT/'p10lc_package/P10LC_WORK'
INSTRUMENTED=ROOT/'p10lg_source_only/P10LG_WORK/stage3d10dd_4d_partition.hpp'
PACKAGE=ROOT/'p10lm_package'
WORK=PACKAGE/'P10LM_WORK'
ARCHIVE=ROOT/'P10LM_M9_TWO_TERM_EXPLICIT_WINDOWS_ONE_SHOT_20261125.zip'
NEW_REV='P10LM_M9_TWO_TERM_EXPLICIT_INSTRUMENTED_P10LG_V1'
OLD_REV='P10GY_R2_FIXED_4D_WRITER_12_36_SELFTEST_GUARDED_ONE_SHOTS'
M9_SHA='a40aca54636a752afe4d7babe9d03e741b2e988b9ad3dbb6f356728bff035a58'
INSTRUMENTED_SHA='0a470e43668a751dc0514f94e8e33ad2b8615c9d56c633579dd7112fafcec2b3'


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def replace_exact(content,before,after):
    n=content.count(before)
    if n!=1:raise RuntimeError(f'expected exactly one replacement, got {n}: {before[:80]}')
    return content.replace(before,after)


def main():
    if PACKAGE.exists() or ARCHIVE.exists():
        raise RuntimeError('P10LM already exists, refuse overwrite')
    if digest(INSTRUMENTED)!=INSTRUMENTED_SHA:
        raise RuntimeError('P10LG instrumented source SHA drift')
    if digest(OLD/'M9.msh')!=M9_SHA:
        raise RuntimeError('accepted M9 source mesh SHA drift')
    old_pin=json.loads((OLD/'P10FN_SOURCE_SHA256.json').read_text())
    if old_pin['revision']!=OLD_REV or len(old_pin['files'])!=101:
        raise RuntimeError('original 101-file source inventory drift')
    for path,sha in old_pin['files'].items():
        if digest(OLD/path)!=sha:
            raise RuntimeError('original pinned source differs: '+path)
    shutil.copytree(OLD,WORK,ignore=shutil.ignore_patterns('build','__pycache__','*.exe'))
    shutil.copy2(INSTRUMENTED,WORK/'stage3d10dd_4d_partition.hpp')
    pin=old_pin.copy();pin['files']=dict(old_pin['files']);pin['revision']=NEW_REV
    pin['origin']='P10LC pinned 101-file solver; ONLY 4D header changed for P10LG signed two-term source diagnostic'
    pin['files']['stage3d10dd_4d_partition.hpp']=INSTRUMENTED_SHA
    assert [p for p in pin['files'] if pin['files'][p]!=old_pin['files'][p]]==['stage3d10dd_4d_partition.hpp']
    (WORK/'P10FN_SOURCE_SHA256.json').write_text(json.dumps(pin,indent=2)+'\n',encoding='utf8')
    new_manifest_sha=digest(WORK/'P10FN_SOURCE_SHA256.json')

    # Retain original Job Object / 15-s heartbeats, but use distinct P10LM
    # state files, logs, output folders, and one-shot marker namespace.
    runner=(OLD/'P10LC_M9_FIRST_FULL4D.py').read_text(encoding='utf8').replace('P10LC','P10LM')
    runner=replace_exact(runner,OLD_REV,NEW_REV)
    runner=replace_exact(runner,'dc3f1b8d3fef2c7c0982b319225c3046c10567a7d4630649df34ae1f222214fc',new_manifest_sha)
    runner=replace_exact(runner,"from P10LM_heartbeat import run_with_heartbeat, compile_with_heartbeat, phase_with_heartbeat",
        "from P10LM_heartbeat import run_with_heartbeat, compile_with_heartbeat, phase_with_heartbeat\n"
        "from P10LM_split_audit import audit_split, NAME as SPLIT_CSV")
    runner=replace_exact(runner,
        "    need(DT*STEPS == 900, 'physical time horizon drift')",
        "    need(sha256(HERE/'stage3d10dd_4d_partition.hpp') == '"+INSTRUMENTED_SHA+"',\n"
        "         'instrumented C++ P10LG header SHA mismatch')\n"
        "    need(DT*STEPS == 900, 'physical time horizon drift')")
    runner=replace_exact(runner,
        "        history=result/'forward_history.bin'",
        "        manifest['two_term_explicit']=phase_with_heartbeat('P10LM_SIGNED_SPLIT_QA',\n"
        "            lambda: audit_split(result,'M9',STEPS,DT))\n"
        "        history=result/'forward_history.bin'")
    runner=replace_exact(runner,
        "             (SELFTEST,SELFTEST.name),*[(result/name,name) for name in CSV]]))",
        "             (SELFTEST,SELFTEST.name),\n"
        "             *[(result/name,name) for name in CSV],\n"
        "             (result/SPLIT_CSV,SPLIT_CSV)]))")
    runner=replace_exact(runner,
        "        manifest['history_sha256']=sha256(history)",
        "        manifest['history_sha256']=sha256(history)\n"
        "        manifest['P10LG_header_sha256']='"+INSTRUMENTED_SHA+"'")
    runner=replace_exact(runner,
        "    verified_test=require_selftest()\n"
        "    need(not marker.exists(), 'M9 physical one-shot marker already consumed; NEVER REPEAT')",
        "    verified_test=require_selftest()\n"
        "    profile_root=os.environ.get('LOCALAPPDATA')\n"
        "    need(bool(profile_root), 'LOCALAPPDATA unavailable; cannot secure one-shot')\n"
        "    profile_marker=Path(profile_root)/'Stage3D07'/'P10LM_M9_ONE_SHOT_MARKERS'/marker.name\n"
        "    need(not profile_marker.exists(), 'P10LM profile one-shot already consumed; STOP')\n"
        "    need(not marker.exists(), 'M9 physical one-shot marker already consumed; NEVER REPEAT')")
    runner=replace_exact(runner,
        "    write_new(marker,manifest)\n"
        "    local_marker = folder/'P10FN_ONE_SHOT_CONSUMED.json'",
        "    write_new(marker,manifest)\n"
        "    write_new(profile_marker,manifest)\n"
        "    local_marker = folder/'P10FN_ONE_SHOT_CONSUMED.json'")
    runner=replace_exact(runner,
        "        phase_with_heartbeat('EVIDENCE_PACKAGING',lambda: zip_evidence(evidence,\n"
        "            [(meta,meta.name),(log,log.name),(progress,progress.name),\n"
        "             (SELFTEST,SELFTEST.name),\n"
        "             *[(result/name,name) for name in CSV],\n"
        "             (result/SPLIT_CSV,SPLIT_CSV)]))",
        "        evidence_files=[(meta,meta.name),(log,log.name),(progress,progress.name),\n"
        "                        (SELFTEST,SELFTEST.name),\n"
        "                        *[(result/name,name) for name in CSV],\n"
        "                        (result/SPLIT_CSV,SPLIT_CSV)]\n"
        "        phase_with_heartbeat('EVIDENCE_PACKAGING',lambda: zip_evidence(evidence,\n"
        "            [(path,name) for path,name in evidence_files if path.is_file()]))")
    (WORK/'P10LM_M9_TWO_TERM.py').write_text(runner,encoding='utf8')
    heartbeat=(OLD/'P10LC_heartbeat.py').read_text(encoding='utf8').replace('P10LC','P10LM')
    (WORK/'P10LM_heartbeat.py').write_text(heartbeat,encoding='utf8')
    shutil.copy2(ROOT/'research/tools/p10lm_split_audit.py',WORK/'P10LM_split_audit.py')
    ast.parse(runner)
    ast.parse(heartbeat)
    ast.parse((WORK/'P10LM_split_audit.py').read_text(encoding='utf8'))
    # The old first-physical one-shot launcher must not be shipped as another
    # callable button in the new package (source inventory excludes it).
    (WORK/'P10LC_M9_FIRST_FULL4D.py').unlink()
    (WORK/'P10LC_heartbeat.py').unlink()

    for number,src in [('01','01_P10LC_M9_PREFLIGHT_AND_WINDOWS_WATCHDOG_TEST.cmd'),
                       ('02','02_P10LC_ONE_M9_FIRST_FULL4D_FEM.cmd')]:
        text=(ROOT/'p10lc_package'/src).read_text(encoding='utf8').replace('P10LC','P10LM')
        text=text.replace('P10LM_M9_FIRST_FULL4D.py','P10LM_M9_TWO_TERM.py')
        name={'01':'01_P10LM_PREFLIGHT_NO_FEM.cmd',
              '02':'02_P10LM_ONE_M9_EXTENDED_EXPLICIT_FEM.cmd'}[number]
        (PACKAGE/name).write_text(text,encoding='utf8')
    readme=(
        '# P10LM — ONE M9 extended signed explicit diagnostic\n\n'
        '1. Extract ZIP into a NEW directory, retaining all internal paths.\n'
        '2. Run 01_P10LM_PREFLIGHT_NO_FEM.cmd (65–85 s). Expect '
        'P10LM_WINDOWS_NATIVE_HEARTBEAT_SELFTEST_PASS, no FEM and no marker.\n'
        '3. Only after PASS run 02_P10LM_ONE_M9_EXTENDED_EXPLICIT_FEM.cmd '
        'once. No user input or PowerShell required.\n'
        '4. After success/STOP do NOT retry the same 02. Return only the '
        'new P10LM_M9_FIRST_FULL4D_EVIDENCE.zip (renamed by runner) without '
        'forward_history.bin. If STOP send manifest/log.\n\n'
        'Physical regime: exact accepted M9 mesh SHA '+M9_SHA+'; '
        'R, EDV_VAR, xi=0, B6=5 mm, 36x25 s, 4 threads.\n'
        'Hard wall limit 2400 s; 8 GiB monitored process memory; 2 GiB '
        'output budget; 15 s independent heartbeat.\n'
        'The full4D original P10DD remains; new CSV is '
        'P10LG_EXPLICIT_GEOMETRY_STRESS_4D.csv. '
        'One-shot marker: P10LM_M9_ONE_SHOT_MARKERS (separate from P10LC).\n'
        'Status: PREPARED, NOT RUN. No old P10LC/M9 marker is modified.\n')
    (PACKAGE/'README_P10LM_RU.md').write_text(readme,encoding='utf8')
    # No compiled executables or previously consumed markers in the package.
    if list(PACKAGE.rglob('*.exe')) or list(PACKAGE.rglob('*CONSUMED*')):
        raise RuntimeError('unsafe executable/consumed marker included')
    with zipfile.ZipFile(ARCHIVE,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for path in sorted(PACKAGE.rglob('*')):
            if path.is_file():z.write(path,path.relative_to(ROOT))
    with zipfile.ZipFile(ARCHIVE) as z:
        bad=z.testzip()
        if bad:raise RuntimeError('ZIP CRC mismatch '+bad)
    result={'protocol':'P10LM_NEW_M9_DIAGNOSTIC_PHYSICAL_ONE_SHOT_PREPARED',
        'status':'SOURCE_ONLY_PREPARED_NOT_EXECUTED',
        'package':ARCHIVE.name,'package_sha256':digest(ARCHIVE),
        'source_manifest_sha256':new_manifest_sha,
        'source_count':len(pin['files']),'modified_pinned_source':['stage3d10dd_4d_partition.hpp'],
        'new_header_sha256':INSTRUMENTED_SHA,'mesh_sha256':M9_SHA,
        'new_one_shot_namespace':'P10LM_M9_ONE_SHOT_MARKERS',
        'old_one_shots_unchanged':['P10LC_M9_ONE_SHOT_MARKERS','P10KV_M8_ONE_SHOT_MARKERS'],
        'FEM_attempts':0,'mesh_generation_attempts':0,
        'native_windows_preflight':'PENDING','native_physical_run':'PENDING',
        'output':'P10LG_EXPLICIT_GEOMETRY_STRESS_4D.csv',
        'resource_limit':{'wall_s':2400,'job_private_gib':8,'output_gib':2,'threads':4}}
    (ROOT/'research/P10LM_PREPARED_PACKAGE_QA.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
