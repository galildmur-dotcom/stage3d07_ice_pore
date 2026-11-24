#!/usr/bin/env python3
"""P10HJ: read-only real M1 quadratic Tet10 κ interpolation and curved-map QA.

No Gmsh invocation, new mesh, FEM or thermal adaptation. Uses original 10
geometric and 10 mechanical-only κ samples in official Gmsh Tet10 node order.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'research/proposals/P10HE_POSTVIEW_SOURCE_ONLY_20261124'),str(ROOT/'scripts')]
import P10HE_build_view as he
import p10hc_continuous_kappa_geo as field

ZIP_SHA='7bff029865bd69e12b8302a9f65b6159d61f58163300fdee81555954988a6ac3'
EDGES=((0,1),(1,2),(2,0),(3,0),(3,2),(3,1))
# Reference barycentrics: centroid, four near-vertex samples, and six edge-biased
# samples. All points are strictly inside the original *curved* Tet10 mapping.
QUERIES=np.array([[.25]*4]+[
    [.7 if i==j else .1 for i in range(4)] for j in range(4)]+[
    [.42 if i in pair else .08 for i in range(4)] for pair in EDGES])


def need(ok,msg):
    if not ok:raise RuntimeError('P10HJ_STOP: '+msg)


def shape(l):
    l=np.asarray(l,float)
    corners=l*(2*l-1)
    edges=np.stack([4*l[...,a]*l[...,b] for a,b in EDGES],axis=-1)
    return np.concatenate((corners,edges),axis=-1)


def describe(v):
    v=np.asarray(v,float)
    return {'count':int(len(v)),'median':float(np.median(v)),
            'p95':float(np.percentile(v,95)),'p99':float(np.percentile(v,99)),
            'max':float(np.max(v)),'above_0p05':int(np.count_nonzero(v>.05))}


def main(path):
    need(hashlib.sha256(path.read_bytes()).hexdigest()==ZIP_SHA,'pinned M1 evidence SHA mismatch')
    nodes,tets=he.mesh_from_zip(path)
    p=ROOT/'research/evidence/P10HA_KAPPA_SOURCE_PILOT_20261124'
    src,v25,_,_,_,qa=field.load_centers(p/'P10HA_SPATIAL_KAPPA_1200_BINS.csv',p/'P10HA_KAPPA_QA.json')
    den=qa['mechanical_only_25_36_shared_smoothing_denominator']
    ids=np.array(sorted(nodes))
    cart=np.array([nodes[i] for i in ids])
    kval=field.rbf_at_points(src,v25,field.physical_query(cart),den)
    byid=dict(zip(ids,kval))
    x10=np.array([[nodes[int(i)] for i in t] for t in tets])
    k10=np.array([[byid[int(i)] for i in t] for t in tets])
    # Nodal exactness with true ten-node Lagrange shape functions.
    nodal=np.array([[1 if i==j else 0 for i in range(4)] for j in range(4)]+
                    [[.5 if i in pair else 0 for i in range(4)] for pair in EDGES])
    Snode=shape(nodal)
    need(np.max(abs(Snode-np.eye(10)))<1e-13,'Tet10 Kronecker basis identity')
    S=shape(QUERIES)
    X=np.einsum('qi,tik->tqk',S,x10)
    quadratic=np.einsum('qi,ti->tq',S,k10)
    # Corner-only linear field at the same mapped physical coordinates. This is
    # a consistency comparator, NOT actual Gmsh spatial probing of old view.
    old=np.einsum('qi,ti->tq',QUERIES,k10[:,:4])
    radius=np.linalg.norm(X-np.asarray(field.C),axis=2)
    valid=radius>=field.PORE_R-1e-12
    exact=np.full(quadratic.shape,np.nan)
    exact[valid]=field.rbf_at_points(src,v25,field.physical_query(X[valid]),den)
    e2=np.abs(quadratic[valid]-exact[valid])
    e1=np.abs(old[valid]-exact[valid])
    mu=(X[:,:,2]-.03)/radius
    mask={'north_mu_ge_0p8':mu>=.8,'south_mu_le_m0p8':mu<=-.8,
          'nonpolar_abs_mu_lt_0p8':abs(mu)<.8,
          'near_wall_d_le_0p1mm':(radius-field.PORE_R)<=1e-4}
    groups={k:{'quadratic':describe(np.abs(quadratic[valid&m]-exact[valid&m])),
               'corner_only':describe(np.abs(old[valid&m]-exact[valid&m]))}
            for k,m in mask.items() if np.any(valid&m)}
    r={'protocol':'P10HJ_R1_REAL_M1_CURVED_TET10_QUADRATIC_SOURCE_ONLY',
       'status':'INDEPENDENT_FIELD_INTERPOLATION_QA_ONLY_NO_GMSH_MESH_NO_FEM',
       'pinned_M1_evidence_sha256':ZIP_SHA,'nodes':len(nodes),'tet10':len(tets),
       'samples_per_tet10':len(QUERIES),'sample_points_total':int(X.shape[0]*X.shape[1]),
       'sample_points_inside_pore_excluded':int(np.count_nonzero(~valid)),
       'quadratic_kappa_abs_error':describe(e2),
       'corner_linear_kappa_abs_error_at_same_curved_reference_points':describe(e1),
       'quadratic_kappa_range_all_samples':[float(quadratic.min()),float(quadratic.max())],
       'quadratic_kappa_outside_0_to_1_count':int(np.count_nonzero((quadratic<0)|(quadratic>1))),
       'groups':groups,'Gmsh_postview_field_eval_verified':False,
       'geometry_note':'Tet10 isoparametric polynomial geometry is used at every sample; not straight chords.',
       'next_gate':'Gmsh model-based NodeData / high-order PostView native probe; do not launch M2',
       'native_1d_2d_3d_FEM_attempts':0}
    print(json.dumps(r,ensure_ascii=False,indent=2))


if __name__=='__main__':main(Path(sys.argv[1]))
