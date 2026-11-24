#!/usr/bin/env python3
"""P10JM: empirically transfer M4 polar Veff response to source-only M5 C2 h5/h4."""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path

import numpy as np
from p10iu_continuous_m4 import Field, rows, C, R
from p10ix_c2_m4_repair_preflight import local_patch

M3_SHA='3d6ce765dced7d146ef5228be3b0a8210b4466ed08a0c9f5a20d1917dc2a8c3a'
M4_SHA='a9fff03ca56b92c1d250e834bd116afee3cb0af1e846b848ef8215fb245e755c'
P10HA_SHA='98bc99af9783e14f7800f08ecd04fc6bee8093d0490b359e3a024f4c6c4566a3'
P10IT_SHA='e31c0b72946391fa4b36572292657197ecb8f31b315403128d0d2c70fbfc3c06'
P10JL_SHA='0c5c475ff1986359d28fd0c4539353b9af5f221069f346008cac7be4ac149a61'

OLD_GENERIC=.1435943053641514
OLD_N=.18
OLD_S=.12998093714900827
OLD_WALL=.10
WALL_DIR=np.array([.4179124587379918,.7804360648608903,-.46504701428566836])
OLD_ACTUAL={'N':.6481194486487811,'S':.6650866315155264}
TARGET=.65


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def patch_values(field,sign):
    selected=np.array([k[0]<=4 and k[1]==(9 if sign>0 else 0) for k in field.keys])
    p=field.center_points[selected]
    taper=np.array([field.taper(d,xyz[2]) for d,xyz in zip(field.dmm[selected],field.xyz[selected])])
    patch=np.array([local_patch(point,WALL_DIR) for point in p])
    return selected,taper,patch


def ratio(field,selected,taper,wall,delta,weights,generic):
    k=field.center_kappa[selected]
    logsize=generic*k+delta*taper+OLD_WALL*wall
    return float(np.average(np.exp(-3*logsize),weights=weights))


def evaluate(field,p,generic,dN,dS):
    v=p-C
    radius=np.linalg.norm(v)
    assert radius >=R-1e-10
    mu=v[2]/radius
    dmm=max(0.,(radius-R)*1000)
    k=field.kappa(p)
    taper=field.taper(dmm,mu)
    wall=local_patch(p,WALL_DIR)
    delta=dN if mu>=0 else dS
    h=math.exp(-generic*k-delta*taper-OLD_WALL*wall)
    return k,taper,wall,h


