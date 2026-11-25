#!/usr/bin/env python3
"""P10MT: compare A/B/C M13 C2 mesh-size source hypotheses, no Gmsh/FEM."""
import hashlib,json,math,sys
from pathlib import Path
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[2]
IN=ROOT/'p10ms_m12_diagnostic/P10MS_1200_BIN_SOURCE_VS_4D_OUTCOME.csv'
COORD=ROOT/'p10mf_package_final/P10HA_SPATIAL_KAPPA_1200_BINS.csv'
QP_SOURCE=ROOT/'p10mk_m12_source/P10MK_M12_M11_MINUS_M10_REAL_SIGNED4D_1200_BINS.csv'
OUT=ROOT/'p10mt_m13_source_only'
sys.path.insert(0,str(ROOT/'p10mf_package_final'))
from p10iu_continuous_m4 import Field,rows,C,R
from p10kp_m8_r2_polar_plateau import kappa_r2

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def clamp(x):return np.clip(x,0.,1.)
def norm(x):
    x=np.asarray(x,dtype=float)
    assert np.isfinite(x).all() and np.min(x)>=0
    return x/max(float(x.max()),1e-30)
def evaluate(field,p):
    r=p-C;radius=float(np.linalg.norm(r));mu=float(r[2]/radius)
    dmm=max(0.,(radius-R)*1000.)
    return kappa_r2(min(1.,max(0.,field.kappa(p))),dmm,mu)

