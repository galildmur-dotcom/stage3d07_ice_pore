#!/usr/bin/env python3
"""P10KM M8 adaptive C2 size field, SOURCE ONLY, never calls Gmsh or FEM."""
from __future__ import annotations
import csv
import hashlib
import json
import math
from pathlib import Path
from zipfile import ZipFile,ZIP_DEFLATED
import numpy as np
import pandas as pd
import sys
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parent
OLD=ROOT/'p10kg_pkg'
OUT=ROOT/'p10km_result'
OUT.mkdir(exist_ok=True)
sys.path.insert(0,str(OLD))
from p10iu_continuous_m4 import Field, rows, C, R
SOURCE=ROOT.parent/'upload/P10KJ_M7_FIRST_FULL4D_EVIDENCE.zip'
M6=ROOT/'p10jw_result/P10DD_SIGNED_R_THETA_PHI_T.csv'
M7_SHA='875c9177de24612d0078f7a792b4b7641a2e604973cb1353500710c87693bb3d'
KEY=['step','region','radial_bin','mu_bin','phi_bin']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

with ZipFile(SOURCE) as a:
    assert a.testzip() is None
    meta=json.loads(a.read('P10KJ_MANIFEST.json'))
    assert meta['status']=='P10KJ_M7_REAL_FULL4D_PASS' and meta['mesh_sha256']==M7_SHA
    with a.open('P10DD_SIGNED_R_THETA_PHI_T.csv') as f:m7=pd.read_csv(f)
m6=pd.read_csv(M6)
assert len(m7)==len(m6)==43236
combined=m7.merge(m6,on=KEY,validate='one_to_one',suffixes=('_7','_6'))
assert len(combined)==43236
combined=combined[combined.region=='VOLUME'].copy()
combined['absdelta']=(combined.total_per_m_7-combined.total_per_m_6).abs()
combined['late_absdelta']=np.where(combined.step>=31,combined.absdelta,0.)
group=combined.groupby(['radial_bin','mu_bin','phi_bin']).agg(
    all_l1=('absdelta','sum'),late_l1=('late_absdelta','sum'),
    support_qp=('mechanical_qp_7','sum')).reset_index()
assert len(group)==1200 and group.all_l1.max()>0 and group.late_l1.max()>0

base=rows(OLD/'P10HA_SPATIAL_KAPPA_1200_BINS.csv')
reference={(int(x['radial_bin']),int(x['mu_bin']),int(x['phi_bin'])):x for x in base}
assert len(reference)==1200
records=[]
for r in group.to_dict('records'):
    key=(int(r['radial_bin']),int(r['mu_bin']),int(r['phi_bin']))
    b=reference[key]
    # Nonnegative bounded source, with data-driven polar priority, no hard angular cuts.
    theta=float(b['theta_mid_rad']);mu=math.cos(theta)
    polar=1+.20*max(0.,min(1.,(abs(mu)-.6)/.3))**3*(10-15*max(0.,min(1.,(abs(mu)-.6)/.3))+6*max(0.,min(1.,(abs(mu)-.6)/.3))**2)
    relative=(.4*float(r['all_l1'])/group.all_l1.max()+.6*float(r['late_l1'])/group.late_l1.max())
    raw=float(relative*polar)
    records.append({'radial_bin':key[0],'mu_bin':key[1],'phi_bin':key[2],
       'M3_QP':max(1,int(float(b['M1_mechanical_QP_dt25']))),
       'beta_0.1_score':raw,'all_l1_per_m':float(r['all_l1']),
       'late_l1_per_m':float(r['late_l1']),
       'M7_mechanical_QP_total':int(r['support_qp']),
       'polar_soft_priority':polar})
outsource=OUT/'P10KM_M8_LATE_TIME_SIGNED4D_1200_BINS.csv'
with outsource.open('w',newline='',encoding='utf8') as f:
    w=csv.DictWriter(f,fieldnames=list(records[0]));w.writeheader();w.writerows(records)

field=Field(base,rows(outsource),'0.1')
TARGET_VOL=.80
def increment(point):
    k=field.kappa(np.asarray(point,dtype=float))
    return k,(1-(1-TARGET_VOL)*k)**(1/3)

samples=[]
for dmm in (0,.02,.05,.1,.2,.3,.5,.7,1,2,5):
    for mu in (-1,-.99,-.9,-.8,-.6,0,.6,.8,.9,.99,1):
        for phi in (-math.pi,-2.5,-.5,0,1,2.5,math.pi):
            v=np.array([math.sqrt(max(0,1-mu**2))*math.cos(phi),math.sqrt(max(0,1-mu**2))*math.sin(phi),mu])
            k,h=increment(C+(R+.001*dmm)*v)
            samples.append({'distance_mm':dmm,'mu':mu,'phi':phi,'kappa':k,'incremental_h_ratio':h,'incremental_volume_ratio':h**3})
