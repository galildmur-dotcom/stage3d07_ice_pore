#!/usr/bin/env python3
"""P10HU independent real M1 vs P10HT candidate curved Tet10 QP343/729.

Read-only: no mesh generation, FEM, or physical solver. Original pinned M1 and
mechanical 4D κ remain unchanged. Rejects missing physical surface or inversion.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import zipfile

import numpy as np

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import p10gj_offline_343_729_adjudicate as qp
import p10hc_continuous_kappa_geo as field

M1_ZIP_SHA='7bff029865bd69e12b8302a9f65b6159d61f58163300fdee81555954988a6ac3'
M1_MSH_SHA='47460969be26c2bd0a15e0b1425806fa350aa09aa2b4ac9f80605b433fc65ca7'
M2_ZIP_SHA='92079e8c1dd7bcf99b34ce973c1a9960c189b4fd5a9e17981a46a90b03dc7883'
M2_MSH_SHA='53de9d5c5ad28c677f21f5b660acd75e497b8a27b3dd93173e4f2de678937d58'


def need(ok,msg):
    if not ok:raise RuntimeError('P10HU_INDEPENDENT_STOP: '+msg)


def load_m1(path):
    raw=path.read_bytes()
    need(hashlib.sha256(raw).hexdigest()==M1_ZIP_SHA,'M1 original evidence fingerprint')
    with zipfile.ZipFile(path) as z:
        need(z.testzip() is None,'M1 CRC')
        mesh=z.read('P10GT_HXT10.msh')
    need(hashlib.sha256(mesh).hexdigest()==M1_MSH_SHA,'M1 pinned mesh fingerprint')
    return qp.read_msh(mesh)


def load_m2(path):
    raw=path.read_bytes()
    need(hashlib.sha256(raw).hexdigest()==M2_ZIP_SHA,'M2 candidate evidence fingerprint')
    with zipfile.ZipFile(path) as z:
        need(z.testzip() is None,'M2 CRC')
        report=json.loads(z.read('P10HT_WORKER_RESULT.json'))
        guard=json.loads(z.read('P10HT_GUARD_RESULT.json'))
        need(guard['status']=='WORKER_FINISHED' and guard['exit_code']==0,'M2 native guard')
        need(report['status']=='NATIVE_3D_CANDIDATE_SAVED_PENDING_INDEPENDENT_D025','M2 native status')
        need(report['accepted_M2'] is False and report['FEM_attempts']==0,'M2 prohibited GO/FEM')
        need(report['physical_mesh_nodes_inside_pore']==0,'native physical node guard')
        mesh=z.read('P10HT_M2_CANDIDATE_UNVERIFIED.msh')
    need(hashlib.sha256(mesh).hexdigest()==M2_MSH_SHA,'M2 candidate mesh SHA')
    return (*qp.read_msh(mesh),report)


def compact_stat(a):
    x=np.asarray(a,float)
    if not len(x):return {'count':0}
    return {'count':int(len(x)),'median':float(np.median(x)),
            'p05':float(np.percentile(x,5)),'p95':float(np.percentile(x,95)),
            'min':float(np.min(x)),'max':float(np.max(x))}


def kappa_groups(nodes,tets,volume):
    p=HERE.parent/'research/evidence/P10HA_KAPPA_SOURCE_PILOT_20261124'
    src,v25,_,_,_,qa=field.load_centers(p/'P10HA_SPATIAL_KAPPA_1200_BINS.csv',p/'P10HA_KAPPA_QA.json')
    den=qa['mechanical_only_25_36_shared_smoothing_denominator']
    # Curved isoparametric tetra reference centroid; ten actual coordinates.
    L=np.array([[.25,.25,.25,.25]])
    N=np.concatenate((L*(2*L-1),np.array([[4*L[0,i]*L[0,j] for i,j in qp.EDGE]])),axis=1)[0]
    x=np.einsum('ni,nij->nj',np.ones((len(tets),10))*N[None,:],nodes[tets])
    q=field.rbf_at_points(src,v25,field.physical_query(x),den)
    # κ at true curved Tet10 nodes is essential: peak κ can live on the
    # physical wall even when NO element-centroid sample reaches κ>=0.8.
    used=np.unique(tets)
    nodal=field.rbf_at_points(src,v25,field.physical_query(nodes[used]),den)
    bynode=np.zeros(len(nodes));bynode[used]=nodal
    nodal_max=bynode[tets].max(axis=1)
    node_r=np.linalg.norm(nodes[tets]-np.array(field.C),axis=2)
    true_wall=np.any(abs(node_r-field.PORE_R)<=1e-10,axis=1)
    off=x-np.asarray(field.C)
    radius=np.linalg.norm(off,axis=1)
    mu=off[:,2]/radius
    bins={'north_wall_d_le_0p5mm':(mu>=.8)&(radius-field.PORE_R<=.0005),
          'south_wall_d_le_0p5mm':(mu<=-.8)&(radius-field.PORE_R<=.0005),
          'nonpolar_wall_d_le_0p5mm':(abs(mu)<.8)&(radius-field.PORE_R<=.0005),
          'high_kappa_ge_0p8':q>=.8,
          'touching_kappa_node_ge_0p8':nodal_max>=.8,
          'touching_pore_wall_with_kappa_node_ge_0p8':true_wall&(nodal_max>=.8),
          'touching_pore_wall_with_kappa_node_ge_0p5':true_wall&(nodal_max>=.5),
          'mid_kappa_0p5_0p8':(q>=.5)&(q<.8),
          'low_kappa_lt_0p1':q<.1,
          'all':np.ones(len(q),bool)}
    return {name:{'Tet10':int(mask.sum()),'kappa':compact_stat(q[mask]),
                  'curved_volume_per_tet_m3':compact_stat(volume[mask]),
                  'total_curved_volume_m3':float(volume[mask].sum())}
            for name,mask in bins.items()}


def evaluate(path1,path2):
    n1,t1,s1=load_m1(path1)
    n2,t2,s2,native=load_m2(path2)
    need(set(s1)==set(s2)==set(range(2,10)),'physical Tri6 group coverage changed')
    results={}
    for label,nodes,tets in [('M1',n1,t1),('candidate',n2,t2)]:
        vol27,j27=qp.baseline_volumes(nodes,tets)
        a=qp.sample(nodes,tets,vol27,7)
        b=qp.sample(nodes,tets,vol27,9)
        need(a['min_detJ']>0 and b['min_detJ']>0,'curved Tet10 Jacobian not positive')
        results[label]={'nodes':len(nodes)-1,'tet10':len(tets),
            'curved_volume_total_m3_343':a['total_volume'],
            'curved_volume_total_m3_729':b['total_volume'],
            'volume_closure_729_rel':b['total_volume']/qp.CAD_VOL-1,
            'min_detJ_27_343_729':[j27,a['min_detJ'],b['min_detJ']],
            'effective_Veff_343':a['V_eff'],'effective_Veff_729':b['V_eff'],
            'signed_region_volume_729':b['region_volume'],
            'signed_region_neff_729':b['N_eff'],
            'groups_centroid_kappa':kappa_groups(nodes,tets,vol27)}
    base=results['M1'];new=results['candidate']
    ratio729=new['effective_Veff_729']/base['effective_Veff_729']
    ratio343=new['effective_Veff_343']/base['effective_Veff_343']
    delta=float(np.max(abs(ratio729-ratio343)))
    rows=[]
    for i in range(18):
        rd,pm=divmod(i//2,3);hem='south' if i%2 else 'north'
        rows.append({'radial_zone':qp.RADS[rd], 'polar_zone':qp.POLS[pm],
                     'hemisphere':hem,'M1_Neff_729':float(base['signed_region_neff_729'][i]),
                     'candidate_Neff_729':float(new['signed_region_neff_729'][i]),
                     'candidate_over_M1_effective_V729':float(ratio729[i]),
                     'candidate_over_M1_effective_V343':float(ratio343[i])})
    grouping={}
    for key in base['groups_centroid_kappa']:
        a=base['groups_centroid_kappa'][key];b=new['groups_centroid_kappa'][key]
        m=a['curved_volume_per_tet_m3']['median'] if a['Tet10'] else None
        n=b['curved_volume_per_tet_m3']['median'] if b['Tet10'] else None
        grouping[key]={'M1_Tet10':a['Tet10'],'candidate_Tet10':b['Tet10'],
          'M1_median_curved_volume_m3':m,'candidate_median_curved_volume_m3':n,
          'median_Vcandidate_over_VM1':n/m if m and n else None,
          'M1_kappa':a['kappa'],'candidate_kappa':b['kappa']}
    checks={'original_and_candidate_Tet10_343_729_detJ_positive':True,
            'both_mesh_volume_closure_729_under_0p5percent':all(
                 abs(results[k]['volume_closure_729_rel'])<.005 for k in ('M1','candidate')),
            'max_18_signed_region_QV343_729_delta_le_0p02':delta<=.02,
            'actual_global_mean_tet_volume_ratio_in_0p80_to_1':.8<=len(t1)/len(t2)<=1,
            'high_kappa_median_volume_in_0p75_to_0p85':(
                 grouping['high_kappa_ge_0p8']['median_Vcandidate_over_VM1'] is not None
                 and .75<=grouping['high_kappa_ge_0p8']['median_Vcandidate_over_VM1']<=.85)}
    def serial(v):
        if isinstance(v,np.ndarray):return v.tolist()
        raise TypeError(type(v))
    result={'protocol':'P10HU_REAL_P10HT_VS_PINNED_M1_INDEPENDENT_CURVED_QP343_729',
            'M1_evidence_sha256':M1_ZIP_SHA,
            'candidate_evidence_sha256':M2_ZIP_SHA,
            'native_ghost_probes':native['nonphysical_pore_probe_count'],
            'native_mesh_nodes_inside_pore':native['physical_mesh_nodes_inside_pore'],
            'pore_wall_tri6_count':s1.get(8),
            'M1':base,'candidate':new,
            'global_mean_tet_volume_ratio':len(t1)/len(t2),
            'signed18_candidate_over_M1':rows,
            'signed18_Q343_Q729_max_delta':delta,
            'kappa_centroid_local_groups':grouping,
            'checks':checks,
            'D025_3D_accepted':False,
            'FEM_attempts':0}
    return json.loads(json.dumps(result,default=serial))


if __name__=='__main__':
    r=evaluate(Path(sys.argv[1]),Path(sys.argv[2]))
    print(json.dumps(r,indent=2,ensure_ascii=False))
