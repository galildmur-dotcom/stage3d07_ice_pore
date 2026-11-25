#!/usr/bin/env python3
"""P10MJ: independent M9/M10/M11 real aligned signed 4D and explicit split audit."""
import io, json, math, sys, zipfile
from pathlib import Path
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[2]
NAMES={9:'P10LM_M9_FIRST_FULL4D_EVIDENCE.zip',
       10:'P10LY_M10_FIRST_FULL4D_EVIDENCE.zip',
       11:'P10MI_M11_FIRST_FULL4D_EVIDENCE.zip'}
KEY=['step','region','radial_bin','mu_bin','phi_bin']
COMP=['mech_explicit_per_m','mech_equilibrium_per_m','mech_history_per_m',
      'thermal_mass_per_m','thermal_diffusion_per_m','thermal_robin_per_m']
SPLIT=['explicit_geometry_normalization_per_m','explicit_stress_chain_per_m','explicit_sum_per_m']
SKEY=['step','radial_bin','mu_bin','phi_bin']

def load(index):
    path=ROOT/'upload'/NAMES[index]
    with zipfile.ZipFile(path) as z:
        assert z.testzip() is None
        data=pd.read_csv(io.BytesIO(z.read('P10DD_SIGNED_R_THETA_PHI_T.csv')))
        split=pd.read_csv(io.BytesIO(z.read('P10LG_EXPLICIT_GEOMETRY_STRESS_4D.csv')))
        manifest=json.loads(z.read('P10LM_MANIFEST.json' if index==9 else
                                   'P10LY_MANIFEST.json' if index==10 else 'P10MI_MANIFEST.json'))
    assert manifest['status'].endswith('_REAL_FULL4D_PASS')
    assert manifest['FEM_attempts']==1 and manifest['independent_4d']['rows']==43236
    assert len(data)==43236 and len(split)==43200
    assert data.step.nunique()==36 and not data[KEY].duplicated().any()
    assert set(data.mesh)=={f'M{index}'}
    assert set(split.mesh)=={f'M{index}'} and not split[SKEY].duplicated().any()
    assert np.max(np.abs(data[COMP].sum(axis=1)-data.total_per_m))<1e-9
    v=data.query("region=='VOLUME'").sort_values(SKEY).reset_index(drop=True)
    s=split.sort_values(SKEY).reset_index(drop=True)
    assert len(v)==43200 and v[SKEY].equals(s[SKEY])
    assert np.max(np.abs(s[SPLIT[0]]+s[SPLIT[1]]-s[SPLIT[2]]))<1e-9
    assert np.max(np.abs(s[SPLIT[2]]-v['mech_explicit_per_m']))<1e-9
    return data.sort_values(KEY).reset_index(drop=True),s,manifest

def norm(values):
    v=np.asarray(values,dtype=float)
    l1=float(np.abs(v).sum())
    l2=float(np.linalg.norm(v))
    signed=float(v.sum())
    return {'L1_per_m':l1,'L2_per_m':l2,'signed_per_m':signed,
            'cancellation_ratio':l1/abs(signed) if signed else None}

