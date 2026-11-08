#!/usr/bin/env python3
"""H0 physics regression for projected SpMV against legacy, two Newton/EDV time steps.
Uses the same FEM executable with only --spmv changed; checkpoint and CSV checked.
"""
import argparse,pathlib,subprocess,tempfile
from p06_compare import compare
p=argparse.ArgumentParser()
p.add_argument('--solver',required=True)
p.add_argument('--mesh',required=True)
p.add_argument('--temp-dir',required=True)
p.add_argument('--threads',default='4')
a=p.parse_args()
with tempfile.TemporaryDirectory(prefix='P2_h0_') as tmp:
    root=pathlib.Path(tmp)
    common=['--mesh',a.mesh,'--temp-dir',a.temp_dir,'--law','EDV','--modulus','VAR',
            '--times','300,600','--quad','3','--optimization','on',
            '--parallel-assembly','on','--threads',a.threads,'--final-vtu-only']
    for mode in ('legacy','projected'):
        subprocess.run([a.solver,*common,'--out',str(root/mode),'--spmv',mode],
                       check=True,stdout=subprocess.DEVNULL)
    rows,bitwise=compare(root/'legacy/EDV_VAR',root/'projected/EDV_VAR')
    if not all(x['passed'] for x in rows):
        for x in rows:print(x)
        raise AssertionError('P2 full FEM numeric regression failed')
    print(f'P2 H0 two-step EDV_VAR: PASS; checkpoint_bitwise={bitwise}')
