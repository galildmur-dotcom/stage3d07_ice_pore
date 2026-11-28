#!/usr/bin/env python3
"""600s external guard; ZIP only a finished 3D candidate, no FEM."""
import json
from pathlib import Path
import subprocess
import sys
import time
import zipfile

HERE=Path(__file__).resolve().parent
GUARD=HERE/'P10HS_GUARD_RESULT.json'
LOG=HERE/'P10HS_GMSH_LOG.txt'
EVIDENCE=HERE/'P10HS_M2_UNVERIFIED_CANDIDATE_EVIDENCE.zip'


def main():
    start=time.monotonic()
    with LOG.open('w',encoding='utf-8') as out:
        p=subprocess.Popen([sys.executable,str(HERE/'P10HS_one_3d_candidate.py')],
                           cwd=HERE,stdout=out,stderr=subprocess.STDOUT)
        print('P10HS worker started; maximum 600 seconds; progress every 15 s.',flush=True)
        last=-1
        while p.poll() is None:
            elapsed=time.monotonic()-start
            if elapsed>=600:
                p.kill()
                p.wait()
                code=124;status='EXTERNAL_600S_TIMEOUT_KILLED_CHILD'
                break
            milestone=int(elapsed//15)
            if milestone>last:
                print(f'P10HS 3D candidate still running: {int(elapsed)} / 600 s',flush=True)
                last=milestone
            time.sleep(1)
        else:
            code=p.returncode
            status='WORKER_FINISHED' if code==0 else 'WORKER_STOP'
    result={'protocol':'P10HS_REAL_3D_M2_CANDIDATE_EXTERNAL_GUARD',
            'status':status,'exit_code':code,
            'wall_s':round(time.monotonic()-start,3),
            'M2_accepted':False,'FEM_attempts':0}
    GUARD.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    if code==0:
        names=('P10HS_GUARD_RESULT.json','P10HS_GMSH_LOG.txt',
               'P10HS_WORKER_RESULT.json','P10HS_M2_CANDIDATE_UNVERIFIED.msh')
        if not all((HERE/n).is_file() for n in names):
            raise RuntimeError('P10HS_STOP: missing complete candidate evidence')
        with zipfile.ZipFile(EVIDENCE,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
            for n in names:z.write(HERE/n,n)
        with zipfile.ZipFile(EVIDENCE) as z:
            if z.testzip():raise RuntimeError('P10HS_STOP: evidence CRC')
        print('P10HS_CANDIDATE_ONLY',EVIDENCE,'bytes',EVIDENCE.stat().st_size)
    else:
        print(status,'return P10HS_GUARD_RESULT.json and P10HS_GMSH_LOG.txt')
    return 0 if code==0 else 2

if __name__=='__main__':sys.exit(main())
