#!/usr/bin/env python3
"""Independent external Gmsh 2D worker timeout, 180 s."""
import json
from pathlib import Path
import subprocess
import sys
import time

HERE=Path(__file__).resolve().parent
REPORT=HERE/'P10HQ_GUARD_RESULT.json'
LOG=HERE/'P10HQ_GMSH_LOG.txt'

def main():
    start=time.monotonic()
    with LOG.open('w',encoding='utf-8') as f:
        try:
            p=subprocess.run([sys.executable,str(HERE/'P10HQ_real_cad_one_2d.py')],cwd=HERE,
                             stdout=f,stderr=subprocess.STDOUT,timeout=180)
            status='WORKER_FINISHED' if p.returncode==0 else 'WORKER_STOP'
            code=p.returncode
        except subprocess.TimeoutExpired:
            status='EXTERNAL_180S_TIMEOUT_KILLED_CHILD';code=124
    REPORT.write_text(json.dumps({'protocol':'P10HQ_REAL_CAD_2D_GUARD',
        'status':status,'exit_code':code,'wall_s':round(time.monotonic()-start,3),
        'native_3d_fem_m2_attempts':0},indent=2)+'\n',encoding='utf-8')
    print(status,'send P10HQ_GUARD_RESULT.json and P10HQ_GMSH_LOG.txt')
    return 0 if code==0 else 2

if __name__=='__main__':sys.exit(main())
