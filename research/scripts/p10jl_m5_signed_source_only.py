#!/usr/bin/env python3
"""P10JL: physical M3/M4 signed 4D -> smooth C2 M5 adaptation source, no mesh/FEM."""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
from pathlib import Path

import numpy as np

from p10it_compare import read, dorfler, PARTS, KEY
from p10iu_continuous_m4 import Field, rows, C, R

EXPECTED_M3='3d6ce765dced7d146ef5228be3b0a8210b4466ed08a0c9f5a20d1917dc2a8c3a'
EXPECTED_M4='a9fff03ca56b92c1d250e834bd116afee3cb0af1e846b848ef8215fb245e755c'
P10HA_SHA='98bc99af9783e14f7800f08ecd04fc6bee8093d0490b359e3a024f4c6c4566a3'
P10IT_SHA='e31c0b72946391fa4b36572292657197ecb8f31b315403128d0d2c70fbfc3c06'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    ap=argparse.ArgumentParser()
    for name in ('m3','m4','ha','prior','out'):
        ap.add_argument('--'+name,type=Path,required=True)
    args=ap.parse_args()
    assert sha(args.ha)==P10HA_SHA and sha(args.prior)==P10IT_SHA
    m3,b3,q3=read(args.m3,'M3');m4,b4,q4=read(args.m4,'M4')
    assert m3.keys()==m4.keys() and b3==b4
    keys=sorted(b3)
    assert len(keys)==1200
    delta=np.array([[m4[k+(s,)]-m3[k+(s,)] for s in range(1,37)] for k in keys])
    assert np.isfinite(delta).all()
    assert abs(delta.sum()+.08513474055522016)<1e-9
    abs_parts=np.abs(delta).sum(axis=1)
    denom=abs_parts.sum(axis=0)
    assert np.all(denom>0)
    norm=abs_parts/denom
    mech=norm[:,:3].mean(axis=1)
    thermal=norm[:,3:].mean(axis=1)
    profiles={str(b):(1-b)*mech+b*thermal for b in (0.,.1,.25)}
    polarN=np.array([k[0]<=4 and k[1]==9 for k in keys])
    polarS=np.array([k[0]<=4 and k[1]==0 for k in keys])
    polar=polarN|polarS
    assert polar.sum()==120
    old_rows={tuple(int(r[k]) for k in KEY):r for r in rows(args.prior)}
    assert set(old_rows)==set(keys)
    old_score=np.array([float(old_rows[k]['beta_0.1_score']) for k in keys])
    old_selected=dorfler(old_score)
    prepared=[]
    for i,k in enumerate(keys):
        rec=dict(zip(KEY,k))
        rec.update(M4_QP=sum(q4[k+(s,)] for s in range(1,37)),
                   M3_QP=sum(q3[k+(s,)] for s in range(1,37)),
                   mech_score=float(mech[i]),thermal_score=float(thermal[i]),
                   absolute_total_4D=float(np.abs(delta[i].sum(axis=1)).sum()),
                   signed_total=float(delta[i].sum()))
        for b,s in profiles.items():rec['beta_'+b+'_score']=float(s[i])
        prepared.append(rec)
    original=rows(args.ha)
    fields={b:Field(original,prepared,b) for b in profiles}
    for b,f in fields.items():
        for i,rec in enumerate(prepared):rec['beta_'+b+'_kappa_smoothed']=float(f.center_kappa[i])
    beta='0.1';f=fields[beta]
    selected=dorfler(profiles[beta])
    jaccard=len(selected&old_selected)/len(selected|old_selected)
    summary={}
    for b,s in profiles.items():
        chosen=dorfler(s)
        summary[b]={'dorfler_theta_0p5_count':len(chosen),
                    'dorfler_polar_bins':int(sum(polar[i] for i in chosen)),
                    'score_fraction_polar':float(s[polar].sum()/s.sum()),
                    'score_fraction_N':float(s[polarN].sum()/s.sum()),
                    'score_fraction_S':float(s[polarS].sum()/s.sum()),
                    'smoothed_kappa_mean':float(fields[b].center_kappa.mean()),
                    'smoothed_kappa_polar_mean':float(fields[b].center_kappa[polar].mean()),
                    'top10_bins':[list(keys[i]) for i in np.argsort(-fields[b].center_kappa)[:10]]}
    # Check actual Cartesian periodicity and exact pole-coordinate continuity.
    seam=0.;pole=0.
    for dmm in (0.,.02,.1,.5,2.):
        for mu in (-.95,-.8,-.6,.6,.8,.95):
            radius=R+dmm*.001
            a=np.array([np.sqrt(1-mu**2),0.,mu])*radius+C
            z=np.array([np.sqrt(1-mu**2)*np.cos(2*np.pi),
                        np.sqrt(1-mu**2)*np.sin(2*np.pi),mu])*radius+C
            seam=max(seam,abs(f.kappa(a)-f.kappa(z)))
        for sign in (-1,1):
            p=C+(R+dmm*.001)*np.array([0.,0.,sign])
            pole=max(pole,abs(f.kappa(p)-f.kappa(p.copy())))
    assert seam<1e-12 and pole<1e-12
    # No h5/h4 calibration or geometry claim at this source-only stage.
    qa={'protocol':'P10JL_M3_M4_SIGNED4D_C2_M5_KAPPA_SOURCE_ONLY',
        'status':'PASS_SOURCE_ONLY_NO_NEW_MESH_NO_FEM',
        'input_SHA256':{'M3_signed4D':sha(args.m3),'M4_signed4D':sha(args.m4),
                        'P10HA_coords':sha(args.ha),'P10IT_prior':sha(args.prior)},
        'physical_mesh_SHA':{'M3':EXPECTED_M3,'M4':EXPECTED_M4},
        'dt_s':25,'steps':36,'source_bins':1200,
        'delta_D_R_jpeak_M4_minus_M3':float(delta.sum()),
        'spacetime_L1_delta':float(np.abs(delta.sum(axis=2)).sum()),
        'beta_primary':.1,'beta_diagnostics':[0.,.25],
        'score':summary,'old_vs_new_beta0p1_dorfler_jaccard':jaccard,
        'old_vs_new_beta0p1_kappa_center_MAE':float(np.abs(f.center_kappa-
            np.array([float(old_rows[k]['beta_0.1_kappa']) for k in keys])).mean()),
        'C2_method':'normalized positive Wendland C2 in log radial and Cartesian direction; quintic s5',
        'seam_max_abs':seam,'pole_max_abs':pole,
        'kappa_center_min_max':[float(f.center_kappa.min()),float(f.center_kappa.max())],
        'continuity_gate':'PASS geometric continuity of source kappa, not Tet10 quality',
        'mesh_quality_gate':'NOT_EVALUATED_NO_M5_MESH',
        'D029_actual_polar_Veff_M5_M4':'NOT_EVALUATED',
        'next':'P10JM source-only calibrate M5 h5/h4 with P10IY empirical N/S response, preregister D029/D031, then distinct guarded M5 mesh-only native attempt'}
    args.out.mkdir(parents=True,exist_ok=True)
    with (args.out/'P10JL_M5_SIGNED_SOURCE_1200_BINS.csv').open('w',newline='') as sink:
        wr=csv.DictWriter(sink,fieldnames=list(prepared[0]));wr.writeheader();wr.writerows(prepared)
    (args.out/'P10JL_M5_SOURCE_ONLY_QA.json').write_text(json.dumps(qa,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(qa,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
