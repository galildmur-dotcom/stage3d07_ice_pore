#!/usr/bin/env python3
"""CTest: H0 EDV_VAR two steps, original solver vs 4-thread race-free assembly."""
import argparse,subprocess,tempfile,pathlib,sys
from p06_compare import compare
p=argparse.ArgumentParser();p.add_argument('--baseline',required=True);p.add_argument('--optimized',required=True)
p.add_argument('--mesh',required=True);p.add_argument('--temp-dir',required=True);p.add_argument('--threads',default='4')
a=p.parse_args()
with tempfile.TemporaryDirectory(prefix='P06_regression_') as td:
    td=pathlib.Path(td)
    base=['--mesh',a.mesh,'--temp-dir',a.temp_dir,'--law','EDV','--modulus','VAR','--times','300,600','--final-vtu-only']
    subprocess.run([a.baseline,*base,'--out',str(td/'baseline')],check=True,stdout=subprocess.DEVNULL)
    subprocess.run([a.optimized,*base,'--out',str(td/'optimized'),'--threads',a.threads,'--parallel-assembly','on'],check=True,stdout=subprocess.DEVNULL)
    rows,exact=compare(td/'baseline/EDV_VAR',td/'optimized/EDV_VAR')
    if not all(r['passed'] for r in rows):raise RuntimeError('P06 numerical discrepancy')
    print(f'P06 H0 two-step E/EDV regression: PASS, checkpoint_bitwise_equal={exact}')
