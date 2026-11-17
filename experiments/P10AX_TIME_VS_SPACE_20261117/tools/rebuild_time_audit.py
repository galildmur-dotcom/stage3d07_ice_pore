#!/usr/bin/env python3
"""P10AX/P10Y: temporal versus spatial cancellation in 3D ice pore shape gradient.

Uses only Python standard library, with SHA identity check of the P10AX 216-row CSV.
The P10Y audit CSVs are checked if supplied from a full Stage3D07 checkout.
See documentation for interpretation: step terms contribute to J(T=900s), not J(t).
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import math
from pathlib import Path

SHA = '4ff42a2cc44eb033053766c3041ac52e6210dd2c'
SOURCE = 'experiments/P10AX_H1_COMPLETED_SPATIOTEMPORAL_20261116/derived/P10AX_216_VERIFIED_STEP_COMPONENTS.csv'
AUDITS = {
    'H4': ('experiments/P10Y_H4_H4W2_COMPARE_20261112/input/P10Y_H4_PARTITION_AUDIT.csv', 'H4'),
    'W2B2': ('experiments/P10Y_H4W2_R_20261112/data/P10Y_PARTITION_AUDIT.csv', 'H4W2'),
    'W4B2': ('experiments/P10Y_W4_PAIR_ANALYSIS_20261117/input/W4B2_P10Y_PARTITION_AUDIT.csv', 'H4W4B2'),
    'W4B20': ('experiments/P10Y_W4_PAIR_ANALYSIS_20261117/input/W4B20_P10Y_PARTITION_AUDIT.csv', 'H4W4B20_P10AB'),
}
PAIRS = (('H4', 'W2B2', 'surface_first'),
         ('W2B2', 'W4B2', 'surface_second'),
         ('W4B2', 'W4B20', 'bulk_at_W4'))
FUNCTIONALS = ('j6', 'jpeak', 'jen')
COLS = {'explicit': 'explicit_per_m', 'equilibrium': 'equilibrium_per_m',
        'history': 'history_per_m', 'mechanical': 'mechanical_step_per_m'}
AUDIT_COLS = {'explicit':'global_explicit_objective_per_m',
              'equilibrium':'global_equilibrium_residual_per_m',
              'history':'global_internal_history_per_m',
              'mechanical':'global_mechanical_per_m'}

def read_csv(path):
    with path.open(newline='', encoding='utf-8-sig') as f:
        return list(csv.DictReader(f))

def write_csv(path, records):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=list(records[0]), lineterminator='\n')
        writer.writeheader()
        writer.writerows(records)

def fmt(v):
    return format(v, '.16e')

def run(repo, source, outdir, check_audits):
    data = source.read_bytes()
    blob_sha = hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()
    if blob_sha != SHA:
        raise ValueError(f'P10AX blob SHA mismatch: {blob_sha}, expected {SHA}')
    full = read_csv(source)
    if len(full) != 216:
        raise ValueError(f'Expected 216 rows, found {len(full)}')
    index = {}
    for r in full:
        key = r['mesh_id'],r['functional'],int(r['time_step'])
        if key in index: raise ValueError(f'Duplicate input key: {key}')
        index[key] = r
        if int(r['time_s']) != int(r['time_step'])*150:
            raise ValueError('Time grid mismatch '+str(key))
        component_sum = math.fsum(float(r[COLS[x]]) for x in ('explicit','equilibrium','history'))
        if abs(component_sum-float(r[COLS['mechanical']]))>1.e-11:
            raise ValueError('Component sum mismatch '+str(key))
    assert len(index)==216
    assert len({(k[0],k[1]) for k in index})==36
    steps, summary, parity = [], [], []
    for mesh,(apath,expected_name) in AUDITS.items():
        path=repo/apath
        if not path.exists():
            if check_audits: raise FileNotFoundError(path)
            continue
        aud = {r['functional']:r for r in read_csv(path)}
        if len(aud)!=3:raise ValueError('Bad audit '+str(path))
        for f in FUNCTIONALS:
            r=aud[f]
            if r['mesh']!=expected_name or r['mode']!='R' or float(r['delta_um'])!=0:
                raise ValueError('Wrong audit metadata '+mesh+f)
            entry={'mesh_id':mesh,'functional':f}
            for c,field in COLS.items():
                step_sum=math.fsum(float(index[(mesh,f,i)][field]) for i in range(1,7))
                global_sum=float(r[AUDIT_COLS[c]])
                d=step_sum-global_sum
                if abs(d)>1.e-9:
                    raise ValueError(f'P10AX to P10Y global disagreement {mesh} {f} {c}: {d}')
                entry[c+'_P10AX_sum_per_m']=fmt(step_sum)
                entry[c+'_P10Y_global_per_m']=fmt(global_sum)
                entry[c+'_P10AX_minus_P10Y_per_m']=fmt(d)
            parity.append(entry)
    for a,b,axis in PAIRS:
        for f in FUNCTIONALS:
            pair=a+'_to_'+b
            signed={k:[] for k in COLS}
            for i in range(1,7):
                x=index[(a,f,i)];y=index[(b,f,i)]
                row={'pair':pair,'refinement_axis':axis,'functional':f,
                     'time_step':i,'time_s':i*150,'source_origin_from':x['origin'], 'source_origin_to':y['origin']}
                for c,field in COLS.items():
                    av,bv=float(x[field]),float(y[field]);d=bv-av
                    row[c+'_from_per_m']=fmt(av)
                    row[c+'_to_per_m']=fmt(bv)
                    row['delta_'+c+'_per_m']=fmt(d)
                    signed[c].append(d)
                den=abs(signed['mechanical'][-1])
                row['local_step_component_cancellation']=fmt(math.fsum(abs(signed[k][-1]) for k in ('explicit','equilibrium','history'))/den) if den>0 else ''
                steps.append(row)
            net=math.fsum(signed['mechanical']); tL1=math.fsum(abs(v) for v in signed['mechanical'])
            if abs(math.fsum(math.fsum(signed[c]) for c in ('explicit','equilibrium','history'))-net)>1.e-10:
                raise ValueError('Pair component imbalance '+pair+f)
            largest=max(range(6),key=lambda i:abs(signed['mechanical'][i]))
            signs=''.join('+' if v>0 else '-' if v<0 else '0' for v in signed['mechanical'])
            last3=math.fsum(signed['mechanical'][3:])
            s={'pair':pair,'refinement_axis':axis,'functional':f,
               'global_delta_mechanical_per_m':fmt(net),
               'L1_time_mechanical_per_m':fmt(tL1),
               'time_cancellation_ratio':fmt(tL1/abs(net)),
               'sum_abs_time_and_components_per_m':fmt(math.fsum(abs(v) for c in ('explicit','equilibrium','history') for v in signed[c])),
               'joint_time_component_cancellation_ratio':fmt(math.fsum(abs(v) for c in ('explicit','equilibrium','history') for v in signed[c])/abs(net)),
               'sign_pattern':signs,'max_abs_time_step':largest+1,'max_abs_time_s':150*(largest+1),
               'late_600_900_signed_fraction':fmt(last3/net),
               'late_750_900_signed_fraction':fmt(math.fsum(signed['mechanical'][4:])/net)}
            for c in COLS:
                s['global_delta_'+c+'_per_m']=fmt(math.fsum(signed[c]))
                s['L1_time_'+c+'_per_m']=fmt(math.fsum(abs(v) for v in signed[c]))
            summary.append(s)
    assert len(steps)==54 and len(summary)==9
    write_csv(outdir/'P10AX_54_TIME_STEP_INTERMESH_COMPONENTS.csv',steps)
    write_csv(outdir/'P10AX_9_TIME_CANCELLATION_METRICS.csv',summary)
    if parity: write_csv(outdir/'P10AX_12_P10Y_GLOBAL_PARITY.csv',parity)
    print('P10AX_TIME_AUDIT_OK steps=54 comparisons=9 parity='+str(len(parity)))
    for s in summary:
        if s['functional']=='jpeak':
            print(s['pair'], 'net=',s['global_delta_mechanical_per_m'],
                  'Kt=',s['time_cancellation_ratio'],'signs=',s['sign_pattern'])

if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--repo',type=Path,default=Path(__file__).resolve().parents[3])
    p.add_argument('--source',type=Path)
    p.add_argument('--outdir',type=Path)
    p.add_argument('--skip-audits',action='store_true',help='Offline limited test only; normal Git-based run verifies P10Y audits')
    args=p.parse_args()
    src=args.source or args.repo/SOURCE
    out=args.outdir or Path(__file__).resolve().parents[1]/'derived'
    run(args.repo,src,out,not args.skip_audits)
