#!/usr/bin/env python3
"""P10KA source-only M7 incremental 20% cell-volume target, smooth C2 size."""
import csv
import hashlib
import json
import math
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from p10iu_continuous_m4 import Field, rows, C, R

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'p10ka_result'
COORD=ROOT/'P10HA_centers.csv'
SOURCE=ROOT/'p10jz_result/P10JZ_M7_PROVISIONAL_C2_1200_BINS.csv'
QA=ROOT/'p10jz_result/P10JZ_4D_LOCALIZATION_AND_M7_SOURCE_QA.json'
SH=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def size_ratio(field,p,volume_ratio=.80):
    # Smooth C² kappa is 0 outside active regions and approaches 1 in priority core.
    # This defines *incremental* M7/M6 linear size; do not compound with M6 CAD size.
    k=field.kappa(p)
    return math.exp(math.log(volume_ratio)*k/3)


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    assert json.loads(QA.read_text())['status']=='PASS_SOURCE_ONLY_NO_GMSH_NO_MESH_NO_FEM'
    a=rows(COORD);b=rows(SOURCE)
    field=Field(a,b,'0.1')
    assert len(field.keys)==1200
    theoretical={str(v):{'min_h7_h6':v**(1/3), 'max_reduction_element_volume_fraction':1-v}
                 for v in (.75,.80,.85)}
    # Actual samples of the continuous C2 field (not an empirical 3D Tet10 volume).
    sample=[]
    for dmm in (0.,.02,.05,.1,.2,.5,1.,2.,3.,5.,8.,15.):
        for mu in (-1.,-.98,-.85,-.7,-.4,0.,.4,.7,.85,.98,1.):
            for phi in (-math.pi,-math.pi/2,-1e-9,0.,math.pi/2,math.pi):
                p=C+(R+dmm*.001)*np.array([math.sqrt(max(0.,1-mu*mu))*math.cos(phi),
                       math.sqrt(max(0.,1-mu*mu))*math.sin(phi),mu])
                k=field.kappa(p)
                rr=[size_ratio(field,p,v) for v in (.75,.80,.85)]
                sample.append({'d_mm':dmm,'mu':mu,'phi':phi,'kappa_C2':k,
                               'h7_h6_volume75':rr[0],
                               'h7_h6_volume80':rr[1],
                               'h7_h6_volume85':rr[2],
                               'v7_v6_volume80_proxy':rr[1]**3})
    assert all(0<=s['kappa_C2']<=1+1e-12 for s in sample)
    assert all(.75**(1/3)-1e-12 <=s['h7_h6_volume75']<=1 for s in sample)
    assert all(.8**(1/3)-1e-12 <=s['h7_h6_volume80']<=1 for s in sample)
    seam=0.;pole=0.;grad=[]
    for dmm in (0.,.02,.1,.5,2.,5.):
        for mu in (-.98,-.7,-.4,.4,.7,.98):
            def p(phi):return C+(R+dmm*.001)*np.array([math.sqrt(1-mu*mu)*math.cos(phi),
                math.sqrt(1-mu*mu)*math.sin(phi),mu])
            seam=max(seam,abs(size_ratio(field,p(-math.pi))-size_ratio(field,p(math.pi))))
        for sign in (-1,1):
            p=C+(R+dmm*.001)*np.array([0,0,sign])
            pole=max(pole,abs(size_ratio(field,p)-size_ratio(field,p.copy())))
    assert seam<1e-12 and pole<1e-12
    # Quantify center-to-center jumps for physically adjacent source cells;
    # smoothness is geometric but this is NOT an actual new Tet10 quality check.
    kmap={key:field.center_kappa[i] for i,key in enumerate(field.keys)}
    for rr,mu,ph in field.keys:
        for neighbor in [(rr+1,mu,ph),(rr,mu+1,ph),(rr,mu,(ph+1)%12)]:
            if neighbor in kmap:
                grad.append(abs(math.exp(math.log(.8)*kmap[(rr,mu,ph)]/3)-
                                math.exp(math.log(.8)*kmap[neighbor]/3)))
    values=np.array([s['h7_h6_volume80'] for s in sample])
    heat=np.zeros((10,10))
    for (rad,polar,phi),kap in kmap.items():
        heat[rad,polar]+=math.exp(math.log(.8)*kap/3)/12
    fig,axs=plt.subplots(1,2,figsize=(12,4.6),constrained_layout=True)
    im=axs[0].imshow(heat.T,origin='lower',aspect='auto',cmap='viridis',
                     vmin=.8**(1/3),vmax=1.)
    axs[0].set_title('M7/M6 linear size: angular average per shell')
    axs[0].set_xlabel('radial shell index')
    axs[0].set_ylabel('polar zone (0=south, 9=north)')
    fig.colorbar(im,ax=axs[0],label='h7/h6')
    for v,c in ((.75,'#aa4545'),(.80,'#2365a0'),(.85,'#338052')):
        axs[1].plot(np.linspace(0,1,101),v**(np.linspace(0,1,101)/3),
                    label=f'{(1-v)*100:.0f}% max volume reduction',color=c)
    axs[1].set_xlabel('κ C² (0 = unchanged, 1 = priority maximum)')
    axs[1].set_ylabel('h7/h6')
    axs[1].set_title('Smooth incremental refinement scenarios')
    axs[1].grid(alpha=.25);axs[1].legend()
    fig.savefig(OUT/'P10KA_M7_C2_SIZE_FIELD.png',dpi=160)
    plt.close(fig)
    qa={'protocol':'P10KA_M7_INCREMENTAL_SMOOTH_C2_H7_H6_SOURCE_ONLY',
        'status':'PASS_NO_GMSH_NO_NEW_MESH_NO_FEM',
        'input_sha256':{'P10HA':SH(COORD),'P10JZ_1200':SH(SOURCE),'P10JZ_QA':SH(QA)},
        'dt_s':25,'steps':36,'source_bins':1200,
        'nominal_element_volume_reduction':.20,
        'formula':'h7/h6(x) = 0.8 ** (kappa_C2(x)/3); V7/V6 local proxy = 0.8 ** kappa_C2(x)',
        'base_reference':'incremental from accepted M6; original CAD and cumulative M6 field unchanged',
        'nominal_target_scenarios':theoretical,
        'sample_count':len(sample),'observed_min_max_h7_h6':[float(values.min()),float(values.max())],
        'seam_max_abs_h7_h6':seam,'pole_identity_max_abs_h7_h6':pole,
        'adjacent_source_centers_h7_h6_abs_delta_max':max(grad),
        'adjacent_source_centers_h7_h6_abs_delta_p95':float(np.quantile(grad,.95)),
        'actual_M7_M6_polar_Veff_D029':'UNVERIFIED_WITHOUT_M7_GMSH',
        'actual_M7_Tet10_D031':'UNVERIFIED_WITHOUT_M7_GMSH',
        'formal_convergence':'UNPROVEN',
        'future_program_CPU_telemetry':'record process CPU seconds / wall seconds and thread-level phases; 15s independent heartbeat',
        'next':'Make distinct M7 guarded mesh-only program only after source review; verify curved Tet10 27/343/729QP D031 and independently observed supported polar D029; no M7 FEM yet'}
    OUT.mkdir(parents=True,exist_ok=True)
    with (OUT/'P10KA_M7_C2_SIZE_FIELD_SAMPLES.csv').open('w',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=list(sample[0]));writer.writeheader();writer.writerows(sample)
    (OUT/'P10KA_M7_C2_SIZE_PREFLIGHT_QA.json').write_text(json.dumps(qa,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(qa,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
