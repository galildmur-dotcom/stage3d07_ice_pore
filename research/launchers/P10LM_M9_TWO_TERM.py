#!/usr/bin/env python3
"""P10LM: guarded first accepted M9 R/EDV_VAR 36x25 direct+adjoint."""
from __future__ import annotations

import json
import os
from pathlib import Path
import sys
import subprocess
import tempfile
from datetime import datetime,timezone

from P10FN_common import (HERE, RUNS, need, now, require_windows, sha256,
                          validate_source, write_new, zip_evidence)
from P10FN_mesh_qa import audit as mesh_audit
from P10FN_physics import compiler_environment, ensure_binary
from P10GY_temporal_series import independent_time_audit, CSV
from P10LM_heartbeat import run_with_heartbeat, compile_with_heartbeat, phase_with_heartbeat
from P10LM_split_audit import audit_split, NAME as SPLIT_CSV

M9_SHA = 'a40aca54636a752afe4d7babe9d03e741b2e988b9ad3dbb6f356728bff035a58'
M9_TET10 = 13166
M9_NODES = 19236
M9_PORE_TRI6 = 734
SOURCE_REVISION = 'P10LM_M9_TWO_TERM_EXPLICIT_INSTRUMENTED_P10LG_V1'
SOURCE_MANIFEST_SHA = '20e38ffc44f4499d5114f9d0e714246f93f28d5ca1d14adb1c94bb1552dc940f'
TEMPORAL_AUDIT_SHA = '547ebec5955c882507e707fe2604f43713ec15a4bf4323b659619c3e1c6ff100'
DT = 25
STEPS = 36
REGIME = {'mode':'R', 'law':'EDV_VAR', 'xi':0, 'B6_mm':5,
          't_final_s':900, 'dt_s':DT, 'steps':STEPS, 'threads':4}
SELFTEST=HERE/'P10LM_WINDOWS_NATIVE_HEARTBEAT_SELFTEST.json'


def preflight():
    require_windows()
    need(sha256(HERE/'P10FN_SOURCE_SHA256.json') == SOURCE_MANIFEST_SHA,
         'P10GY R2 source manifest SHA mismatch')
    need(validate_source() == SOURCE_REVISION, 'exact 101-file solver revision mismatch')
    need(sha256(HERE/'P10GY_temporal_series.py') == TEMPORAL_AUDIT_SHA,
         'independent signed 4D temporal audit SHA mismatch')
    cpp=(HERE/'stage3d10fn_any_mesh_full4d.cpp').read_text(encoding='utf-8')
    need('grid!="36x25"' in cpp and 'P10FN_ONE_SHOT_MARKER' in cpp,
         '36x25 C++ source guard not present')
    need(sha256(HERE/'stage3d10dd_4d_partition.hpp') == '0a470e43668a751dc0514f94e8e33ad2b8615c9d56c633579dd7112fafcec2b3',
         'instrumented C++ P10LG header SHA mismatch')
    need(DT*STEPS == 900, 'physical time horizon drift')
    mesh = HERE/'M9.msh'
    need(sha256(HERE/'P10LB_M9_R1_GEOMETRY_ACCEPTANCE_PASSPORT_20261125.json')=='0aaf1fffb247717ef91f75472c79bc8e8fa7f4b4219b3ba8b4512373d93017b7',
         'P10KI accepted geometry passport SHA drift')
    need(mesh.is_file() and sha256(mesh)==M9_SHA,
         'P10JV accepted M9 exact mesh SHA mismatch')
    qa = mesh_audit(mesh)
    need(qa['tet10']==M9_TET10 and qa['nodes']==M9_NODES and
         qa['pore_tri6']==M9_PORE_TRI6 and qa['nonpositive_samples']==0 and
         qa['physical_surface_tags']==list(range(2,10)),
         'P10JV M9 curved 27QP / physical surface QA differs')
    print('P10LM_M9_PREFLIGHT_PASS_NO_FEM', 'source_count=101',
          'mesh_sha256='+M9_SHA, 'tet10='+str(M9_TET10),
          'dt_s='+str(DT), 'steps='+str(STEPS), flush=True)
    return mesh, qa


