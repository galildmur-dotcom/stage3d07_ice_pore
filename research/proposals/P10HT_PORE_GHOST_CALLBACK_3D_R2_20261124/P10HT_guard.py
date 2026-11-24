#!/usr/bin/env python3
"""P10HT only one 3D Gmsh child with 600s deadline and evidence ZIP."""
import json
from pathlib import Path
import subprocess
import sys
import time
import zipfile

HERE=Path(__file__).resolve().parent
GUARD=HERE/'P10HT_GUARD_RESULT.json'
LOG=HERE/'P10HT_GMSH_LOG.txt'
EVIDENCE=HERE/'P10HT_M2_UNVERIFIED_CANDIDATE_EVIDENCE.zip'


def main():
    begin=time.monotonic()
    with LOG.open('w',encoding='utf-8') as out:
        p=subprocess.Popen([sys.executable,str(HERE/'P10HT_one_3d_candidate_r2.py')],
                           cwd=HERE,stdout=out,stderr=subprocess.STDOUT)
        last=-1
        while p.poll() is None:
            elapsed=time.monotonic()-begin
            if elapsed>=600:
                p.kill();p.wait();code=124;status='EXTERNAL_600S_TIMEOUT_KILLED_CHILD';break
            slot=int(elapsed//15)
            if slot>last:
                print(f'P10HT 3D running: {int(elapsed)} / 600 s',flush=True)
                last=slot
            time.sleep(1)
        else:
            code=p.returncode;status='WORKER_FINISHED' if code==0 else 'WORKER_STOP'
    result={'protocol':'P10HT_R2_REAL_CAD_3D_GUARD','status':status,
            'exit_code':code,'wall_s':round(time.monotonic()-begin,3),
            'accepted_M2':False,'FEM_attempts':0}
    GUARD.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    if code==0:
        names=('P10HT_GUARD_RESULT.json','P10HT_GMSH_LOG.txt',
               'P10HT_WORKER_RESULT.json','P10HT_M2_CANDIDATE_UNVERIFIED.msh')
        if not all((HERE/n).is_file() for n in names):
            raise RuntimeError('P10HT_STOP: incomplete candidate evidence')
        with zipfile.ZipFile(EVIDENCE,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
            for n in names:z.write(HERE/n,n)
        with zipfile.ZipFile(EVIDENCE) as z:
            if z.testzip():raise RuntimeError('P10HT_STOP: ZIP CRC')
        print('P10HT_CANDIDATE_ONLY',EVIDENCE,'bytes',EVIDENCE.stat().st_size)
    else:
        print(status,'send P10HT_GUARD_RESULT.json and P10HT_GMSH_LOG.txt')
    return 0 if code==0 else 2

if __name__=='__main__':sys.exit(main())
