#!/usr/bin/env python3
"""P10KE: diagnose failed M7 D031/D029, propose smooth polar C2 collar, no Gmsh."""
import csv
import hashlib
import json
import math
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

from p10iu_continuous_m4 import Field, rows, C, R, s5

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'p10ke_result'
HA=ROOT/'P10HA_centers.csv'
SRC=ROOT/'p10jz_result/P10JZ_M7_PROVISIONAL_C2_1200_BINS.csv'
M7_AUDIT=ROOT/'p10kc_m7_audit/P10KC_M6_M7_INDEPENDENT_D031_D029.json'
BAD_AUDIT=ROOT/'p10kc_m7_audit/P10KD_LOCAL_BAD_TET10_D031.json'


def collar(position):
    v=np.asarray(position)-C
    r=float(np.linalg.norm(v))
    mu=float(v[2]/r)
    dmm=max(0.,(r-R)*1000)
    # C² plateau on pole cap, supported around 0..0.8 mm from the pore wall.
    angular=float(s5((abs(mu)-.68)/.18))
    radial=float(1-s5((dmm-.30)/.50))
    return angular*radial


def composite(k0,w,lam):
    # k0=1-(1-k0), formula preserves [0,1] and C².
    return 1-(1-k0)*(1-lam*w)


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    audits=json.loads(M7_AUDIT.read_text())
    bad=json.loads(BAD_AUDIT.read_text())['M7']['ten_worst'][0]
    assert audits['status']=='GEOMETRY_STOP'
    assert bad['element_id']==7442 and bad['minSICN']<.2
    src=rows(SRC)
    field=Field(rows(HA),src,'0.1')
    keys=field.keys
    weights={tuple(int(row[x]) for x in ('radial_bin','mu_bin','phi_bin')):
             int(row['M3_QP']) for row in src}
    assert min(weights.values())>0
    caps={'N':np.array([k[0]<5 and k[1]==9 for k in keys]),
          'S':np.array([k[0]<5 and k[1]==0 for k in keys])}
    cent=field.center_points
    origin=np.asarray([field.kappa(x) for x in cent])
    wedge=np.asarray([collar(x) for x in cent])
    qp=np.asarray([weights[k] for k in keys],float)
    bad_point=np.asarray(bad['corner_centroid_m'])
    bad_kw=field.kappa(bad_point)
    assert abs(bad_kw-.001817382292584)<1e-9 and collar(bad_point)==0
    # Bracketing hypotheses, not an empirical volume calibration.
    scenarios={}
    for lam in (.5,.75,1.):
        k=1-(1-origin)*(1-lam*wedge)
        sizes=np.power(.8,k/3)
        record={}
        for side,mask in caps.items():
            record[side]={'M6_QP_support':int(qp[mask].sum()),
                          'mean_kappa_qp_weighted':float(np.average(k[mask],weights=qp[mask])),
                          'nominal_cube_proxy_qp_weighted':float(np.average(.8**k[mask],weights=qp[mask])),
                          'baseline_cube_proxy_qp_weighted':float(np.average(.8**origin[mask],weights=qp[mask]))}
        scenarios[str(lam)]={'cap_regions':record,
                             'min_max_incremental_h7_h6':[float(sizes.min()),float(sizes.max())],
                             'bad_tet7442_collar_weight':float(collar(bad_point)),
                             'bad_tet7442_incremental_h7_h6':float(.8**(composite(bad_kw,0,lam)/3))}
    # Select full C² collar as an exploratory source, not a new Gmsh attempt.
    lam=1.;knew=1-(1-origin)*(1-lam*wedge)
    values=[]
    for i,key in enumerate(keys):
        values.append({'radial_bin':key[0],'mu_bin':key[1],'phi_bin':key[2],
                       'kappa_original':float(origin[i]),'C2_polar_collar':float(wedge[i]),
                       'kappa_proposed':float(knew[i]),
                       'M7_R2_over_M6_h_source':float(.8**(knew[i]/3)),
                       'original_signed4D_score':float(src[i]['beta_0.1_score']),
                       'M6_QP':int(qp[i])})
    # Spherical seam, pole uniqueness and interpolation continuity: base field
    # has C2 and the added cap is a product of two C2 smoothstep plateaus.
    seam=0.;pole=0.
    def fn(p):return float(.8**(composite(field.kappa(p),collar(p),1)/3))
    for d in (0.,.02,.1,.3,.5,.7,1.,2.,5.):
        for mu in (-.99,-.85,-.65,.65,.85,.99):
            def p(phi):
                return C+(R+d*.001)*np.array([math.sqrt(1-mu*mu)*math.cos(phi),
                                               math.sqrt(1-mu*mu)*math.sin(phi),mu])
            seam=max(seam,abs(fn(p(-math.pi))-fn(p(math.pi))))
        for sign in (-1,1):
            p=C+(R+d*.001)*np.array([0,0,sign])
            pole=max(pole,abs(fn(p)-fn(p.copy())))
    assert seam<1e-12 and pole<1e-12
    matrix_old=np.zeros((10,10));matrix_new=np.zeros((10,10))
    for (rad,pol,az),o,n in zip(keys,origin,knew):
        matrix_old[rad,pol]+=o/12
        matrix_new[rad,pol]+=n/12
    fig,axs=plt.subplots(1,3,figsize=(16,4.8),constrained_layout=True)
    for ax,xx,title in zip(axs,(matrix_old,matrix_new,matrix_new-matrix_old),
                           ('M7 R1 κ source (failed geometry)',
                            'M7 R2 proposed κ C² polar collar',
                            'Extra κ without changing max volume 20%')):
        im=ax.imshow(xx.T,origin='lower',aspect='auto',vmin=0,vmax=1,cmap='viridis')
        ax.set_title(title)
        ax.set_xlabel('radial shell index');ax.set_ylabel('polar zone, 0=S, 9=N')
        fig.colorbar(im,ax=ax,shrink=.78)
    fig.savefig(OUT/'P10KE_M7_C2_POLAR_COLLAR_SOURCE_ONLY.png',dpi=150)
    plt.close(fig)
    with (OUT/'P10KE_M7_R2_PROPOSED_C2_SOURCE_1200_BINS.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(values[0]));w.writeheader();w.writerows(values)
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    qa={'protocol':'P10KE_M7_D031_D029_DIAGNOSIS_C2_POLAR_COLLAR_SOURCE_ONLY',
        'status':'PASS_SOURCE_ONLY_NO_NEW_GMSH_NO_MESH_NO_FEM',
        'inputs_sha256':{'M7_R1_QA':sha(M7_AUDIT),'M7_bad_tet':sha(BAD_AUDIT),
                          'M7_R1_source':sha(SRC),'centers':sha(HA)},
        'bad_tet_id':bad['element_id'],
        'bad_tet_distance_to_pore_mm':bad['distance_to_pore_mm'],
        'bad_tet_mu':bad['mu'],'bad_tet_original_kappa':bad_kw,
        'bad_tet_collar_weight':collar(bad_point),
        'actual_M7_R1_over_M6_polar_Veff':{s:audits['D029_regions']['near_p0_'+s]['actual_M7_over_M6_729'] for s in ('N','S')},
        'scenarios':scenarios,
        'proposed_method':'kappa_R2=1-(1-kappa_R1)*(1-s5((abs(mu)-.68)/.18)*(1-s5((dmm-.30)/.50)))',
        'reference_cube_proxy': '0.8 ** kappa_R2; NOT observed Veff and NOT guaranteed 15-25pct actual reduction',
        'seam_abs':seam,'pole_identity_abs':pole,
        'M7_candidate_status':'UNACCEPTED: D031 minSICN 0.16262 and D029 miss',
        'next':'P10KF physically guard local Tet7442 topology and revised C2, distinct new mesh-only attempt; D031 and D029 read-only before any FEM'}
    (OUT/'P10KE_M7_R2_SOURCE_ONLY_QA.json').write_text(json.dumps(qa,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(qa,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