def main():
    ap=argparse.ArgumentParser()
    for name in ('ha','it','jl','out'):
        ap.add_argument('--'+name,type=Path,required=True)
    args=ap.parse_args()
    assert sha(args.ha)==P10HA_SHA and sha(args.it)==P10IT_SHA and sha(args.jl)==P10JL_SHA
    a=rows(args.ha)
    old=Field(a,rows(args.it),'0.1')
    jlrows=rows(args.jl)
    new=Field(a,jlrows,'0.1')
    # P10IU's legacy Field defaults to M3_QP. For the M4→M5 transfer
    # the independent physical support MUST use M4_QP instead.
    jlmap={tuple(int(r[k]) for k in ('radial_bin','mu_bin','phi_bin')):r for r in jlrows}
    new.qp=np.array([int(jlmap[k]['M4_QP']) for k in new.keys])
    assert np.all(new.qp>0)
    assert old.keys==new.keys
    assert len(new.keys)==1200
    generic=OLD_GENERIC  # same generic log size as empirically accepted M4
    sides={}
    ds={}
    for name,sign,dold in (('N',1,OLD_N),('S',-1,OLD_S)):
        sel,taper,wall=patch_values(old,sign)
        sel2,taper2,wall2=patch_values(new,sign)
        assert np.array_equal(sel,sel2) and np.max(abs(taper-taper2))<1e-12
        old_weight=old.qp[sel].astype(float)
        new_weight=new.qp[sel].astype(float)
        oldproxy=ratio(old,sel,taper,wall,dold,old_weight,OLD_GENERIC)
        actual=OLD_ACTUAL[name]
        transfer=actual/oldproxy

        def predict(patch):
            return transfer*ratio(new,sel2,taper2,wall2,patch,new_weight,generic)
        baseline=predict(0.)
        low,high=0.,.90
        if baseline<=TARGET:
            chosen=0.
            reached=False
        else:
            assert predict(high)<=TARGET
            for _ in range(60):
                mid=(low+high)/2
                if predict(mid)>TARGET:low=mid
                else:high=mid
            chosen=(low+high)/2
            reached=True
        ds[name]=chosen
        scenarios={}
        for target in (.50,.65,.75):
            if baseline<=target:
                scenarios[str(target)]={'patch':0.,'predicted_actual_proxy':baseline}
                continue
            lo,hi=0.,.90
            if predict(hi)>target:
                scenarios[str(target)]={'patch':None,'predicted_actual_proxy_at_high':predict(hi)}
                continue
            for _ in range(60):
                mid=(lo+hi)/2
                if predict(mid)>target:lo=mid
                else:hi=mid
            xx=(lo+hi)/2
            scenarios[str(target)]={'patch':xx,'predicted_actual_proxy':predict(xx)}
        sides[name]={'supported_bins':int(sel.sum()),'M3_QP':int(old_weight.sum()),
                     'M4_QP':int(new_weight.sum()),
                     'previous_M4_M3_actual_Veff_729':actual,
                     'previous_M4_M3_center_cube_proxy':oldproxy,
                     'empirical_transfer_factor':transfer,
                     'new_M5_M4_center_cube_proxy_unpatched_transfer':baseline,
                     'new_selected_polar_logsize_patch':chosen,
                     'new_empirical_calibrated_prediction':predict(chosen),
                     'nominal_target_reached':reached,
                     'sensitivity_scenarios':scenarios,
                     'new_polar_kappa_qp_weighted':float(np.average(new.center_kappa[sel2],weights=new_weight)),
                     'old_polar_kappa_qp_weighted':float(np.average(old.center_kappa[sel],weights=old_weight))}
    samples=[]
    for name,sign in (('N',1),('S',-1)):
        for dmm in (0.,.02,.05,.1,.25,.3,.5,.7,1.,2.,5.):
            for absmu in (.3,.6,.7,.8,.95,1.):
                for phi in (0.,math.pi/2,math.pi-1e-7):
                    mu=sign*absmu
                    direction=np.array([math.sqrt(1-mu*mu)*math.cos(phi),
                                        math.sqrt(1-mu*mu)*math.sin(phi),mu])
                    p=C+(R+dmm*.001)*direction
                    k,t,w,h=evaluate(new,p,generic,ds['N'],ds['S'])
                    samples.append({'side':name,'d_mm':dmm,'mu':mu,'phi':phi,
                                    'kappa':k,'polar_taper':t,'wall_patch':w,
                                    'h5_over_h4_source_proxy':h,'cube_proxy':h**3})
    seam=0.;pole=0.
    for dmm in (0.,.03,.5,2.):
        for mu in (-.95,-.8,-.55,.55,.8,.95):
            def p(phi):
                return C+(R+.001*dmm)*np.array([math.sqrt(1-mu*mu)*math.cos(phi),
                    math.sqrt(1-mu*mu)*math.sin(phi),mu])
            seam=max(seam,max(abs(x-y) for x,y in zip(
                evaluate(new,p(-math.pi),generic,ds['N'],ds['S']),
                evaluate(new,p(math.pi),generic,ds['N'],ds['S']))))
        for sign in (-1,1):
            point=C+(R+.001*dmm)*np.array([0.,0.,sign])
            pole=max(pole,max(abs(x-y) for x,y in zip(
                evaluate(new,point,generic,ds['N'],ds['S']),
                evaluate(new,point.copy(),generic,ds['N'],ds['S']))))
    assert seam<1e-12 and pole<1e-12
    assert all(0<=r['kappa']<=1 and 0<r['h5_over_h4_source_proxy']<=1 for r in samples)
    qa={'protocol':'P10JM_M5_EMPIRICAL_C2_SIZE_FIELD_SOURCE_ONLY',
        'status':'PASS_SOURCE_ONLY_NO_M5_MESH_NO_FEM',
        'source_hashes':{'P10HA':sha(args.ha),'P10IT':sha(args.it),'P10JL':sha(args.jl)},
        'base_mesh_sha':{'M3':M3_SHA,'M4':M4_SHA},
        'beta':.10,'generic_logsize_delta':generic,
        'retained_P10IX_wall_C2_logsize_max':OLD_WALL,
        'wall_direction':WALL_DIR.tolist(),
        'target_polar_actual_Veff_ratio_M5_over_M4_proxy':TARGET,
        'north_south':sides,
        'sample_count':len(samples),
        'sample_min_max_h5_h4':[min(r['h5_over_h4_source_proxy'] for r in samples),
                                max(r['h5_over_h4_source_proxy'] for r in samples)],
        'seam_max_abs':seam,'pole_max_abs':pole,
        'D029_actual_M5_M4_Veff':'UNKNOWN_UNTIL_NATIVE_GMSH',
        'D031_all_Tet10_M5':'UNKNOWN_UNTIL_NATIVE_GMSH',
        'caveat':'One observed M4/M3 response per side; transferred cube proxy is not validated prediction; no FEM or new Gmsh performed.',
        'next':'distinct guarded P10JN M5 mesh-only native Gmsh followed by independent curved Tet10 D031 and supported polar actual Veff D029'}
    args.out.mkdir(parents=True,exist_ok=True)
    (args.out/'P10JM_M5_SIZE_FIELD_QA.json').write_text(json.dumps(qa,ensure_ascii=False,indent=2)+'\n')
    with (args.out/'P10JM_M5_SIZE_FIELD_SAMPLES.csv').open('w',newline='') as f:
        wr=csv.DictWriter(f,fieldnames=list(samples[0]));wr.writeheader();wr.writerows(samples)
    print(json.dumps(qa,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
