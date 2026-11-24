#!/usr/bin/env python3
"""Guarded first physical R/EDV_VAR solve on P10IP-accepted M3; one attempt."""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import sys

from P10FN_common import (HERE, RUNS, need, now,
                          require_windows, sha256, validate_source, write_new,
                          zip_evidence)
from P10FN_mesh_qa import audit as mesh_audit
from P10FN_physics import compiler_environment, ensure_binary
from P10GY_temporal_series import independent_time_audit, CSV
from P10IR_heartbeat import run_with_heartbeat, compile_with_heartbeat

M3_SHA = '3d6ce765dced7d146ef5228be3b0a8210b4466ed08a0c9f5a20d1917dc2a8c3a'
M3_TET10 = 10063
DT = 25
STEPS = 36
REGIME = {'mode':'R','law':'EDV_VAR','xi':0,'B6_mm':5,
          't_final_s':900,'dt_s':DT,'steps':STEPS,'threads':4}


def mesh_preflight():
    mesh = HERE / 'M3.msh'
    need(mesh.is_file() and sha256(mesh) == M3_SHA,
         'pinned P10IO R2 M3.msh absent or changed; no FEM')
    qa = mesh_audit(mesh)
    need(qa['tet10'] == M3_TET10 and qa['nodes'] == 14653 and
         qa['pore_tri6'] == 262 and qa['nonpositive_samples'] == 0 and
         qa['physical_surface_tags'] == list(range(2,10)),
         'P10IP M3 curved physical-mesh QA differs; no FEM')
    return mesh, qa


def main():
    require_windows()
    validate_source()
    mesh, qa = mesh_preflight()
    need(DT*STEPS == 900, 'physical time horizon')
    print('P10IR_M3_PREFLIGHT_PASS_NO_FEM',
          'mesh_sha256='+M3_SHA,'tet10='+str(M3_TET10), flush=True)
    if '--run' not in sys.argv:
        return 0
    toolchain, build = compile_with_heartbeat(ensure_binary)
    exe = HERE / 'build' / 'stage3d10fn_any_mesh_full4d.exe'
    marker = RUNS / 'P10IR_M3_ONE_SHOT_MARKERS' / (
        f'M3_R_DT{DT}_STEPS{STEPS}_{M3_SHA[:16]}.json')
    need(not marker.exists(), 'M3 physical one-shot already consumed: '+str(marker))
    folder = RUNS / f'P10IR_M3_R_DT{DT}_{now()}'
    folder.mkdir(parents=True, exist_ok=False)
    result = folder / f'P10FN_M3_DT{DT}_R'
    manifest = {'protocol':'P10IR_FIRST_REAL_M3_FULL4D_V1',
                'status':'CONSUMED', 'mesh':'M3','mesh_sha256':M3_SHA,
                'mesh_qa':qa,'regime':REGIME,'FEM_attempts':1,
                'fresh_forward':True,'same_mesh_analytic_adjoint':True,
                'mesh_source':'P10IO_R2_P10IP_GEOMETRY_GO_20261124',
                'exe_sha256':build['exe_sha256'], 'started_utc':now(),
                'one_shot_marker':str(marker)}
    write_new(marker,manifest)
    local_marker = folder / 'P10FN_ONE_SHOT_CONSUMED.json'
    write_new(local_marker,manifest)
    command = [str(exe),'--p10fn-authorized','--mesh',str(mesh),
               '--out',str(result),'--mode','R','--steps',str(STEPS),
               '--dt',str(DT),'--cutoff-mm','5','--threads','4']
    env = compiler_environment(toolchain)
    env['P10FN_ONE_SHOT_MARKER'] = str(local_marker)
    log = folder / 'P10IR_NATIVE_LOG.txt'
    try:
        manifest.update(run_with_heartbeat(command,cwd=HERE,log=log,wall_s=2400,
                                           memory_gib=8,output_dir=folder,
                                           output_gib=2,env=env))
        need(manifest['native_exit_code']==0 and not manifest['stop_reason'],
             'native STOP; never auto-retry')
        for name in CSV:
            need((result/name).is_file(), 'missing signed-4D file '+name)
        manifest['independent_4d'] = independent_time_audit(
            result,'M3',M3_TET10,DT,STEPS)
        history=result/'forward_history.bin'
        need(history.is_file(), 'fresh forward history absent')
        manifest['history_sha256']=sha256(history)
        manifest['status']='P10IR_M3_REAL_FULL4D_PASS'
    except BaseException as error:
        manifest['status']='P10IR_STOP_NO_RETRY'
        manifest['error']=repr(error)
    finally:
        meta=folder/'P10IR_MANIFEST.json'
        meta.write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+'\n',
                        encoding='utf-8')
        evidence=folder/'P10IR_M3_FIRST_FULL4D_EVIDENCE.zip'
        zip_evidence(evidence,[(meta,meta.name),(log,log.name),
                    *[(result/name,name) for name in CSV]])
    print('P10IR_FINAL_STATUS',manifest['status'],flush=True)
    print('P10IR_SEND_ONE_ARCHIVE',evidence,flush=True)
    return 0 if manifest['status']=='P10IR_M3_REAL_FULL4D_PASS' else 2


if __name__=='__main__':
    try:
        sys.exit(main())
    except Exception as error:
        print('P10IR_STOP_NO_FEM_OR_NO_RETRY',repr(error),flush=True)
        sys.exit(2)
