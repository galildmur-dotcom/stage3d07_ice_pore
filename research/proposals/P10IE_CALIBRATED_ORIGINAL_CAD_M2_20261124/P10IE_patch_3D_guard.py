#!/usr/bin/env python3
"""One-time bounded P10IE C1 patch 3D M2 geometry pilot, no FEM."""
from __future__ import annotations
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import zipfile
import P10IB_2D_worker as pinned
from P10ID_3D_guard import mem

HERE=Path(__file__).resolve().parent
MARKER=HERE/'P10IE_ONE_3D_ATTEMPT_CONSUMED.marker'
LOG=HERE/'P10IE_GMSH_LOG.txt'
RESULT=HERE/'P10IE_GUARD_RESULT.json'
EVIDENCE=HERE/'P10IE_PATCH_M2_3D_EVIDENCE.zip'
WALL=900
RAM=8*1024**3
LOG_LIMIT=16*1024**2
MSH_LIMIT=750*1024**2

def main():
    if MARKER.exists():
        print('P10IE_STOP: marker consumed, no repeat',flush=True)
        return 2
    for n,sha in [('P10GT_HXT10.geo',pinned.GEO_SHA),
                  ('P10GT_HXT10.msh',pinned.M1_SHA),
                  ('P10HA_SPATIAL_KAPPA_1200_BINS.csv',pinned.CSV_SHA),
                  ('P10HA_KAPPA_QA.json',pinned.QA_SHA)]:pinned.check_sha(n,sha)
    import gmsh
    pinned.need(gmsh.__version__=='4.15.2','gmsh must be 4.15.2')
    with MARKER.open('x',encoding='ascii') as f:f.write('P10IE one bounded 3D Gmsh, FEM=0\n')
    begin=time.monotonic();status='UNKNOWN';rc=2;peak=0
    with LOG.open('w',encoding='utf8') as log:
        proc=subprocess.Popen([sys.executable,str(HERE/'P10IE_patch_3D_worker.py')],
                              cwd=HERE,stdout=log,stderr=subprocess.STDOUT,
                              env={**os.environ,'OPENBLAS_NUM_THREADS':'1'})
        while proc.poll() is None:
            m=mem(proc.pid)
            if m is not None:peak=max(peak,m)
            if time.monotonic()-begin>WALL:
                rc=124;status='STOP_WALL';proc.kill();proc.wait();break
            if m is not None and m>RAM:
                rc=125;status='STOP_MEMORY';proc.kill();proc.wait();break
            if LOG.stat().st_size>LOG_LIMIT:
                rc=126;status='STOP_LOG';proc.kill();proc.wait();break
            time.sleep(.5)
        else:
            rc=proc.returncode
            status='WORKER_FINISHED' if rc==0 else 'WORKER_STOP'
    if rc==0:
        msh=HERE/'P10IE_M2_PATCH_CALIBRATED_3D_UNVERIFIED.msh'
        if not msh.exists() or msh.stat().st_size>MSH_LIMIT:
            status='STOP_MSH';rc=127
    RESULT.write_text(json.dumps({
        'status':status,'exit_code':rc,'wall_s':round(time.monotonic()-begin,3),
        'peak_observed_bytes':peak,'max_wall_s':WALL,'max_memory_bytes':RAM,
        'one_shot_consumed':True,'mesh_attempts_3D':1,
        'FEM_attempts':0,'accepted_M2':False},indent=2)+'\n',encoding='utf8')
    if rc==0:
        files=['P10IE_GUARD_RESULT.json','P10IE_GMSH_LOG.txt','P10IE_WORKER_RESULT.json',
               'P10IE_M2_PATCH_CALIBRATED_3D_UNVERIFIED.msh',
               'P10IE_ONE_3D_ATTEMPT_CONSUMED.marker']
        with zipfile.ZipFile(EVIDENCE,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
            for f in files:z.write(HERE/f,f)
        with zipfile.ZipFile(EVIDENCE) as z:pinned.need(z.testzip() is None,'CRC failure')
        print('P10IE_NEW_3D_EVIDENCE_COMPLETE_NO_FEM',flush=True)
    else:print('P10IE_STOP: return guard/log/error; never rerun consumed marker',flush=True)
    return 0 if rc==0 else 2

if __name__=='__main__':
    try:sys.exit(main())
    except Exception as e:
        print('P10IE_GUARD_STOP',type(e).__name__,str(e),flush=True)
        sys.exit(2)
