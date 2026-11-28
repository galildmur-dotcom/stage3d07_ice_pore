#!/usr/bin/env python3
"""External bounded 180 s matched-pair Gmsh 2D worker guard."""
import json
from pathlib import Path
import subprocess
import sys
import time

HERE=Path(__file__).resolve().parent
RESULT=HERE/'P10HR_GUARD_RESULT.json'
LOG=HERE/'P10HR_GMSH_LOG.txt'

def main():
    start=time.monotonic()
    with LOG.open('w',encoding='utf-8') as out:
        try:
            p=subprocess.run([sys.executable,str(HERE/'P10HR_matched_2d.py')],cwd=HERE,
                             stdout=out,stderr=subprocess.STDOUT,timeout=180)
            code=p.returncode
            status='WORKER_FINISHED' if code==0 else 'WORKER_STOP'
        except subprocess.TimeoutExpired:
            code=124;status='EXTERNAL_180S_TIMEOUT_KILLED_CHILD'
    RESULT.write_text(json.dumps({'protocol':'P10HR_REAL_CAD_MATCHED_2D_EXTERNAL_GUARD',
        'status':status,'exit_code':code,'wall_s':round(time.monotonic()-start,3),
        'native_3D_M2_FEM_attempts':0},indent=2)+'\n',encoding='utf-8')
    print(status,'return guard, Gmsh log and paired 2D result')
    return 0 if code==0 else 2

if __name__=='__main__':sys.exit(main())
