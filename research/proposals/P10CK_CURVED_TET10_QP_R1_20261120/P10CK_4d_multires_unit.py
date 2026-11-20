#!/usr/bin/env python3
"""Unit-only signed 4D partition and independent 2D mechanical P10BA replay.

No physical (d,mu,phi,t) data are synthesized or claimed: 4D input is synthetic.
The optional t=900 s replay uses only the physically measured (d,mu) projection.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import csv
import hashlib
import math
from pathlib import Path
import random

COMPONENTS=('mechanical_explicit','mechanical_equilibrium','mechanical_edv_history',
            'thermal_mass','thermal_diffusion','thermal_robin')
SOURCES={
 'H4W4B2':'219b237e42305f1e4db3089f6501bdd59034dc664f9eee83c5bdc0888e15d447',
 'H4W4B20':'3803ed656045384727109952c9331c4e073e4cec9f718a3a7770ecf3a28bd1be',
 'H4W5B2':'8ad499250082e919942e8ea105ed0b21463cfd5083085af3f004ee293294c11c',
}


def sha256(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def near(a,b,scale=1.):
    return abs(a-b)<=8.e-13*max(scale,abs(a),abs(b),1.e-14)


def unit4d():
    rng=random.Random(20261120)
    bins=defaultdict(lambda:[[] for _ in COMPONENTS])
    direct=[[] for _ in COMPONENTS]
    for r in range(20):
        for mu in range(10):
            for phi in range(12):
                for step in range(6):
                    # Deterministic alternating signed test, not an ice field.
                    vals=[(((-1.)**(r+j))*rng.random()+.03*math.sin((mu+1)*(phi+1)))
                          *(2.e-5/(j+1)) for j in range(6)]
                    key=(r,mu,phi,step)
                    for j,v in enumerate(vals):bins[key][j].append(v);direct[j].append(v)
    assert len(bins)==20*10*12*6
    reference=[math.fsum(d) for d in direct]
    levels=[('fine',lambda k:k),
            ('radial_2',lambda k:(0 if k[0]<10 else 1,k[1],k[2],k[3])),
            ('radial_1',lambda k:(0,k[1],k[2],k[3])),
            ('phi_integrated',lambda k:(k[0],k[1],0,k[3])),
            ('time_integrated',lambda k:(k[0],k[1],k[2],0)),
            ('radial_phi_time_integrated',lambda k:(0,k[1],0,0)),
            ('all_integrated',lambda k:(0,0,0,0))]
    report=['P10CK_4D_UNIT=SYNTHETIC_ONLY','N_SPATIAL_TEMPORAL_BINS='+str(len(bins)),
            'N_TIME_STEPS=6','N_R=20','N_MU=10','N_PHI=12',
            'COMPONENTS='+','.join(COMPONENTS)]
    for name,keyfun in levels:
        grouped=defaultdict(lambda:[[] for _ in COMPONENTS])
        for key,vec in bins.items():
            newkey=keyfun(key)
            for j in range(6):grouped[newkey][j].extend(vec[j])
        totals=[math.fsum(math.fsum(vec[j]) for vec in grouped.values()) for j in range(6)]
        assert all(near(a,b) for a,b in zip(totals,reference)),name
        report.append(name.upper()+'_KEYS='+str(len(grouped)))
        report.append(name.upper()+'_MAX_ABS_COMPONENT_CLOSURE='+str(max(abs(a-b) for a,b in zip(totals,reference))))
    # Boundary and outside support are separately tracked, never silently folded
    # into a 4D volumetric cell.
    boundary=[-.001,0.,.002,.0001,-.0002,.0005]
    outside=[.0002,-.0003,.0001,.0004,0.,-.0001]
    physical_like_total=[math.fsum((reference[j],boundary[j],outside[j])) for j in range(6)]
    assert near(math.fsum(physical_like_total),
                math.fsum(reference+boundary+outside))
    mechanical=math.fsum(physical_like_total[:3])
    thermal=math.fsum(physical_like_total[3:])
    assert near(mechanical+thermal,math.fsum(physical_like_total))
    report.extend(['BOUNDARY_COMPONENTS_TRACKED=6','OUTSIDE_SUPPORT_COMPONENTS_TRACKED=6',
                   'MECHANICAL_THERMAL_SPLIT_SUM=PASS',
                   'QUADRATURE_OR_ADJOINT_FEM=NOT_EXECUTED',
                   'P10CK_4D_MULTIRES_SIGNED_UNIT=PASS'])
    return report


def real2d_replay(directory):
    report=['P10CK_P10BA_REPLAY=PHYSICAL_2D_PROJECTION_t900_ONLY',
            'PHI=INTEGRATED_IN_SOURCE','TIME=FINAL_STEP_ONLY',
            'THERMAL_COMPONENTS=UNAVAILABLE_NOT_ZERO']
    for mesh,sha in SOURCES.items():
        p=directory/(mesh+'_P10BA_QP_POLAR_RADIAL.csv')
        assert sha256(p)==sha,mesh+' SHA fail'
        data={}
        with p.open(newline='',encoding='utf-8-sig') as f:
            for row in csv.DictReader(f):
                if int(row['time_step'])!=6 or float(row['time_s'])!=900.:continue
                k=(round(float(row['radial_lower_mm']),8),int(row['polar_band']))
                assert k not in data
                vals=(float(row['explicit_per_m']),float(row['equilibrium_per_m']),
                      float(row['history_per_m']))
                total=float(row['total_mechanical_per_m'])
                assert near(math.fsum(vals),total,max(1.,sum(abs(x) for x in vals)))
                data[k]=vals
        assert len(data)==200
        fine=[math.fsum(x[j] for x in data.values()) for j in range(3)]
        for shell in (2,1):
            grouped=defaultdict(lambda:[[] for _ in range(3)])
            for (r,mu),vec in data.items():
                k=(0 if shell==1 or r<.05 else 1,mu)
                for j in range(3):grouped[k][j].append(vec[j])
            coarse=[math.fsum(math.fsum(g[j]) for g in grouped.values()) for j in range(3)]
            assert all(near(a,b,max(1.,abs(a))) for a,b in zip(coarse,fine))
            report.append(mesh+'_SIGNED_RADIAL_'+str(shell)+'SHELL_3MECH_COMPONENTS=PASS')
        report.append(mesh+'_MECHANICAL_EXPLICIT_SUM_PER_M='+repr(fine[0]))
        report.append(mesh+'_MECHANICAL_EQUILIBRIUM_SUM_PER_M='+repr(fine[1]))
        report.append(mesh+'_MECHANICAL_EDV_HISTORY_SUM_PER_M='+repr(fine[2]))
        report.append(mesh+'_MECHANICAL_SUM_PER_M='+repr(math.fsum(fine)))
    report.append('P10CK_P10BA_MECHANICAL_SIGNED_REPLAY=PASS')
    return report


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--reference-dir',type=Path,required=True)
    p.add_argument('--output',type=Path)
    a=p.parse_args()
    lines=unit4d()+real2d_replay(a.reference_dir)
    lines+=['PHYSICAL_FEM_RUNS=0','SPATIAL_CONVERGENCE_PROVEN=NO',
            'REAL_4D_MECHANICAL_THERMAL_FIELD=NOT_YET_EXPORTED',
            'RESULT=P10CK_4D_MULTIRES_UNIT_AND_2D_MECHANICAL_REPLAY_OK_NO_FEM']
    print('\n'.join(lines))
    if a.output:
        a.output.parent.mkdir(parents=True,exist_ok=True)
        a.output.write_text('\n'.join(lines)+'\n',encoding='utf-8')
    return 0


if __name__=='__main__':raise SystemExit(main())
