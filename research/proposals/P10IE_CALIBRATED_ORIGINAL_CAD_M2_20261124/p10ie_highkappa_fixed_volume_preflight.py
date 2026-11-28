#!/usr/bin/env python3
"""P10IE source-only: evaluate κ>=.8 at curved Tet10 QP in fixed physical space.

No Gmsh generation or FEM. This discontinuous κ mask requires QP stability QA.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import time

import numpy as np
import p10hv_independent_scan as mesh
import p10hc_continuous_kappa_geo as source
from p10hk_direct_kappa_callback_benchmark import DirectKappa

HERE=Path(__file__).resolve().parent
FILES={
    'M1':(HERE/'P10GT_HXT10.msh','47460969be26c2bd0a15e0b1425806fa350aa09aa2b4ac9f80605b433fc65ca7'),
    'M2_P10ID':(HERE/'P10ID_M2_3D_UNVERIFIED.msh','8acba5a9b3185429c200989015a7dfffb2b19452170db9d508da3e59ea0102f5')}
C=np.array([0.,0.,.03])

def analyze(path,direct,order):
    xyz,tet,_=mesh.read_msh(path.read_bytes())
    N,D,W=mesh.rule(order)
    sums=np.zeros(2);n_eff=np.zeros(2);volume=np.zeros(2);points=0;high=0
    # Physically conservative preselector: every relevant element has a node
    # within 2.5mm of the pore centre, and 343/729QP detects its actual mask.
    corners=xyz[tet[:,:4]]-C
    preselect=np.min(np.linalg.norm(corners,axis=2),axis=1)<.0035
    indices=np.flatnonzero(preselect)
    for k in range(0,len(indices),16):
        ids=indices[k:k+16];p=xyz[tet[ids]]
        jac=np.einsum('nic,qij->nqcj',p,D,optimize=True)
        det=np.linalg.det(jac)
        if np.any(det<=0):raise ValueError('non-positive curved Jacobian')
        vtot=(det*W).sum(axis=1)
        x=np.einsum('nic,qi->nqc',p,N,optimize=True)
        dr=x-C;rr=np.linalg.norm(dr,axis=2)
        d=rr-.001;mu=dr[:,:,2]/rr
        # Fixed admissible volume, restrict κ test to near wall and polar cone.
        # The quadratic approximation of a curved boundary can locally place
        # quadrature points just inside the analytic cavity. Such points are
        # outside the physical ice mask; do not evaluate physical κ there.
        possible=(d>=0)&(d<=.0005)&(np.abs(mu)>=.6)
        for j in range(len(ids)):
            for q in np.flatnonzero(possible[j]):
                points+=1
                if direct.kappa(*x[j,q])<.8:continue
                high+=1
                side=0 if mu[j,q]>=0 else 1
                weight=float(det[j,q]*W[q])
                sums[side]+=weight
                n_eff[side]+=weight/vtot[j]
                volume[side]+=weight
    return {'order':order,'candidate_tets_screened':int(len(indices)),
            'near_polar_QP_evaluated':points,'high_kappa_QP':high,
            'north':{'N_eff':float(n_eff[0]),'Veff_m3':float(volume[0]/n_eff[0]) if n_eff[0]>0 else None,
                     'represented_volume_m3':float(sums[0])},
            'south':{'N_eff':float(n_eff[1]),'Veff_m3':float(volume[1]/n_eff[1]) if n_eff[1]>0 else None,
                     'represented_volume_m3':float(sums[1])}}

def main():
    s,v,_,_,_,qa=source.load_centers(HERE/'P10HA_SPATIAL_KAPPA_1200_BINS.csv',HERE/'P10HA_KAPPA_QA.json')
    direct=DirectKappa(s,v,qa['mechanical_only_25_36_shared_smoothing_denominator'])
    out={'protocol':'P10IE_FIXED_PHYSICAL_MECHANICAL_KAPPA_GE_0p8_QP_SOURCE_ONLY',
         'status':'diagnostic_not_GO', 'kappa_cut':.8,'d_max_mm':.5,'polar_abs_mu_min':.6,
         'provenance':{},'qp':{},'mesh_generation_attempts':0,'FEM_attempts':0}
    begin=time.perf_counter()
    for name,(path,sha) in FILES.items():
        h=hashlib.sha256(path.read_bytes()).hexdigest()
        if h!=sha:raise ValueError('pinned SHA mismatch '+name)
        out['provenance'][name]=sha
        out['qp'][name]={}
        for order in (3,7,9):
            out['qp'][name][str(order)]=analyze(path,direct,order)
            print(f'{name} order {order} done',flush=True)
    out['ratios']={}
    for order in ('3','7','9'):
        out['ratios'][order]={}
        for side in ('north','south'):
            a=out['qp']['M1'][order][side]['Veff_m3']
            b=out['qp']['M2_P10ID'][order][side]['Veff_m3']
            out['ratios'][order][side]={'M2_over_M1':b/a if a and b else None,
                                       'M1_Neff':out['qp']['M1'][order][side]['N_eff'],
                                       'M2_Neff':out['qp']['M2_P10ID'][order][side]['N_eff']}
    out['wall_seconds']=round(time.perf_counter()-begin,3)
    print(json.dumps(out,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
