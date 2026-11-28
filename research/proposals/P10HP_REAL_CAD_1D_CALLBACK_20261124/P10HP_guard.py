#!/usr/bin/env python3
"""External 120 s hard timeout guard, independent from Gmsh native internals."""
from pathlib import Path
import json
import subprocess
import sys
import time

HERE=Path(__file__).resolve().parent
RESULT=HERE/'P10HP_GUARD_RESULT.json'
LOG=HERE/'P10HP_GMSH_LOG.txt'

def main():
    start=time.monotonic()
    with LOG.open('w',encoding='utf-8') as log:
        try:
            p=subprocess.run([sys.executable,str(HERE/'P10HP_real_cad_one_1d.py')],
                             cwd=HERE,stdout=log,stderr=subprocess.STDOUT,
                             timeout=120)
            status='WORKER_FINISHED' if p.returncode==0 else 'WORKER_STOP'
            return_code=p.returncode
        except subprocess.TimeoutExpired:
            status='EXTERNAL_120S_TIMEOUT_KILLED_CHILD'
            return_code=124
    report={'protocol':'P10HP_R1_REAL_CAD_ONE_1D_EXTERNAL_GUARD',
            'status':status,'worker_exit_code':return_code,
            'wall_s':round(time.monotonic()-start,3),
            'native_2d_3d_fem_m2_attempts':0,
            'read_next':'Submit guard result and Gmsh log; no automatic retry or M2'}
    RESULT.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(status,'guard',RESULT,'log',LOG)
    return 0 if return_code==0 else 2

if __name__=='__main__':sys.exit(main())