def native_watchdog_selftest():
    """Actual Windows Job+PSAPI process runner, silent 65s, before FEM marker."""
    require_windows()
    if SELFTEST.exists():
        old=require_selftest()
        print('P10LM_WINDOWS_NATIVE_HEARTBEAT_SELFTEST_PASS reused_previous_test beats='+
              str(old['observed_heartbeat_count']),flush=True)
        return old
    print('P10LM_WINDOWS_NATIVE_SILENT_TEST_START 65s child, no FEM, no marker',flush=True)
    with tempfile.TemporaryDirectory(prefix='p10jw_silent_native_') as tmp:
        root=Path(tmp)
        child=[sys.executable,'-c','import time;time.sleep(65)']
        result=run_with_heartbeat(child,cwd=HERE,log=root/'native_silent.log',
                                  wall_s=90,memory_gib=8,output_dir=root,
                                  output_gib=1,env=os.environ.copy())
        progress=root/'P10LM_PROGRESS_LOG.txt'
        need(progress.is_file(),'independent progress audit absent')
        lines=progress.read_text(encoding='utf-8').splitlines()
        ticks=[s for s in lines if s.startswith('P10LM_INDEPENDENT_FEM_HEARTBEAT')]
        need(result['native_exit_code']==0 and not result['stop_reason'],
             'real Windows Job silent child did not pass')
        need(len(ticks)>=4 and result['independent_progress_heartbeat_count']>=4,
             '15s watchdog did not produce >=4 ticks in silent 65s process')
        payload={'protocol':'P10LM_WINDOWS_JOB_NATIVE_SILENT_65S_PREMARKER_TEST',
                 'status':'PASS_NO_FEM_NO_MARKER', 'native_exit_code':0,
                 'native_silent_child_s':65,'observed_heartbeat_count':len(ticks),
                 'heartbeat_interval_s':15,'mesh_sha256':M9_SHA,
                 'heartbeat_source_sha256':sha256(HERE/'P10LM_heartbeat.py'),
                 'time_utc':datetime.now(timezone.utc).isoformat(),
                 'marker_consumed':False,'FEM_attempts':0,
                 'mesh_generation_attempts':0}
        SELFTEST.write_text(json.dumps(payload,indent=2)+'\n',encoding='utf-8')
        print('P10LM_WINDOWS_NATIVE_HEARTBEAT_SELFTEST_PASS beats='+str(len(ticks)),flush=True)
        return payload


def require_selftest():
    need(SELFTEST.is_file(), 'run 01 native Windows heartbeat selftest first; NO FEM')
    record=json.loads(SELFTEST.read_text(encoding='utf-8'))
    need(record['status']=='PASS_NO_FEM_NO_MARKER' and
         record['mesh_sha256']==M9_SHA and
         record['observed_heartbeat_count']>=4 and
         record['heartbeat_source_sha256']==sha256(HERE/'P10LM_heartbeat.py'),
         'native Windows heartbeat test unverified or source changed; NO FEM')
    return record


