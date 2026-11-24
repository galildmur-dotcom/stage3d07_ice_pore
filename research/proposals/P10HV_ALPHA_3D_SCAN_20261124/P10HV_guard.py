#!/usr/bin/env python3
"""External 600s cap for three-case native 3D α scan, archive evidence."""
import json
from pathlib import Path
import subprocess
import sys
import time
import zipfile

HERE=Path(__file__).resolve().parent
GUARD=HERE/'P10HV_GUARD_RESULT.json'
LOG=HERE/'P10HV_GMSH_LOG.txt'
OUT=HERE/'P10HV_THREE_ALPHA_3D_EVIDENCE.zip'

def main():
    start=time.monotonic()
    with LOG.open('w',encoding='utf-8') as f:
        proc=subprocess.Popen([sys.executable,str(HERE/'P10HV_three_alpha_3d.py')],
                              cwd=HERE,stdout=f,stderr=subprocess.STDOUT)
        milestone=-1
        while proc.poll() is None:
            elapsed=time.monotonic()-start
            if elapsed>=600:
                proc.kill();proc.wait();code=124;status='EXTERNAL_600S_TIMEOUT_KILLED_CHILD';break
            n=int(elapsed//15)
            if n>milestone:
                print(f'P10HV 3D scan: {int(elapsed)} / 600 seconds',flush=True)
                milestone=n
            time.sleep(1)
        else:
            code=proc.returncode;status='WORKER_FINISHED' if code==0 else 'WORKER_STOP'
    GUARD.write_text(json.dumps({'protocol':'P10HV_3D_ALPHA_SCAN_GUARD',
        'status':status,'exit_code':code,'wall_s':round(time.monotonic()-start,3),
        'FEM_attempts':0,'accepted_M2':False},indent=2)+'\n',encoding='utf-8')
    if code==0:
        names=['P10HV_GUARD_RESULT.json','P10HV_GMSH_LOG.txt','P10HV_WORKER_RESULT.json',
               'P10HV_ALPHA_15_M2_UNVERIFIED.msh','P10HV_ALPHA_20_M2_UNVERIFIED.msh',
               'P10HV_ALPHA_25_M2_UNVERIFIED.msh']
        if not all((HERE/n).is_file() for n in names):raise RuntimeError('P10HV_STOP: missing evidence file')
        with zipfile.ZipFile(OUT,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
            for n in names:z.write(HERE/n,n)
        with zipfile.ZipFile(OUT) as z:
            if z.testzip():raise RuntimeError('P10HV_STOP: evidence ZIP CRC')
        print('P10HV_CANDIDATES_UNVERIFIED',OUT,'bytes',OUT.stat().st_size)
    else:
        print(status,'send guard, Gmsh log and worker error, if present')
    return 0 if code==0 else 2

if __name__=='__main__':sys.exit(main())
