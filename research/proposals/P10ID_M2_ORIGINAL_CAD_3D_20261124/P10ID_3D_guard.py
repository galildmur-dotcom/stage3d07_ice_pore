#!/usr/bin/env python3
"""P10ID one-shot guarded Gmsh 3D-only trial (local or Windows)."""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import zipfile

import P10IB_2D_worker as base
from P10IB_2D_guard import private_bytes

HERE=Path(__file__).resolve().parent
MARKER=HERE/'P10ID_ONE_3D_ATTEMPT_CONSUMED.marker'
GUARD=HERE/'P10ID_GUARD_RESULT.json'
LOG=HERE/'P10ID_GMSH_LOG.txt'
EVIDENCE=HERE/'P10ID_M2_3D_EVIDENCE.zip'
MAX_TIME=900
MAX_MEMORY=8*1024**3
MAX_LOG=16*1024**2
MAX_MSH=750*1024**2

def mem(pid):
    if sys.platform=='win32':return private_bytes(pid)
    try:
        status=(Path('/proc')/str(pid)/'status').read_text()
        for row in status.splitlines():
            if row.startswith('VmRSS:'):return int(row.split()[1])*1024
    except (FileNotFoundError,PermissionError):pass
    return None

def main():
    if MARKER.exists():
        print('P10ID_STOP: attempt already consumed; never rerun',flush=True)
        return 2
    for name,sha in (('P10GT_HXT10.geo',base.GEO_SHA),
                     ('P10GT_HXT10.msh',base.M1_SHA),
                     ('P10HA_SPATIAL_KAPPA_1200_BINS.csv',base.CSV_SHA),
                     ('P10HA_KAPPA_QA.json',base.QA_SHA)):
        base.check_sha(name,sha)
    import gmsh
    base.need(gmsh.__version__=='4.15.2','pinned gmsh Python version')
    with MARKER.open('x',encoding='ascii') as f:
        f.write('P10ID one original CAD 3D mesh-only trial, no FEM\n')
    start=time.monotonic();peak=0;status='UNKNOWN';rc=2
    with LOG.open('w',encoding='utf8') as out:
        process=subprocess.Popen([sys.executable,str(HERE/'P10ID_3D_worker.py')],
                                 cwd=HERE,stdout=out,stderr=subprocess.STDOUT,
                                 env={**os.environ,'OPENBLAS_NUM_THREADS':'1'})
        while process.poll() is None:
            elapsed=time.monotonic()-start
            ram=mem(process.pid)
            if ram is not None:peak=max(peak,ram)
            if elapsed>MAX_TIME:
                status='STOP_WALL_900S';rc=124;process.kill();process.wait();break
            if ram is not None and ram>MAX_MEMORY:
                status='STOP_MEMORY_8GIB';rc=125;process.kill();process.wait();break
            if LOG.stat().st_size>MAX_LOG:
                status='STOP_LOG_16MIB';rc=126;process.kill();process.wait();break
            time.sleep(.5)
        else:
            rc=process.returncode
            status='WORKER_FINISHED' if rc==0 else 'WORKER_STOP'
    if rc==0:
        mesh=HERE/'P10ID_M2_3D_UNVERIFIED.msh'
        if not mesh.is_file() or mesh.stat().st_size>MAX_MSH:
            rc=127;status='STOP_MESH_MISSING_OR_OVER_750MIB'
    payload={'status':status,'exit_code':rc,
             'wall_s':round(time.monotonic()-start,3),
             'observed_peak_bytes':peak,'memory_measure':'private' if sys.platform=='win32' else 'VmRSS',
             'max_wall_s':MAX_TIME,'max_memory_bytes':MAX_MEMORY,
             'max_mesh_bytes':MAX_MSH,'max_log_bytes':MAX_LOG,
             'one_shot_consumed':True,'mesh_attempts_3D':1,'FEM_attempts':0,
             'accepted_M2':False}
    GUARD.write_text(json.dumps(payload,indent=2)+'\n',encoding='utf8')
    if rc==0:
        files=['P10ID_GUARD_RESULT.json','P10ID_GMSH_LOG.txt',
               'P10ID_WORKER_RESULT.json','P10ID_M2_3D_UNVERIFIED.msh',
               'P10ID_ONE_3D_ATTEMPT_CONSUMED.marker']
        with zipfile.ZipFile(EVIDENCE,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
            for name in files:z.write(HERE/name,name)
        with zipfile.ZipFile(EVIDENCE) as z:base.need(z.testzip() is None,'evidence CRC')
        print('P10ID_M2_3D_CANDIDATE_EVIDENCE_CREATED',flush=True)
    else:print('P10ID_STOP: return guard/log/error, do not rerun',flush=True)
    return 0 if rc==0 else 2

if __name__=='__main__':
    try:sys.exit(main())
    except Exception as exc:
        print('P10ID_GUARD_STOP',type(exc).__name__,str(exc),flush=True)
        sys.exit(2)
