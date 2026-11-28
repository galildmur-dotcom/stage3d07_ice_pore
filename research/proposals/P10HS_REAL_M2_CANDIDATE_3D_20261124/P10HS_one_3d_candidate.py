#!/usr/bin/env python3
"""One bounded original CAD 3D candidate with direct mechanical 4D C2 κ.

This creates a *candidate*, never accepted M2 and never FEM. Require an
independent curved Tet10 343/729-QP D-025 audit against actual pinned M1.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import time
import traceback

import numpy as np

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from p10hk_direct_kappa_callback_benchmark import DirectKappa
import p10hc_continuous_kappa_geo as field

GEO_SHA='f1227074616375c28706e1e55cddde370b9a9fca069aab88513b4313c8239f51'
LIMIT=4000000
MESH=HERE/'P10HS_M2_CANDIDATE_UNVERIFIED.msh'
REPORT=HERE/'P10HS_WORKER_RESULT.json'
ERROR=HERE/'P10HS_WORKER_ERROR.txt'


def main():
    if hashlib.sha256((HERE/'P10GT_HXT10.geo').read_bytes()).hexdigest()!=GEO_SHA:
        raise RuntimeError('P10HS_STOP: pinned original P10GT GEO mismatch')
    import gmsh
    if gmsh.__version__!='4.15.2':raise RuntimeError('P10HS_STOP: Gmsh 4.15.2 required')
    source,v25,_,_,_,qa=field.load_centers(
        HERE/'P10HA_SPATIAL_KAPPA_1200_BINS.csv',HERE/'P10HA_KAPPA_QA.json')
    direct=DirectKappa(source,v25,qa['mechanical_only_25_36_shared_smoothing_denominator'])
    gmsh.initialize()
    calls=0;overflow=False;inside_pore=0;kmin=1.;kmax=0.;lcmin=float('inf');lcmax=0.
    by_dim={}
    try:
        gmsh.option.setNumber('General.Terminal',1)
        gmsh.open(str(HERE/'P10GT_HXT10.geo'))
        if len(gmsh.model.getEntities(3))!=2:
            raise RuntimeError('P10HS_STOP: expected original two-volume CAD')
        if abs(gmsh.option.getNumber('Mesh.MeshSizeFactor')-.9378887276834518)>1e-12:
            raise RuntimeError('P10HS_STOP: pinned original global size factor changed')

        def callback(dim,tag,x,y,z,lc):
            nonlocal calls,overflow,inside_pore,kmin,kmax,lcmin,lcmax
            calls+=1
            if calls>LIMIT:
                overflow=True
                return lc
            r=((x-field.C[0])**2+(y-field.C[1])**2+(z-field.C[2])**2)**.5
            if r<field.PORE_R-1e-12:
                inside_pore+=1
                return lc # excluded; any such probe invalidates candidate
            k=direct.kappa(x,y,z)
            h=lc*(1-field.ALPHA*k)**(1/3)
            kmin=min(kmin,k);kmax=max(kmax,k)
            lcmin=min(lcmin,lc);lcmax=max(lcmax,lc)
            by_dim[str(dim)]=by_dim.get(str(dim),0)+1
            return h

        gmsh.model.mesh.setSizeCallback(callback)
        start=time.perf_counter()
        gmsh.model.mesh.generate(3)  # ONLY single candidate, NO FEM
        elapsed=time.perf_counter()-start
        gmsh.model.mesh.removeSizeCallback()
        if overflow:raise RuntimeError('P10HS_STOP: callback count limit exceeded')
        if inside_pore:raise RuntimeError('P10HS_STOP: callback requested '+str(inside_pore)+' pore interior points')
        node_ids,coords,_=gmsh.model.mesh.getNodes()
        arr=np.asarray(coords).reshape(-1,3)
        r=np.linalg.norm(arr-np.array(field.C),axis=1)
        if np.any(r<field.PORE_R-1e-12):
            raise RuntimeError('P10HS_STOP: mesh node inside pore')
        types,element_ids,connections=gmsh.model.mesh.getElements(3)
        by_type={str(t):len(ids) for t,ids in zip(types,element_ids)}
        if 11 not in types or any(t!=11 for t in types):
            raise RuntimeError('P10HS_STOP: 3D mesh must contain Tet10 only')
        tet_count=sum(map(len,element_ids))
        if tet_count<100:raise RuntimeError('P10HS_STOP: too few 3D tetrahedra')
        gmsh.write(str(MESH))
        mesh_sha=hashlib.sha256(MESH.read_bytes()).hexdigest()
        report={'protocol':'P10HS_R1_ONE_REAL_P10GT_CAD_3D_KAPPA_M2_CANDIDATE',
                'status':'NATIVE_3D_CANDIDATE_ONLY_PENDING_INDEPENDENT_D025_QP343_729',
                'gmsh_version':gmsh.__version__,
                'original_geo_sha256':GEO_SHA,
                'original_M1_mesh_sha256':'47460969be26c2bd0a15e0b1425806fa350aa09aa2b4ac9f80605b433fc65ca7',
                'source_mechanical_only_signed_M0_M1_4D':True,
                'alpha_nominal':field.ALPHA,
                'nominal_volume_ratio_at_kappa1':1-field.ALPHA,
                'gmsh_native_3d_wall_s':round(elapsed,3),
                'callback_count':calls,'callback_counts_by_dimension':by_dim,
                'callback_kappa_min_max':[kmin,kmax],
                'callback_lc_min_max':[lcmin,lcmax],
                'callbacks_inside_pore':inside_pore,
                'mesh_nodes':len(node_ids),'tet10_count':tet_count,
                'volume_element_types':by_type,
                'candidate_msh_sha256':mesh_sha,'candidate_msh_bytes':MESH.stat().st_size,
                'candidate_is_accepted_M2':False,
                'independent_Tet10_curved_QP343_729_and_D025_GO':False,
                'native_FEM_attempts':0}
        REPORT.write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
        print(report['status'],'nodes',len(node_ids),'Tet10',tet_count,'callback',calls)
    finally:
        gmsh.finalize()


if __name__=='__main__':
    try:main()
    except Exception:
        ERROR.write_text(traceback.format_exc(),encoding='utf-8')
        print('P10HS_WORKER_STOP',ERROR)
        sys.exit(2)
