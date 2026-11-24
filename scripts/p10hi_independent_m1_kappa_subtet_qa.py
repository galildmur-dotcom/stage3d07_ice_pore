#!/usr/bin/env python3
"""Read-only independent P10HG real M1 Tet10 κ interpolation/subdivision QA.

Does NOT create a mesh or native Gmsh/FEM run. Parses the pinned user's M1 ZIP,
checks old C0 corner-linear error, tests a fixed eight-subtet decomposition.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import zipfile
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'research/proposals/P10HE_POSTVIEW_SOURCE_ONLY_20261124'))
sys.path.insert(0,str(ROOT/'scripts'))
import P10HE_build_view as he
import p10hc_continuous_kappa_geo as field

EVIDENCE_SHA='7bff029865bd69e12b8302a9f65b6159d61f58163300fdee81555954988a6ac3'
M1_SHA='47460969be26c2bd0a15e0b1425806fa350aa09aa2b4ac9f80605b433fc65ca7'
PAIRS=((0,1),(1,2),(2,0),(3,0),(3,2),(3,1))
# Four corner subtets + a central octahedron split along diagonal (4,8).
SUBTETS=((0,4,6,7),(1,5,4,9),(2,6,5,8),(3,7,8,9),
         (4,5,6,8),(4,6,7,8),(4,7,9,8),(4,9,5,8))


def need(v,msg):
    if not v:raise RuntimeError('P10HI_INDEPENDENT_STOP: '+msg)


def stat(x):
    x=np.asarray(x,float)
    return {'count':int(x.size),'mean':float(x.mean()) if x.size else None,
            'median':float(np.median(x)) if x.size else None,
            'p95':float(np.percentile(x,95)) if x.size else None,
            'max':float(x.max()) if x.size else None,
            'above_0p05':int(np.count_nonzero(x>.05))}


def volume(vertices):
    return float(np.linalg.det(np.array([vertices[i]-vertices[0] for i in (1,2,3)])))/6


def main(evidence):
    need(hashlib.sha256(evidence.read_bytes()).hexdigest()==EVIDENCE_SHA,'M1 ZIP SHA')
    nodes,tets=he.mesh_from_zip(evidence)
    p=ROOT/'research/evidence/P10HA_KAPPA_SOURCE_PILOT_20261124'
    src,v25,v36,k25,k36,qa=field.load_centers(
        p/'P10HA_SPATIAL_KAPPA_1200_BINS.csv',p/'P10HA_KAPPA_QA.json')
    ids=np.array(sorted(nodes))
    cart=np.array([nodes[i] for i in ids])
    val=field.rbf_at_points(src,v25,field.physical_query(cart),
                qa['mechanical_only_25_36_shared_smoothing_denominator'])
    κ=dict(zip(ids,val))
    errors=[];xmid=[];k_mid=[];chord_offset=[]
    sub_ratios=[]; negative=0; ratio_min=10.;ratio_max=0.
    for t in tets:
        ten=np.array([nodes[int(i)] for i in t])
        parent=abs(volume(ten[:4]))
        need(parent>0,'zero parent tetra')
        subt=[volume(ten[list(vert)]) for vert in SUBTETS]
        # Absolute volumes, independent of orientation of fixed local tuples.
        subtotal=sum(abs(v) for v in subt)
        sub_ratios.append(subtotal/parent)
        negative+=sum(v<0 for v in subt)
        for i,(a,b) in enumerate(PAIRS):
            midx=ten[4+i];chord=.5*(ten[a]+ten[b])
            errors.append(abs(κ[int(t[4+i])]-.5*(κ[int(t[a])]+κ[int(t[b])])))
            xmid.append(midx)
            k_mid.append(κ[int(t[4+i])])
            chord_offset.append(float(np.linalg.norm(midx-chord)))
    errors=np.array(errors)
    xmid=np.array(xmid)
    k_mid=np.array(k_mid)
    chord_offset=np.array(chord_offset)
    dmm=(np.linalg.norm(xmid-np.array(field.C),axis=1)-field.PORE_R)*1000
    mu=(xmid[:,2]-.03)/np.linalg.norm(xmid-np.array(field.C),axis=1)
    masks={'north_mu_ge_0p8':mu>=.8,'south_mu_le_m0p8':mu<=-.8,
           'nonpolar_abs_mu_lt_0p8':abs(mu)<.8,
           'near_wall_d_le_0p1mm':dmm<=.1,
           'wall_0_to_0p02mm':dmm<=.02,
           'late_far_d_gt_2mm':dmm>2,
           'high_kappa_gt_0p5':k_mid>.5}
    bins={name:stat(errors[mask]) for name,mask in masks.items()}
    ratios=np.asarray(sub_ratios)
    # The original C2 field at *quarter-edge* positions tests how much
    # eight-subtet linear interpolation still under-resolves between nodes.
    qpos=[];qlinear=[]
    for t in tets:
        ten=np.array([nodes[int(i)] for i in t])
        for j,(a,b) in enumerate(PAIRS):
            vertex=ten[a];midedge=ten[4+j]
            qpos.append(.5*(vertex+midedge))
            qlinear.append(.5*(κ[int(t[a])]+κ[int(t[4+j])]))
    qpos=np.asarray(qpos)
    qradius=np.linalg.norm(qpos-np.array(field.C),axis=1)
    valid=qradius>=field.PORE_R-1e-12
    exact=field.rbf_at_points(src,v25,field.physical_query(qpos[valid]),
                qa['mechanical_only_25_36_shared_smoothing_denominator'])
    qerrors=np.abs(exact-np.asarray(qlinear)[valid])
    result={'protocol':'P10HI_R1_READ_ONLY_M1_3D_KAPPA_EIGHT_SUBTET_QA',
            'original_M1_evidence_sha256':EVIDENCE_SHA,'original_M1_msh_sha256':M1_SHA,
            'M1_nodes':len(ids),'M1_tet10':len(tets),
            'old_corner_only_mid_edge_error':stat(errors),
            'corner_only_error_groups':bins,
            'corner_only_mass_high_kappa_error_gt_0p05':int(np.count_nonzero((errors>.05)&(k_mid>.5))),
            'max_curved_midedge_vs_chord_mm':float(chord_offset.max()*1000),
            'median_curved_midedge_vs_chord_mm':float(np.median(chord_offset)*1000),
            'subtet_count':len(SUBTETS)*len(tets),
            'subtet_abs_volume_sum_over_corner_tet_volume':{
                'min':float(ratios.min()),'median':float(np.median(ratios)),
                'p95':float(np.percentile(ratios,95)),'max':float(ratios.max())},
            'subtet_signed_orientation_negative_count':negative,
            'eight_subtet_quarter_edge_error':stat(qerrors),
            'quarter_edge_test_ice_valid':int(np.count_nonzero(valid)),
            'quarter_edge_test_inside_pore_excluded':int(np.count_nonzero(~valid)),
            'unit_warning':'subtet volumes use straight corners/midpoints, not exact curved Tet10 mapping. This is source-only representation QA, not D-025 or mesh quality GO',
            'native_2d_3d_FEM_attempts':0}
    print(json.dumps(result,indent=2,ensure_ascii=False))


if __name__=='__main__':main(Path(sys.argv[1]))