def main():
    if OUT.exists():raise RuntimeError('P10MT output exists; no overwrite')
    src=pd.read_csv(IN).sort_values(['radial_bin','mu_bin','phi_bin']).reset_index(drop=True)
    assert len(src)==1200 and not src[['radial_bin','mu_bin','phi_bin']].duplicated().any()
    keys=['radial_bin','mu_bin','phi_bin']
    qp=pd.read_csv(QP_SOURCE)[keys+['M3_QP']]
    src=src.merge(qp,on=keys,validate='one_to_one')
    assert len(src)==1200 and src.M3_QP.gt(0).all()
    old=src.old_L1.to_numpy();new=src.new_L1.to_numpy()
    late=src.late_new_actual.to_numpy()
    gain=np.maximum(new-old,0.)
    allnorm=norm(new);latenorm=norm(late);growthnorm=norm(gain)
    polar=np.where(src.mu_bin.isin((0,9)),1.,0.)
    # A: the established absolute+late source, using new M11->M12 data.
    scoreA=(.4*allnorm+.6*latenorm)*(1+.20*polar)
    # B: add an explicit reward for bins that deteriorated during M12.
    scoreB=(.45*allnorm+.25*latenorm+.30*growthnorm)*(1+.20*polar)
    # C: balanced score: per-bin baseline + deterioration, milder polar bias,
    # and additive floor to resist over-concentration of the nominal size law.
    scoreC=(.40*allnorm+.25*latenorm+.20*growthnorm+.15)*(1+.08*polar)
    raw={'A_existing_residual':scoreA,'B_growth_aware':scoreB,
         'C_balanced_coverage':scoreC}
    for name,z in raw.items():
        assert len(z)==1200 and np.isfinite(z).all() and z.min()>=0 and z.max()>0,name
    OLD=rows(COORD)
    OUT.mkdir()
    status={'protocol':'P10MT_M13_THREE_C2_SOURCE_ONLY_HYPOTHESES',
       'status':'PASS_SOURCE_ONLY_NO_GMSH_NO_MESH_NO_FEM',
       'parent_source_sha256':sha(IN),'coordinate_sha256':sha(COORD),
       'qp_source_sha256':sha(QP_SOURCE),
       'bins':1200,'full4d_old_L1':float(old.sum()),'full4d_new_L1':float(new.sum()),
       'growth_positive_L1_sum':float(gain.sum()),
       'existing_polar_core':'retained P10KP C2 plateau d<=0.5mm, abs(mu)>=0.8',
       'nominal_incremental_Veff_ratio':'1-0.20*kappa13, 0.80..1.0 (not measured Tet10)',
       'variants':{},'mesh_attempts':0,'FEM_attempts':0,
       'limitations':['Score-to-error overlap is source-only retrospective and not predictive FEM validation',
                      'C2 field is spatially interpolated; curved 729QP D029 and Gmsh D031 remain unmeasured',
                      'No M13 geometry generated; not yet authorized FEM']}
    for name,z in raw.items():
        csv=src[keys+['M3_QP','old_L1','new_L1','late_new_actual','L1_reduction']].copy()
        csv['beta_0.1_score']=z
        path=OUT/(f'P10MT_M13_{name}_1200_BINS.csv')
        csv.to_csv(path,index=False,float_format='%.17g')
        f=Field(OLD,rows(path),'0.1')
        # Retain old full polar collar. Distinguish source-center weights,
        # reconstructed physical C2 samples, and actual mesh volumes.
        kap=np.array([evaluate(f,p) for p in f.center_points])
        assert (kap>=0).all() and (kap<=1).all() and kap.max()>0
        volume_ratio=1.-.20*kap
        groups={}
        masks={'north':src.mu_bin.eq(9).to_numpy(),
               'south':src.mu_bin.eq(0).to_numpy(),
               'middle':src.mu_bin.between(1,8).to_numpy(),
               'wall012':src.radial_bin.le(2).to_numpy(),
               'polar_wall012':(src.radial_bin.le(2)&src.mu_bin.isin((0,9))).to_numpy(),
               'worsened':gain>0,
               'unselected_old_top20':src['beta_0.1_score'].le(src['beta_0.1_score'].quantile(.8)).to_numpy()}
        for key,mask in masks.items():
            groups[key]={'count':int(mask.sum()),
                'mean_kappa':float(kap[mask].mean()),
                'mean_nominal_volume_ratio':float(volume_ratio[mask].mean()),
                'new_L1_weighted_kappa':float(np.dot(new[mask],kap[mask])/max(1e-30,new[mask].sum())),
                'growth_L1_weighted_kappa':float(np.dot(gain[mask],kap[mask])/max(1e-30,gain[mask].sum()))}
        # Source-center delta tests across exact azimuth seam/poles.
        seam=0.;pole=0.
        for d in (0.,.02,.1,.5,1.,5.):
            for mu in (-.95,-.8,-.6,.6,.8,.95):
                def pos(phi):return C+(R+.001*d)*np.array([math.sqrt(1-mu*mu)*math.cos(phi),
                                                            math.sqrt(1-mu*mu)*math.sin(phi),mu])
                seam=max(seam,abs(evaluate(f,pos(-math.pi))-evaluate(f,pos(math.pi))))
            for sign in (-1,1):
                p=C+(R+.001*d)*np.array([0.,0.,float(sign)])
                values=[evaluate(f,p) for _ in range(5)]
                pole=max(pole,max(values)-min(values))
        assert seam<1e-10 and pole<1e-12
        status['variants'][name]={'csv':path.name,'csv_sha256':sha(path),
          'score_max':float(z.max()),'score_min':float(z.min()),
          'center_kappa_min_max':[float(kap.min()),float(kap.max())],
          'center_kappa_mean':float(kap.mean()),
          'center_nominal_Veff_ratio_min_max':[float(volume_ratio.min()),float(volume_ratio.max())],
          'center_new_L1_weighted_kappa':float(np.dot(new,kap)/new.sum()),
          'center_growth_L1_weighted_kappa':float(np.dot(gain,kap)/max(gain.sum(),1e-30)),
          'groups':groups,'seam_error':seam,'pole_error':pole,
          'c2_status':'analytical positive Wendland C2 plus S5; exact seam/pole equality sampled'}
    (OUT/'P10MT_THREE_FIELDS_SOURCE_ONLY_QA.json').write_text(json.dumps(status,indent=2)+'\n')
    print(json.dumps({'status':status['status'],
      'variants':{k:{x:v[x] for x in ('center_kappa_mean','center_new_L1_weighted_kappa',
               'center_growth_L1_weighted_kappa','center_nominal_Veff_ratio_min_max')}
        for k,v in status['variants'].items()}},indent=2))

if __name__=='__main__':main()
