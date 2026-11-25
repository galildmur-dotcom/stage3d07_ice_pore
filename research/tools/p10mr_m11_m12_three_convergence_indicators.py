#!/usr/bin/env python3
"""Independent M11->M12 real 4D and three mandatory P10MQ indicators; no FEM."""
import io,json,math,zipfile
from pathlib import Path
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[2]
SOURCES={11:ROOT/'upload/P10MI_M11_FIRST_FULL4D_EVIDENCE.zip',
         12:ROOT/'upload/P10MO_M12_FIRST_FULL4D_EVIDENCE.zip'}
KEY=['step','region','radial_bin','mu_bin','phi_bin']
KEY4=['step','radial_bin','mu_bin','phi_bin']
COMP=['mech_explicit_per_m','mech_equilibrium_per_m','mech_history_per_m',
      'thermal_mass_per_m','thermal_diffusion_per_m','thermal_robin_per_m']
SPLIT=['explicit_geometry_normalization_per_m','explicit_stress_chain_per_m','explicit_sum_per_m']

def load(i):
    with zipfile.ZipFile(SOURCES[i]) as z:
        assert z.testzip() is None
        p=pd.read_csv(io.BytesIO(z.read('P10DD_SIGNED_R_THETA_PHI_T.csv')))
        q=pd.read_csv(io.BytesIO(z.read('P10LG_EXPLICIT_GEOMETRY_STRESS_4D.csv')))
        m=json.loads(z.read('P10MI_MANIFEST.json' if i==11 else 'P10MO_MANIFEST.json'))
    assert m['status']==f'P10{"MI" if i==11 else "MO"}_M{i}_REAL_FULL4D_PASS'
    assert m['FEM_attempts']==1 and m['native_exit_code']==0 and not m['stop_reason']
    assert m['independent_4d']['status']=='P10GY_INDEPENDENT_TIME4D_CLOSURE_PASS'
    assert m['two_term_explicit']['status']=='P10LM_TWO_TERM_PHYSICAL_CSV_QA_PASS'
    assert len(p)==43236 and len(q)==43200
    assert set(p.mesh)=={f'M{i}'} and set(q.mesh)=={f'M{i}'}
    assert not p[KEY].duplicated().any() and not q[KEY4].duplicated().any()
    assert np.abs(p[COMP].sum(axis=1)-p.total_per_m).max()<1e-9
    v=p.query("region=='VOLUME'").sort_values(KEY4).reset_index(drop=True)
    q=q.sort_values(KEY4).reset_index(drop=True)
    assert v[KEY4].equals(q[KEY4]) and len(v)==43200
    assert np.abs(q[SPLIT[0]]+q[SPLIT[1]]-q[SPLIT[2]]).max()<1e-9
    assert np.abs(q[SPLIT[2]]-v['mech_explicit_per_m']).max()<1e-9
    return p.sort_values(KEY).reset_index(drop=True),q,m

def norm(x):
    v=np.asarray(x,dtype=float)
    return {'L1_per_m':float(np.abs(v).sum()),'L2_per_m':float(np.linalg.norm(v)),
            'signed_per_m':float(v.sum())}

