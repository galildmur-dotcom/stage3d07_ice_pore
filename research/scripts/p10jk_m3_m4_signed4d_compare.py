#!/usr/bin/env python3
"""Independent read-only M3/M4 signed space-time comparison and polar QA."""
import csv
import hashlib
import json
import math
from pathlib import Path
import sys

import numpy as np
from p10it_compare import read, PARTS, KEY, BOUNDS

M3_D = 2.4732148709178685
M4_D = 2.388080130362648


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main(m2path, m3path, m4path, outdir):
    m2, b2, q2 = read(Path(m2path), 'M2')
    m3, b3, q3 = read(Path(m3path), 'M3')
    m4, b4, q4 = read(Path(m4path), 'M4')
    assert m2.keys()==m3.keys()==m4.keys()
    assert b2==b3==b4
    keys=sorted(b4)
    n=len(keys)
    assert n==1200
    d32=np.array([[m3[k+(s,)]-m2[k+(s,)] for s in range(1,37)] for k in keys])
    d43=np.array([[m4[k+(s,)]-m3[k+(s,)] for s in range(1,37)] for k in keys])
    assert np.all(np.isfinite(d43))
    signed43=float(d43.sum())
    assert abs(signed43-(M4_D-M3_D))<2e-9
    for k in keys:
        for s in range(1,37):
            assert min(q2[k+(s,)],q3[k+(s,)],q4[k+(s,)])>0
    near=np.array([k[0]<=4 for k in keys],bool)
    north=np.array([k[0]<=4 and k[1]==9 for k in keys],bool)
    south=np.array([k[0]<=4 and k[1]==0 for k in keys],bool)
    masks={'N':north,'S':south,'polar':north|south,'near':near,'all':np.ones(n,bool)}
    spatial=d43.sum(axis=1)
    polarcomp={}
    for name,mask in masks.items():
        aa=d43[mask]
        bb=d32[mask]
        polarcomp[name]={
            'bins':int(mask.sum()),
            'M3_over_M2_signed':float(bb.sum()),
            'M4_over_M3_signed':float(aa.sum()),
            'M4_over_M3_component':dict(zip(PARTS,map(float,aa.sum(axis=(0,1))))),
            'M4_over_M3_L1_spatial_signed_total':float(np.abs(aa.sum(axis=2)).sum()),
            'M4_over_M3_L1_component_4D':float(np.abs(aa).sum()),
            'M4_over_M3_L1_temporal_signed_bin':float(np.abs(aa.sum(axis=2)).sum()),
            'M3_over_M2_L1_temporal_signed_bin':float(np.abs(bb.sum(axis=2)).sum()),
            'M3_QP':int(sum(q3[k+(s,)] for k,m in zip(keys,mask) if m for s in range(1,37))),
            'M4_QP':int(sum(q4[k+(s,)] for k,m in zip(keys,mask) if m for s in range(1,37))),
        }
    result={'protocol':'P10JK_INDEPENDENT_M2_M3_M4_DT25_SIGNED_4D',
            'status':'PASS_SOURCE_ONLY_NO_GMSH_NO_FEM',
            'inputs_sha256':{'M2':sha(m2path),'M3':sha(m3path),'M4':sha(m4path)},
            'time_steps':36,'dt_s':25,'bins':n,
            'M3_D_R_jpeak_per_m':M3_D,'M4_D_R_jpeak_per_m':M4_D,
            'M4_minus_M3_per_m':signed43,
            'M3_minus_M2_per_m':float(d32.sum()),
            'ratio_absolute_sequential_increments':abs(signed43/d32.sum()),
            'component_signed_delta_M4_M3':dict(zip(PARTS,map(float,d43.sum(axis=(0,1))))),
            'sum_abs_component_4d_delta_M4_M3':float(np.abs(d43).sum()),
            'spacetime_L1_total_delta_M4_M3':float(np.abs(d43.sum(axis=2)).sum()),
            'cancellation_factor':float(np.abs(d43.sum(axis=2)).sum()/abs(signed43)),
            'regions':polarcomp,
            'FEM_attempts':0}
    out=Path(outdir)
    out.mkdir(parents=True,exist_ok=True)
    (out/'P10JK_M3_M4_SIGNED4D_QA.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    with (out/'P10JK_M3_M4_1200_SIGNED_BINS.csv').open('w',newline='') as f:
        fields=list(KEY)+['M3_QP','M4_QP','M3_to_M4_signed','M3_to_M4_temporal_L1','M2_to_M3_signed','M2_to_M3_temporal_L1']
        fields+=['delta_'+p for p in PARTS]
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
        for i,k in enumerate(keys):
            row=dict(zip(KEY,k))
            row.update(M3_QP=sum(q3[k+(s,)] for s in range(1,37)),M4_QP=sum(q4[k+(s,)] for s in range(1,37)),
                       M3_to_M4_signed=float(spatial[i].sum()),
                       M3_to_M4_temporal_L1=float(np.abs(spatial[i]).sum()),
                       M2_to_M3_signed=float(d32[i].sum()),
                       M2_to_M3_temporal_L1=float(np.abs(d32[i].sum(axis=1)).sum()))
            row.update({'delta_'+p:float(v) for p,v in zip(PARTS,d43[i].sum(axis=0))})
            w.writerow(row)
    print(json.dumps({k:result[k] for k in ('M4_minus_M3_per_m','M3_minus_M2_per_m','ratio_absolute_sequential_increments','spacetime_L1_total_delta_M4_M3','cancellation_factor','regions')},ensure_ascii=False,indent=2))


if __name__=='__main__':
    main(*sys.argv[1:])