assert all(0<=r['kappa']<=1+1e-12 and .8-1e-12<=r['incremental_volume_ratio']<=1+1e-12 for r in samples)
with (OUT/'P10KM_M8_FIELD_SAMPLES.csv').open('w',newline='') as f:
    w=csv.DictWriter(f,fieldnames=list(samples[0]));w.writeheader();w.writerows(samples)

seamerr=0.;poleerr=0.
for dmm in (0,.03,.1,.5,1,2,5):
    for mu in (-1,-.9,-.8,-.6,.6,.8,.9,1):
        def p(phi):return C+(R+.001*dmm)*np.array([math.sqrt(max(0,1-mu**2))*math.cos(phi),math.sqrt(max(0,1-mu**2))*math.sin(phi),mu])
        a=increment(p(-math.pi));b=increment(p(math.pi))
        seamerr=max(seamerr,max(abs(x-y) for x,y in zip(a,b)))
        if abs(mu)==1:
            for phi in (-2.5,0,1.7,math.pi):
                v=increment(p(phi));poleerr=max(poleerr,max(abs(x-y) for x,y in zip(v,a)))
assert seamerr<1e-10 and poleerr<1e-10
score=np.array([r['beta_0.1_score'] for r in records]);order=np.argsort(-score)
qa={'protocol':'P10KM_M8_SOURCE_ONLY_C2_4D_ADAPTIVITY',
    'status':'PASS_SOURCE_ONLY_NO_GMSH_NO_MESH_NO_FEM',
    'source_M7_evidence_sha256':sha(SOURCE),'source_M6_csv_sha256':sha(M6),
    'accepted_M7_sha256':M7_SHA,'source_bins':len(records),
    'mesh_attempts':0,'FEM_attempts':0,'time_steps':36,'dt_s':25,
    'weight_formula':'0.4*L1(all 36)/max + 0.6*L1(steps 31..36)/max, times smooth polar factor [1,1.2]',
    'interpolator':'existing positive compact Wendland C2, Cartesian direction + log radial distance, quintic smoothstep normalization',
    'nominal_max_incremental_element_volume_reduction':.20,
    'nominal_max_incremental_element_length_reduction':1-.8**(1/3),
    'h_ratio_law':'(1-0.20*kappa)^(1/3)',
    'kappa_center_max':float(field.center_kappa.max()),
    'kappa_center_mean':float(field.center_kappa.mean()),
    'sample_kappa_range':[min(r['kappa'] for r in samples),max(r['kappa'] for r in samples)],
    'sample_length_ratio_range':[min(r['incremental_h_ratio'] for r in samples),max(r['incremental_h_ratio'] for r in samples)],
    'sample_count':len(samples),'polar_coordinate_max_abs_drift':poleerr,
    'azimuth_periodic_seam_max_abs_drift':seamerr,
    'top10_source_bin_keys':[list(records[i][k] for k in ('radial_bin','mu_bin','phi_bin')) for i in order[:10]],
    'caveats':['The field is a smooth SOURCE-ONLY mesh-design proxy, NOT a posteriori error bound.',
               'M7 baseline cumulative Gmsh callback must be exactly preserved before introducing this factor.',
               'Actual M8 geometry D031 and D029 adaptation still need independent Gmsh mesh evidence.',
               'No physical FEM or shape-gradient convergence claimed.']}
(OUT/'P10KM_M8_SOURCE_ONLY_DESIGN_QA.json').write_text(json.dumps(qa,indent=2,ensure_ascii=False)+'\n',encoding='utf8')
frame=pd.DataFrame(records)
heat=frame.groupby(['mu_bin','radial_bin'])['beta_0.1_score'].mean().unstack(fill_value=0).sort_index()
fig,ax=plt.subplots(figsize=(8,5.1),layout='constrained')
im=ax.imshow(heat,origin='lower',aspect='auto',cmap='magma',extent=[-.5,9.5,-.5,9.5])
ax.set(xlabel='Radial bin (0 near pore)',ylabel='Polar bin (0 south, 9 north)',
       title='P10KM M8 source-only 4D-informed priority (mean over azimuth)')
fig.colorbar(im,ax=ax,label='Source priority score (nonnegative)')
fig.savefig(OUT/'P10KM_M8_SOURCE_PRIORITY_MAP.png',dpi=170)
plt.close(fig)
with ZipFile(ROOT/'P10KM_M8_SOURCE_ONLY_4D_ADAPTIVITY_DESIGN_20261125.zip','w',ZIP_DEFLATED) as z:
    for p in sorted(OUT.iterdir()):z.write(p,p.name)
print(json.dumps(qa,indent=2,ensure_ascii=False))