def main():
    out=ROOT/'research/P10MJ_M9_M10_M11_REAL_SIGNED4D_AUDIT.json'
    if out.exists():raise RuntimeError('P10MJ result exists; no overwrite')
    data={};split={};manifest={}
    for index in NAMES:
        data[index],split[index],manifest[index]=load(index)
    for a,b in ((9,10),(10,11)):
        assert data[a][KEY].equals(data[b][KEY])
        assert split[a][SKEY].equals(split[b][SKEY])
        for k in ('time_start_s','time_end_s','r_lower_mm','r_upper_mm',
                  'theta_lower_rad','theta_upper_rad','phi_lower_rad','phi_upper_rad'):
            assert np.allclose(data[a][k],data[b][k],rtol=0,atol=1e-12,equal_nan=True),k
    differences={(9,10):(data[10].total_per_m-data[9].total_per_m).to_numpy(),
                 (10,11):(data[11].total_per_m-data[10].total_per_m).to_numpy()}
    old,new=(differences[(9,10)],differences[(10,11)])
    r={'protocol':'P10MJ_REAL_M9_M10_M11_SIGNED4D_AND_EXPLICIT_TWO_TERM',
       'status':'INDEPENDENT_ALIGNED_FULL4D_PASS','rows':43236,'volume_rows':43200,
       'steps':36,'dt_s':25,'M11_mesh_sha256':manifest[11]['mesh_sha256'],
       'D_R_jpeak_per_m':{str(k):float(manifest[k]['independent_4d']['jpeak_derivative_per_m']) for k in NAMES},
       'M9_to_M10':norm(old),'M10_to_M11':norm(new),
       'L1_new_over_previous':norm(new)['L1_per_m']/norm(old)['L1_per_m'],
       'L2_new_over_previous':norm(new)['L2_per_m']/norm(old)['L2_per_m'],
       'consecutive_cosine':float(np.dot(old,new)/(np.linalg.norm(old)*np.linalg.norm(new))),
       'consecutive_pearson':float(np.corrcoef(old,new)[0,1]),
       'components_M10_to_M11_per_m':{key:float((data[11][key]-data[10][key]).sum()) for key in COMP},
       'split_integral_per_m':{str(k):{col:float(split[k][col].sum()) for col in SPLIT} for k in NAMES},
       'radial_M10_to_M11':{},'latitude_M10_to_M11':{},'time_M10_to_M11':{},
       'component_local_L1_M10_to_M11':{},'split_local_L1_M10_to_M11':{},
       'max_independent_closure_abs_per_m':max(float(np.abs(data[k][COMP].sum(axis=1)-data[k].total_per_m).max()) for k in NAMES),
       'M11_runtime_wall_s':manifest[11]['wall_s'],
       'M11_average_busy_logical_CPUs':manifest[11]['cpu_telemetry']['average_busy_logical_CPUs'],
       'M11_peak_private_polled_bytes':manifest[11]['peak_private_bytes_polled']}
    vol=(data[11].region=='VOLUME').to_numpy()
    mu=data[11].mu_bin.to_numpy()
    for ir in range(10):
        mask=vol&(data[11].radial_bin.to_numpy()==ir)
        r['radial_M10_to_M11'][str(ir)]=norm(new[mask])
    for label,mask in [('south',mu==0),('mid',(mu>=1)&(mu<=8)),('north',mu==9)]:
        r['latitude_M10_to_M11'][label]=norm(new[vol&mask])
    for stage in range(1,37):
        mask=vol&(data[11].step.to_numpy()==stage)
        r['time_M10_to_M11'][str(stage)]=norm(new[mask])
    r['last_six_steps_L1_fraction']=float(np.abs(new[vol&(data[11].step.to_numpy()>=31)]).sum()/np.abs(new[vol]).sum())
    for key in COMP:
        delta=data[11][key].to_numpy()-data[10][key].to_numpy()
        r['component_local_L1_M10_to_M11'][key]=norm(delta)
    for key in SPLIT:
        delta=split[11][key].to_numpy()-split[10][key].to_numpy()
        r['split_local_L1_M10_to_M11'][key]=norm(delta)
    r['negative_mech_explicit_nearwall_radial0_M11']={
        'explicit':manifest[11]['two_term_explicit']['radial_10_bins'][0]['explicit'],
        'geometry':manifest[11]['two_term_explicit']['radial_10_bins'][0]['geometry'],
        'stress':manifest[11]['two_term_explicit']['radial_10_bins'][0]['stress']}
    out.write_text(json.dumps(r,indent=2)+'\n')
    print(json.dumps({key:r[key] for key in ('status','D_R_jpeak_per_m','M9_to_M10',
        'M10_to_M11','L1_new_over_previous','L2_new_over_previous',
        'consecutive_cosine','consecutive_pearson','split_integral_per_m',
        'last_six_steps_L1_fraction')},indent=2))

if __name__=='__main__':main()
