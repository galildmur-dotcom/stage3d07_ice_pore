#!/usr/bin/env python3
"""Physical H0 regression: E/ED/EDV, CONST/VAR, P2 Jacobi vs P5 Additive Schwarz AS0/AS1.
Uses the same optimized FEM executable, mesh, temperatures and P2 projected SpMV.
"""
import argparse
import csv
from pathlib import Path
import subprocess
import tempfile
import math
import sys


def read_summary(root,law,mod):
    fp = root/(law+'_'+mod)/'time_series.csv'
    with fp.open(newline='',encoding='utf-8') as f:
        table=list(csv.DictReader(f))
    if len(table)!=1:raise RuntimeError(f'Expected one time step in {fp}, got {len(table)}')
    return table[0]


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--solver',type=Path,required=True)
    ap.add_argument('--mesh',type=Path,required=True)
    ap.add_argument('--temp-dir',type=Path,default=None,help='Optional precomputed matching field directory')
    ap.add_argument('--thermal',type=Path,help='Thermal solver to create missing fields')
    ap.add_argument('--compare',type=Path,help='Checkpoint comparator for all internal variables')
    ap.add_argument('--threads',type=int,default=4)
    ap.add_argument('--times',default='300')
    args=ap.parse_args()
    for name,path in [('solver',args.solver),('mesh',args.mesh)]:
        if not path.exists():raise RuntimeError(f'{name} input is missing: {path}')
    with tempfile.TemporaryDirectory(prefix='p3_all6_') as tmp:
        data=Path(tmp)
        thermal_dir=args.temp_dir if args.temp_dir else data/'thermal'
        if args.temp_dir is None:
            if args.thermal is None or not args.thermal.exists():
                raise RuntimeError('Supply --thermal to generate temperatures, or --temp-dir')
            schedule=[int(s) for s in args.times.split(',')]
            if sorted(schedule)!=schedule or min(schedule)<=0 or len(set(schedule))!=len(schedule):
                raise RuntimeError('Expected unique increasing time steps')
            if len(schedule)==1:
                dt=schedule[0]
            else:
                dt=schedule[0]
                if schedule!=list(range(dt,schedule[-1]+1,dt)):
                    raise RuntimeError('Generated thermal field requires uniform --times increments')
            subprocess.run([str(args.thermal.resolve()),'--mesh',str(args.mesh.resolve()),
                 '--out',str(thermal_dir),'--dt',str(dt),'--tend',str(schedule[-1]),
                 '--xi','0','--every-step'],check=True,timeout=90)
        for seconds in args.times.split(','):
            temp=thermal_dir/('thermal_'+seconds+'s.vtu')
            if not temp.exists():raise RuntimeError('Missing thermal field '+str(temp))

        for prec in ['jacobi','as0','as1']:
            cmd=[str(args.solver.resolve()),'--mesh',str(args.mesh.resolve()),
                 '--temp-dir',str(thermal_dir.resolve()),'--out',str(data/prec),
                 '--law','ALL','--modulus','ALL','--times',args.times,
                 '--optimization','on','--spmv','projected',
                 '--preconditioner',prec,'--schwarz-core','32','--cg-tol','1e-9','--newton-tol','1e-8','--profile','--threads',str(args.threads),
                 '--final-vtu-only']
            print('RUN:', ' '.join(cmd),flush=True)
            subprocess.run(cmd,check=True,timeout=290)
        fields=['Psi6','PsiOmega','maxS1_MPa']
        for law in ('E','ED','EDV'):
            for mod in ('CONST','VAR'):
                # Compare end-step physical quantities and solver residuals.
                def last(prec):
                    fp=data/prec/(law+'_'+mod)/'time_series.csv'
                    with fp.open(newline='',encoding='utf-8') as f:rows=list(csv.DictReader(f))
                    if not rows:raise RuntimeError('Empty '+str(fp))
                    return rows[-1]
                aa=last('jacobi')
                for prec in ('as0','as1'):
                    bb=last(prec)
                    for field in fields:
                        va,vb=float(aa[field]),float(bb[field])
                        tol=1e-9+5e-7*max(abs(va),abs(vb))
                        if not math.isfinite(va) or not math.isfinite(vb) or abs(va-vb)>tol:
                            raise RuntimeError(f'{law}/{mod} {field}: Jacobi={va}, {prec}={vb}, tol={tol}')
                    if float(bb['residual_rel'])>1e-5:
                        raise RuntimeError(f'Unacceptable Newton residual: {law}/{mod}: {bb["residual_rel"]}')
                    if args.compare:
                        comparison=data/f'{law}_{mod}_{prec}_restart_comparison.csv'
                        subprocess.run([str(args.compare.resolve()),
                            '--baseline',str(data/'jacobi'/(law+'_'+mod)/'restart.bin'),
                            '--optimized',str(data/prec/(law+'_'+mod)/'restart.bin'),
                            '--output',str(comparison),'--tol','1e-6'],check=True,timeout=30)
                    print('PASS',law,mod,prec,'Jacobi CG',aa['CG'],'Schwarz CG',bb['CG'],flush=True)
        print('P5 FEM PASS all six E/ED/EDV × CONST/VAR H0, Jacobi/AS0/AS1, checkpoint')

if __name__=='__main__':
    try:main()
    except Exception as e:print('P5 FEM FAIL',e,file=sys.stderr);sys.exit(2)
