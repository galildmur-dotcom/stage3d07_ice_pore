#!/usr/bin/env python3
"""Independent GH3/zero arithmetic and legacy j6 check for Stage 3D-09B.
Usage: python tests/p09b_numeric_audit.py path/to/P09B/output [path/to/P09A_COMPARISON.csv]
"""
import csv
import math
import pathlib
import sys

def read(path):
    with open(path, newline='', encoding='utf-8') as f:
        return list(csv.DictReader(f))

def eq(a, b, tol=3e-11):
    return math.isfinite(a) and math.isfinite(b) and abs(a-b)<=tol*max(1., abs(a),abs(b))

def check(base, old=None):
    sc = read(base / 'P09B_SCENARIOS.csv')
    rows = read(base / 'P09B_COMPARISON.csv')
    assert len(rows)>0
    weights = {0.0: 2./3.,-math.sqrt(3):1./6.,math.sqrt(3):1./6.}
    for row in rows:
        sample = [x for x in sc if x['law']==row['law'] and x['modulus']==row['modulus']]
        assert len(sample)==int(row['xi_nodes'])
        for f, name in [('j6','j6'),('jpeak','jpeak'),('jen','jen')]:
            z = [(float(x['weight']),float(x[name])) for x in sample]
            for w,v in z: assert math.isfinite(w) and math.isfinite(v) and w>0 and v>=0
            assert eq(sum(w for w,v in z),1.0)
            mu=sum(w*v for w,v in z)
            var=sum(w*(v-mu)**2 for w,v in z)
            assert eq(mu,float(row[f'mean_{f}'])), (row['law'],row['modulus'],f,'mean')
            assert eq(var,float(row[f'variance_{f}'])), (row['law'],row['modulus'],f,'var')
        zero = next(x for x in sample if float(x['xi'])==0.)
        assert eq(float(zero['j6']),float(row['xi0_j6']))
    if old:
        for o in read(old):
            match=next((r for r in rows if r['law']==o['law'] and r['modulus']==o['modulus']), None)
            if match:
                for name in ['mean_j6','variance_j6','xi0_j6']:
                    assert eq(float(match[name]),float(o[name]),tol=1e-13), (o['law'],o['modulus'],name)
    print(f'P09B_AUDIT_OK: {len(sc)} trajectories, {len(rows)} models, three GH moments'+(' and legacy j6 match' if old else ''))

if __name__=='__main__':
    if len(sys.argv) not in (2,3):
        sys.exit('Usage: python tests/p09b_numeric_audit.py P09B_OUTPUT_FOLDER [P09A_COMPARISON.csv]')
    check(pathlib.Path(sys.argv[1]),pathlib.Path(sys.argv[2]) if len(sys.argv)==3 else None)
