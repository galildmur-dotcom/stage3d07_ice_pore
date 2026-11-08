#!/usr/bin/env python3
"""Cross-check P09A moment tables using independent decimal-CSV reading."""
import csv, math, sys
from pathlib import Path
p=Path(sys.argv[1]) if len(sys.argv)>1 else Path(__file__).resolve().parents[1]/'STAGE3D09A_PILOT'
def read(name):
 with open(p/name,encoding='utf-8',newline='') as f:return list(csv.DictReader(f))
rr=read('P09A_SCENARIOS.csv'); cc=read('P09A_COMPARISON.csv')
assert len(rr)==18 and len(cc)==6
for row in cc:
 cases=[r for r in rr if r['law']==row['law'] and r['modulus']==row['modulus']]
 assert len(cases)==3
 weight=sum(float(r['weight']) for r in cases)
 assert abs(weight-1)<1e-12
 mean=sum(float(r['weight'])*float(r['j6']) for r in cases)
 variance=sum(float(r['weight'])*(float(r['j6'])-mean)**2 for r in cases)
 assert math.isclose(mean,float(row['mean_j6']),rel_tol=1e-11,abs_tol=1e-15)
 assert math.isclose(variance,float(row['variance_j6']),rel_tol=1e-11,abs_tol=1e-15)
 assert min(float(r['steps']) for r in cases)==1
print('P09A_PILOT_INDEPENDENT_AUDIT_OK 18 cases; 6 means and variances')
