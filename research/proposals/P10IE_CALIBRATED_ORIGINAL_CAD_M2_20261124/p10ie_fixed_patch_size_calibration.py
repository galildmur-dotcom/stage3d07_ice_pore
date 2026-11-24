#!/usr/bin/env python3
"""P10IE: read-only physical-patch calibration proposal for original CAD M2.

It estimates a *relative* log-size correction from actual curved Tet10 Veff.
No Gmsh/FEM/mesh generation. Not a guarantee of the next native mesh response.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import numpy as np
import p10hv_independent_scan as scan

HERE=Path(__file__).resolve().parent
SOURCE={
 'M1':('P10GT_HXT10.msh','47460969be26c2bd0a15e0b1425806fa350aa09aa2b4ac9f80605b433fc65ca7'),
 'P10ID':('P10ID_M2_3D_UNVERIFIED.msh','8acba5a9b3185429c200989015a7dfffb2b19452170db9d508da3e59ea0102f5')}
GOAL=.625

def patches(name,sha):
    raw=(HERE/name).read_bytes()
    if hashlib.sha256(raw).hexdigest()!=sha:raise RuntimeError('source fingerprint mismatch')
    nodes,tet,_=scan.read_msh(raw)
    q27=scan.evaluate(nodes,tet,3,None)
    q343=scan.evaluate(nodes,tet,7,q27['volume'])
    q729=scan.evaluate(nodes,tet,9,q27['volume'])
    return scan.groups(q343),scan.groups(q729)

def smoothstep(x):
    z=np.clip(x,0,1)
    return z*z*(3-2*z)

def corrected_factor(delta_n,delta_s,d_mm,mu):
    """C1 patch: angular 0.6–0.8 absolute polar, radial 0.3–1.0mm taper."""
    angle=smoothstep((abs(mu)-.6)/.2)
    radial=1-smoothstep((d_mm-.3)/.7)
    delta=delta_n if mu>=0 else delta_s
    return float(np.exp(-delta*angle*radial))

def main():
    all_q={k:patches(*v) for k,v in SOURCE.items()}
    out={'protocol':'P10IE_R1_SOURCE_ONLY_ACTUAL_M1_M2_PATCH_SIZE_CALIBRATION',
         'goal_Veff_new_over_M1':GOAL,'calibration_patch':'d=0..0.5mm and abs(mu)>=0.8 north/south',
         'calibrated_using_actual_curved_729QP_not_nominal_Gmsh_h':True,
         'calibrated_patches':{},'spatial_C1_correction_examples':[],
         'no_new_Gmsh_attempts':True,'FEM_attempts':0}
    delta={}
    for side,s in [('north','N'),('south','S')]:
        key=f'near_p0_{s}'
        old=all_q['M1'][1][key]
        new=all_q['P10ID'][1][key]
        q=new['Veff']/old['Veff']
        correction=(GOAL/q)**(1/3)
        d=-np.log(correction)
        delta[side]=float(d)
        q343=all_q['P10ID'][0][key]['Veff']/all_q['M1'][0][key]['Veff']
        out['calibrated_patches'][side]={
            'M1_Veff_m3':old['Veff'],'M1_h_eff_cube_root_mm':old['Veff']**(1/3)*1000,
            'P10ID_Veff_m3':new['Veff'],'P10ID_h_eff_cube_root_mm':new['Veff']**(1/3)*1000,
            'M1_N_eff':old['Neff'],'P10ID_N_eff':new['Neff'],
            'observed_Veff_ratio_729':q,'observed_Veff_ratio_343':q343,
            'additional_nominal_linear_factor':float(correction),
            'log_size_patch_delta':float(d),
            'estimated_Veff_ratio_if_faithful_cubic_response':float(q*correction**3),
            'hypothesis_not_a_native_Gmsh_prediction':True}
    for dmm in (.0,.1,.3,.5,.7,1.0):
        for mu in (.7,.8,.95):
            out['spatial_C1_correction_examples'].append({'d_mm':dmm,'abs_mu':mu,
                'north_factor':corrected_factor(delta['north'],delta['south'],dmm,mu),
                'south_factor':corrected_factor(delta['north'],delta['south'],dmm,-mu)})
    print(json.dumps(out,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