def main():
    need(len(sys.argv) in (1,2) and (len(sys.argv)==1 or sys.argv[1] in
         ('--run','--watchdog-selftest')),
         'only preflight, guarded watchdog selftest or explicit --run supported')
    print('P10LM_START stage=source_and_mesh_preflight', flush=True)
    mesh, qa = phase_with_heartbeat('PREFLIGHT',preflight)
    if len(sys.argv)==1 or sys.argv[1]=='--watchdog-selftest':
        report={'protocol':'P10LM_M9_FIRST_FULL4D_PREFLIGHT_V1',
                'status':'PASS_SOURCE_M9_NO_FEM', 'FEM_attempts':0,
                'compilation_attempts':0, 'mesh_generation_attempts':0,
                'one_shot_consumed':False, 'mesh_sha256':M9_SHA,
                'source_manifest_sha256':SOURCE_MANIFEST_SHA,
                'source_revision':SOURCE_REVISION, 'regime':REGIME,
                'mesh_qa':qa}
        (HERE/'P10LM_M9_PREFLIGHT_RESULT.json').write_text(
            json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
        print('P10LM_SEND_PREFLIGHT_RESULT', 'P10LM_M9_PREFLIGHT_RESULT.json',flush=True)
        if len(sys.argv)==2:
            native_watchdog_selftest()
        return 0

    # The --run branch must be triggered by the separately authorized CMD only.
    marker = RUNS/'P10LM_M9_ONE_SHOT_MARKERS'/(
        f'M9_R_DT{DT}_STEPS{STEPS}_{M9_SHA[:16]}.json')
    verified_test=require_selftest()
    profile_root=os.environ.get('LOCALAPPDATA')
    need(bool(profile_root), 'LOCALAPPDATA unavailable; cannot secure one-shot')
    profile_marker=Path(profile_root)/'Stage3D07'/'P10LM_M9_ONE_SHOT_MARKERS'/marker.name
    need(not profile_marker.exists(), 'P10LM profile one-shot already consumed; STOP')
    need(not marker.exists(), 'M9 physical one-shot marker already consumed; NEVER REPEAT')
    print('P10LM_BUILD_PHASE: first compile/selftest, no FEM yet', flush=True)
    toolchain, build = compile_with_heartbeat(ensure_binary)
    need(not marker.exists(), 'M9 marker appeared during build; STOP')
    exe = HERE/'build'/'stage3d10fn_any_mesh_full4d.exe'
    folder = RUNS/f'P10LM_M9_R_DT{DT}_{now()}'
    folder.mkdir(parents=True,exist_ok=False)
    result = folder/f'P10FN_M9_DT{DT}_R'
    manifest={'protocol':'P10LM_FIRST_REAL_M9_FULL4D_V1',
              'status':'CONSUMED', 'mesh':'M9', 'mesh_sha256':M9_SHA,
              'mesh_qa':qa, 'source_revision':SOURCE_REVISION,
              'source_manifest_sha256':SOURCE_MANIFEST_SHA,
              'regime':REGIME, 'FEM_attempts':1,
              'fresh_forward':True, 'same_mesh_analytic_adjoint':True,
              'mesh_source':'P10LB_D031_D029_REAL_M9_R1_GEOMETRY_GO_20261125',
              'windows_native_heartbeat_preflight':verified_test,
              'exe_sha256':build['exe_sha256'], 'started_utc':now(),
              'one_shot_marker':str(marker)}
    # Irreversible consume BEFORE starting the native FEM process.
    write_new(marker,manifest)
    write_new(profile_marker,manifest)
    local_marker = folder/'P10FN_ONE_SHOT_CONSUMED.json'
    write_new(local_marker,manifest)
    command=[str(exe),'--p10fn-authorized','--mesh',str(mesh),
             '--out',str(result),'--mode','R','--steps',str(STEPS),
             '--dt',str(DT),'--cutoff-mm','5','--threads','4']
    env=compiler_environment(toolchain)
    env['P10FN_ONE_SHOT_MARKER']=str(local_marker)
    log=folder/'P10LM_NATIVE_LOG.txt'
    progress=folder/'P10LM_PROGRESS_LOG.txt'
    try:
        manifest.update(run_with_heartbeat(command,cwd=HERE,log=log,wall_s=2400,
                                           memory_gib=8,output_dir=folder,
                                           output_gib=2,env=env))
        need(progress.is_file(), 'missing persisted independent progress log')
        ticks=[s for s in progress.read_text(encoding='utf-8').splitlines()
               if s.startswith('P10LM_INDEPENDENT_FEM_HEARTBEAT')]
        need(len(ticks)>=1, 'independent progress never appeared')
        manifest['independent_progress_log_sha256']=sha256(progress)
        manifest['independent_progress_lines']=len(ticks)
        need(manifest['native_exit_code']==0 and not manifest['stop_reason'],
             'native STOP; NEVER automatically retry')
        for name in CSV:
            need((result/name).is_file(), 'missing signed-4D file '+name)
        manifest['independent_4d']=phase_with_heartbeat('SIGNED_4D_QA',
            lambda: independent_time_audit(result,'M9',M9_TET10,DT,STEPS))
        manifest['two_term_explicit']=phase_with_heartbeat('P10LM_SIGNED_SPLIT_QA',
            lambda: audit_split(result,'M9',STEPS,DT))
        history=result/'forward_history.bin'
        need(history.is_file(), 'fresh forward history absent')
        manifest['history_sha256']=sha256(history)
        manifest['P10LG_header_sha256']='0a470e43668a751dc0514f94e8e33ad2b8615c9d56c633579dd7112fafcec2b3'
        manifest['status']='P10LM_M9_REAL_FULL4D_PASS'
    except BaseException as error:
        manifest['status']='P10LM_STOP_NO_RETRY'
        manifest['error']=repr(error)
    finally:
        meta=folder/'P10LM_MANIFEST.json'
        meta.write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+'\n',
                        encoding='utf-8')
        evidence=folder/'P10LM_M9_FIRST_FULL4D_EVIDENCE.zip'
        evidence_files=[(meta,meta.name),(log,log.name),(progress,progress.name),
                        (SELFTEST,SELFTEST.name),
                        *[(result/name,name) for name in CSV],
                        (result/SPLIT_CSV,SPLIT_CSV)]
        phase_with_heartbeat('EVIDENCE_PACKAGING',lambda: zip_evidence(evidence,
            [(path,name) for path,name in evidence_files if path.is_file()]))
    print('P10LM_FINAL_STATUS',manifest['status'],flush=True)
    print('P10LM_SEND_ONE_ARCHIVE',evidence,flush=True)
    return 0 if manifest['status']=='P10LM_M9_REAL_FULL4D_PASS' else 2


if __name__=='__main__':
    try:
        sys.exit(main())
    except Exception as error:
        print('P10LM_STOP_NO_FEM_OR_NO_RETRY',repr(error),flush=True)
        sys.exit(2)
