#!/usr/bin/env python3
"""Independent 4D M8/M9/M10 cross-mesh audit on identical partition bins, no FEM."""
import csv, io, json, math, sys, zipfile
from pathlib import Path
import numpy as np
import pandas as pd

KEY=['step','region','radial_bin','mu_bin','phi_bin']
COMP=['mech_explicit_per_m','mech_equilibrium_per_m','mech_history_per_m',
      'thermal_mass_per_m','thermal_diffusion_per_m','thermal_robin_per_m']
NAME='P10DD_SIGNED_R_THETA_PHI_T.csv'

def load(path):
    with zipfile.ZipFile(path) as z:
        assert z.testzip() is None
        p=pd.read_csv(io.BytesIO(z.read(NAME)))
    assert len(p)==43236 and p.step.nunique()==36
    assert not p[KEY].duplicated().any()
    assert set(p.mesh)=={path.stem.split('_')[1]} or len(set(p.mesh))==1
    assert (p.region=='VOLUME').sum()==43200
    err=np.abs(p[COMP].sum(axis=1)-p.total_per_m).max()
    assert err<1e-9,err
    return p

def main():
    m8,m9,m10,out=map(Path,sys.argv[1:5])
    x={8:load(m8),9:load(m9),10:load(m10)}
    x={k:v.sort_values(KEY).reset_index(drop=True) for k,v in x.items()}
    for a,b in ((8,9),(9,10)):
        assert x[a][KEY].equals(x[b][KEY]),'4D keys mismatch'
        for col in ('time_start_s','time_end_s','r_lower_mm','r_upper_mm',
                    'theta_lower_rad','theta_upper_rad','phi_lower_rad','phi_upper_rad'):
            assert np.allclose(x[a][col],x[b][col],atol=1e-12,rtol=0,equal_nan=True),col
    def d(a,b):return (x[b].total_per_m-x[a].total_per_m).to_numpy()
    d89,d910=d(8,9),d(9,10)
    vol=(x[10].region=='VOLUME').to_numpy()
    def norms(z):
        absolute=float(np.abs(z).sum());signed=float(z.sum())
        return {'L1_per_m':absolute,'L2_per_m':float(np.linalg.norm(z)),
                'signed_per_m':signed,'cancellation_ratio':absolute/abs(signed) if signed else None}
    old,new=norms(d89),norms(d910)
    r={'protocol':'P10LZ_M8_M9_M10_REAL_SIGNED4D_NO_FEM','status':'ALIGNED_4D_PASS',
       'row_count':43236,'volume_rows':43200,'steps':36,
       'D_R_jpeak_per_m':{str(i):float(x[i].total_per_m.sum()) for i in (8,9,10)},
       'M8_to_M9':old,'M9_to_M10':new,
       'L1_new_over_prior':new['L1_per_m']/old['L1_per_m'],
       'L2_new_over_prior':new['L2_per_m']/old['L2_per_m'],
       'consecutive_cosine':float(np.dot(d89,d910)/(np.linalg.norm(d89)*np.linalg.norm(d910))),
       'consecutive_pearson':float(np.corrcoef(d89,d910)[0,1]),
       'components_M9_to_M10_per_m':{k:float((x[10][k]-x[9][k]).sum()) for k in COMP},
       'radial_M9_to_M10':{},'polar_M9_to_M10':{},'last_six':{},
       'total_closure_max_abs_per_m':max(float(np.abs(v[COMP].sum(axis=1)-v.total_per_m).max()) for v in x.values())}
    for ir in range(10):
        mask=vol&(x[10].radial_bin.to_numpy()==ir)
        r['radial_M9_to_M10'][str(ir)]=norms(d910[mask]) if mask.any() else None
    mu=x[10].mu_bin.to_numpy()
    for key,mask in [('south',mu==0),('mid',(mu>0)&(mu<9)),('north',mu==9)]:
        r['polar_M9_to_M10'][key]=norms(d910[vol&mask])
    late=(x[10].step.to_numpy()>=31)&vol
    r['last_six']={'L1_per_m':float(np.abs(d910[late]).sum()),
       'L1_fraction':float(np.abs(d910[late]).sum()/np.abs(d910[vol]).sum()),
       'signed_per_m':float(d910[late].sum())}
    assert not out.exists()
    out.write_text(json.dumps(r,indent=2)+'\n')
    print(json.dumps(r,indent=2))

if __name__=='__main__':main()
