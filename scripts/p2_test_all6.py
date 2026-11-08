#!/usr/bin/env python3
"""Stage3D06-P2 matrix-kernel regression across all E/ED/EDV x CONST/VAR.
No physics or j6 definitions are modified.
"""
import argparse,pathlib,subprocess,tempfile
from p06_compare import compare
p=argparse.ArgumentParser()
p.add_argument('--solver',required=True)
p.add_argument('--mesh',required=True)
p.add_argument('--temp-dir',required=True)
p.add_argument('--threads',default='4')
a=p.parse_args()
with tempfile.TemporaryDirectory(prefix='P2_all6_') as tmp:
    root=pathlib.Path(tmp)
    common=['--mesh',a.mesh,'--temp-dir',a.temp_dir,'--law','ALL','--modulus','ALL',
            '--times','300','--quad','3','--optimization','on',
            '--parallel-assembly','on','--threads',a.threads,'--final-vtu-only']
    for mode in ('legacy','projected'):
        subprocess.run([a.solver,*common,'--out',str(root/mode),'--spmv',mode],
                       check=True,stdout=subprocess.DEVNULL)
    for law in ('E','ED','EDV'):
        for mod in ('CONST','VAR'):
            case=f'{law}_{mod}'
            rows,bitwise=compare(root/'legacy'/case,root/'projected'/case)
            if not all(x['passed'] for x in rows):
                for x in rows:print(case,x)
                raise AssertionError(f'P2 {case} regression failed')
            print(f'P2 {case}: PASS; checkpoint_bitwise={bitwise}',flush=True)
