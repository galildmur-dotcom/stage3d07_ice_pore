#!/usr/bin/env python3
"""P10IL: independent equal-time-grid M1/M2 signed-4D spatial comparison.

Read-only for original evidence; emits compact derived JSON and 1200-bin CSV.
No FEM, no geometric finite differences, no reconstructed time grid.
"""
import argparse
from collections import defaultdict
import csv
import json
import math
from pathlib import Path

PARTS=('mech_explicit_per_m','mech_equilibrium_per_m','mech_history_per_m',
       'thermal_mass_per_m','thermal_diffusion_per_m','thermal_robin_per_m')


def need(ok,msg):
    if not ok:raise ValueError('P10IL_STOP: '+msg)


def load_4d(path,mesh,dt=25):
    spatial=defaultdict(lambda:[0.]*6)
    spatial_qp=defaultdict(int)
    by4d={}
    bounds={}
    with path.open(newline='',encoding='utf-8-sig') as inp:
        for r in csv.DictReader(inp):
            need(r['mesh']==mesh and r['mode']=='R' and r['functional']=='jpeak',
                 'wrong mesh/physics')
            steps=900//dt
            n=int(r['step']);need(1<=n<=steps and int(r['time_start_s'])==dt*(n-1)
                             and int(r['time_end_s'])==dt*n,'wrong time grid')
            if r['region']=='TOP_ROBIN':
                continue
            need(r['region']=='VOLUME','unknown region')
            key=tuple(int(r[x]) for x in ('radial_bin','mu_bin','phi_bin'))
            need(all(0<=v<lim for v,lim in zip(key,(10,10,12))), 'wrong bin')
            coord=tuple(r[x] for x in ('r_lower_mm','r_upper_mm','theta_lower_rad',
                                        'theta_upper_rad','phi_lower_rad','phi_upper_rad'))
            if key in bounds:need(bounds[key]==coord,'physical-bin bounds drift')
            bounds[key]=coord
            tkey=(*key,n)
            need(tkey not in by4d,'duplicate space-time bin')
            vals=tuple(float(r[x]) for x in PARTS)
            need(all(math.isfinite(v) for v in vals),'nonfinite signed part')
            by4d[tkey]=vals
            spatial[key]=[a+b for a,b in zip(spatial[key],vals)]
            spatial_qp[key]+=int(r['mechanical_qp'])
    need(len(by4d)==1200*(900//dt) and len(spatial)==1200,
         'incomplete full 4D grid')
    return spatial,by4d,bounds,spatial_qp


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--m1',type=Path,required=True)
    p.add_argument('--m2',type=Path,required=True)
    p.add_argument('--m1-dt36',type=Path)
    p.add_argument('--source-kappa',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    args=p.parse_args()
    a,a4,ab,aq=load_4d(args.m1,'M1')
    b,b4,bb,bq=load_4d(args.m2,'M2')
    need(ab==bb,'physical coordinate partitions differ')
    previous=None
    if args.m1_dt36:
        previous,_,pb,_=load_4d(args.m1_dt36,'M1',36)
        need(pb==ab,'M1 25/36 spatial-bin bounds mismatch')
    kappa={}
    with args.source_kappa.open(newline='',encoding='utf-8-sig') as inp:
        for r in csv.DictReader(inp):
            key=tuple(int(r[x]) for x in ('radial_bin','mu_bin','phi_bin'))
            kappa[key]=float(r['kappa25_primary_for_M2_source_only'])
    need(len(kappa)==1200,'not original 1200-bin P10HA kappa')
    indicators={'all':lambda x:True,
                'polar_supported':lambda x:x[0]<=4 and x[1] in (0,9),
                'north_supported':lambda x:x[0]<=4 and x[1]==9,
                'south_supported':lambda x:x[0]<=4 and x[1]==0,
                'high_kappa_source':lambda x:kappa[x]>=.8}
    rows=[]
    for k in sorted(a):
        m1=sum(a[k]);m2=sum(b[k]);delta=m2-m1
        row={'radial_bin':k[0],'mu_bin':k[1],'phi_bin':k[2],
             'kappa25_source':kappa[k], 'M1_mechanical_QP':aq[k],
             'M2_mechanical_QP':bq[k],
             'M1_total_per_m':m1,'M2_total_per_m':m2,'M2_minus_M1_total_per_m':delta}
        if previous is not None:
            change=abs(sum(a[k])-sum(previous[k]))
            row['M1_dt36_to25_abs_total_per_m']=change
            row['M2_M1_abs_over_M1_temporal_proxy']=(abs(delta)/change if change else None)
        for i,col in enumerate(PARTS):
            row['M1_'+col]=a[k][i]
            row['M2_'+col]=b[k][i]
            row['M2_minus_M1_'+col]=b[k][i]-a[k][i]
        rows.append(row)
    regions={}
    for name,select in indicators.items():
        chosen=[k for k in a if select(k)]
        delta=[sum(b[k])-sum(a[k]) for k in chosen]
        differences=[sum(b[k][i]-a[k][i] for k in chosen) for i in range(6)]
        l1=sum(abs(v) for v in delta)
        regions[name]={'bins':len(chosen),'M1_total':sum(sum(a[k]) for k in chosen),
                       'M2_total':sum(sum(b[k]) for k in chosen),
                       'signed_difference':sum(delta),'spatial_L1_difference':l1,
                       'signed_parts_difference':dict(zip(PARTS,differences)),
                       'M1_mechanical_QP':sum(aq[k] for k in chosen),
                       'M2_mechanical_QP':sum(bq[k] for k in chosen)}
        if previous is not None:
            instability=sum(abs(sum(a[k])-sum(previous[k])) for k in chosen)
            signal=regions[name]['spatial_L1_difference']
            regions[name]['M1_dt36_to25_spatial_L1_proxy']=instability
            regions[name]['M2_M1_spatial_L1_to_M1_time_proxy_ratio']=(
                signal/instability if instability else None)
            regions[name]['bins_M2_M1_above_5x_M1_time_proxy']=sum(
                abs(sum(b[k])-sum(a[k]))>5*abs(sum(a[k])-sum(previous[k]))
                for k in chosen)
    temporal_4d_l1=sum(abs(sum(b4[k])-sum(a4[k])) for k in a4)
    need(abs(regions['all']['signed_difference']-(-0.0689550239165))<2e-8,
         'global M1 to M2 closure')
    summary={'protocol':'P10IL_M1_M2_EQUAL_DT25_SIGNED4D_INDEPENDENT',
             'time_bins':36,'spatial_bins':1200,'full4d_bins':43200,
             'strict_same_spatial_time_bounds':True,
             'regions':regions,'full4d_L1_difference':temporal_4d_l1,
             'note':'No claim of local temporal convergence; M2 dt36 missing.'}
    args.out.mkdir(parents=True,exist_ok=True)
    (args.out/'P10IL_COMPARE.json').write_text(json.dumps(summary,indent=2)+'\n')
    with (args.out/'P10IL_M1_M2_1200_BINS.csv').open('w',newline='') as out:
        w=csv.DictWriter(out,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    print(json.dumps(summary,indent=2))


if __name__=='__main__':main()