def main():
    out=ROOT/'research/P10MR_M11_M12_REAL_FULL4D_THREE_INDICATORS.json'
    if out.exists():raise RuntimeError('P10MR output exists; no overwrite')
    p={};q={};m={}
    for i in SOURCES:p[i],q[i],m[i]=load(i)
    assert p[11][KEY].equals(p[12][KEY]) and q[11][KEY4].equals(q[12][KEY4])
    for col in ('time_start_s','time_end_s','r_lower_mm','r_upper_mm',
                'theta_lower_rad','theta_upper_rad','phi_lower_rad','phi_upper_rad'):
        assert np.allclose(p[11][col],p[12][col],atol=1e-12,rtol=0,equal_nan=True),col
    d=(p[12].total_per_m-p[11].total_per_m).to_numpy()
    a=norm(d)
    D11=float(m[11]['independent_4d']['jpeak_derivative_per_m'])
    D12=float(m[12]['independent_4d']['jpeak_derivative_per_m'])
    delta=D12-D11
    assert abs(a['signed_per_m']-delta)<1e-9
    E=abs(delta)/abs(D12) if D12 else None
    K=1-abs(delta)/a['L1_per_m'] if a['L1_per_m'] else None
    ratio=a['L1_per_m']/abs(delta) if delta else None
    vol=(p[12].region=='VOLUME').to_numpy()
    mu=p[12].mu_bin.to_numpy()
    radial=p[12].radial_bin.to_numpy()
    steps=p[12].step.to_numpy()
    r={'protocol':'P10MR_M11_M12_REAL_SIGNED_FULL4D_THREE_INDICATORS',
       'status':'INDEPENDENT_ALIGNED_4D_AND_THREE_INDICATORS_PASS',
       'rows':43236,'volume_rows':43200,'steps':36,'dt_s':25,
       'M11_mesh_sha256':m[11]['mesh_sha256'],
       'M12_mesh_sha256':m[12]['mesh_sha256'],
       'D_R_jpeak_M11_per_m':D11,'D_R_jpeak_M12_per_m':D12,
       'delta_global_per_m':delta,'E_relative_global':E,
       'E_relative_global_percent':100*E if E is not None else None,
       'L1_signed_4D_per_m':a['L1_per_m'],'L2_signed_4D_per_m':a['L2_per_m'],
       'K_normalized_cancellation':K,'C_cancellation_ratio':ratio,
       'positive_local_delta_sum_per_m':.5*(a['L1_per_m']+delta),
       'negative_local_delta_abs_sum_per_m':.5*(a['L1_per_m']-delta),
       'component_signed_M12_minus_M11_per_m':{},
       'component_local_L1_M12_minus_M11_per_m':{},
       'split_local_L1_M12_minus_M11_per_m':{},
       'radial_L1_M12_minus_M11':{},'polar_L1_M12_minus_M11':{},
       'time_L1_M12_minus_M11':{},
       'late_last6_L1_fraction':float(np.abs(d[vol&(steps>=31)]).sum()/a['L1_per_m']),
       'max_4d_row_closure':max(float(np.abs(p[i][COMP].sum(axis=1)-p[i].total_per_m).max()) for i in SOURCES),
       'FEM_attempts_new':0,'mesh_generation_attempts_new':0}
    for col in COMP:
        diff=(p[12][col]-p[11][col]).to_numpy()
        r['component_signed_M12_minus_M11_per_m'][col]=float(diff.sum())
        r['component_local_L1_M12_minus_M11_per_m'][col]=norm(diff)
    for col in SPLIT:
        r['split_local_L1_M12_minus_M11_per_m'][col]=norm((q[12][col]-q[11][col]).to_numpy())
    for ir in range(10):
        r['radial_L1_M12_minus_M11'][str(ir)]=norm(d[vol&(radial==ir)])
    for label,mask in [('south',mu==0),('middle',(mu>0)&(mu<9)),('north',mu==9)]:
        r['polar_L1_M12_minus_M11'][label]=norm(d[vol&mask])
    for step in range(1,37):
        r['time_L1_M12_minus_M11'][str(step)]=norm(d[vol&(steps==step)])
    prev=json.loads((ROOT/'research/P10MJ_M9_M10_M11_REAL_SIGNED4D_AUDIT.json').read_text())
    r['L1_new_over_M10_to_M11']=r['L1_signed_4D_per_m']/prev['M10_to_M11']['L1_per_m']
    r['L2_new_over_M10_to_M11']=r['L2_signed_4D_per_m']/prev['M10_to_M11']['L2_per_m']
    out.write_text(json.dumps(r,indent=2)+'\n')
    print(json.dumps({k:r[k] for k in ('status','D_R_jpeak_M11_per_m','D_R_jpeak_M12_per_m',
      'delta_global_per_m','E_relative_global_percent','L1_signed_4D_per_m',
      'L2_signed_4D_per_m','K_normalized_cancellation','C_cancellation_ratio',
      'L1_new_over_M10_to_M11','L2_new_over_M10_to_M11','late_last6_L1_fraction')},indent=2))

if __name__=='__main__':main()
