#!/usr/bin/env python3
"""Independent finite-difference GH3 audit & H3/H4/HP comparison.
No dependencies beyond Python stdlib. Does not count as FEM solver validation.
"""
import argparse,csv,math,pathlib

def table(path):
    with open(path,newline='',encoding='utf-8-sig') as f:return list(csv.DictReader(f))
def byfun(path):
    rows=table(path)
    return {r['functional']:r for r in rows if r['mode']=='y20' and r['law']=='EDV' and r['modulus']=='VAR'}
def check(hp_root):
    node=table(hp_root/'P09C_NODES.csv'); orig=byfun(hp_root/'P09C_SENSITIVITIES.csv')
    if set(orig)!={'j6','jpeak','jen'}:raise ValueError('Not exactly three output functionals for HP/y20/EDV/VAR')
    for f in orig:
        sample=sorted((r for r in node if r['mode']=='y20' and r['law']=='EDV' and r['modulus']=='VAR' and r['functional']==f),key=lambda r:float(r['xi']))
        if len(sample)!=3:raise ValueError('Missing GH3 node for '+f)
        w=[float(x['weight']) for x in sample];p=[float(x['value_plus']) for x in sample];m=[float(x['value_minus']) for x in sample]
        if abs(sum(w)-1)>1e-14:raise ValueError('Invalid weights')
        delta=float(orig[f]['delta_um'])*1e-6
        mp=sum(a*b for a,b in zip(w,p));mm=sum(a*b for a,b in zip(w,m))
        vp=sum(a*(b-mp)**2 for a,b in zip(w,p));vm=sum(a*(b-mm)**2 for a,b in zip(w,m))
        deriv=(mp-mm)/(2*delta); dvar=(vp-vm)/(2*delta)
        v1=float(orig[f]['D_mean_per_m']);v2=float(orig[f]['D_variance_per_m'])
        if abs(deriv-v1)>1e-8*max(1,abs(v1)) or abs(dvar-v2)>1e-8*max(1,abs(v2)):
            raise ValueError(f'Derivative mismatch for {f}')
    return orig

def main():
    ap=argparse.ArgumentParser();ap.add_argument('hp_output_dir');args=ap.parse_args();p=pathlib.Path(args.hp_output_dir)
    base=pathlib.Path(__file__).resolve().parents[1]/'P09D_REFERENCE'
    r3=byfun(base/'H3_y20.csv');r4=byfun(base/'H4_y20.csv');rp=check(p)
    print('function,stat,H3,H4,HP,H4_to_HP_percent,stable_sign')
    for fun in ('j6','jpeak','jen'):
        for stat,col in [('mean','D_mean_per_m'),('variance','D_variance_per_m')]:
            a=float(r3[fun][col]);b=float(r4[fun][col]);c=float(rp[fun][col]);diff=100*(c-b)/abs(b)
            print(f'{fun},{stat},{a:.12g},{b:.12g},{c:.12g},{diff:.5f},{(a*b>0 and b*c>0)}')
    print('P09D_HP_GH3_AUDIT_OK')
    print('CAUTION: This compares nonnested meshes; no rigorous discretization error estimate.')
if __name__=='__main__':main()
