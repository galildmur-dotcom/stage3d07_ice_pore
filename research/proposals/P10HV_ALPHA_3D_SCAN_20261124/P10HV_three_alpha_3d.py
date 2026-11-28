#!/usr/bin/env python3
"""P10HV: three predefined original-CAD 3D candidate alpha scans, no FEM.

α = 0.15, 0.20, 0.25; pinned signed 4D κ and CAD fixed. All candidates
remain unapproved until independent curved Tet10 QP343/729 vs pinned M1.
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
ALPHAS=(.15,.20,.25)
MAX_EVALS=6000000
REPORT=HERE/'P10HV_WORKER_RESULT.json'
ERROR=HERE/'P10HV_WORKER_ERROR.txt'


def main():
    if hashlib.sha256((HERE/'P10GT_HXT10.geo').read_bytes()).hexdigest()!=GEO_SHA:
        raise RuntimeError('P10HV_STOP: original CAD GEO fingerprint mismatch')
    import gmsh
    if gmsh.__version__!='4.15.2':raise RuntimeError('P10HV_STOP: pinned Gmsh 4.15.2 required')
    src,v25,_,_,_,qa=field.load_centers(
        HERE/'P10HA_SPATIAL_KAPPA_1200_BINS.csv',HERE/'P10HA_KAPPA_QA.json')
    direct=DirectKappa(src,v25,qa['mechanical_only_25_36_shared_smoothing_denominator'])
    gmsh.initialize()
    total_calls=0
    rows=[]
    try:
        gmsh.option.setNumber('General.Terminal',1)
        gmsh.open(str(HERE/'P10GT_HXT10.geo'))
        if len(gmsh.model.getEntities(3))!=2:
            raise RuntimeError('P10HV_STOP: expected 2 original ice CAD volumes')
        if abs(gmsh.option.getNumber('Mesh.MeshSizeFactor')-.9378887276834518)>1e-12:
            raise RuntimeError('P10HV_STOP: size factor mismatch')
        for case_no,alpha in enumerate(ALPHAS):
            if case_no:gmsh.model.mesh.clear()
            calls=0;ghost=0;max_depth=0.;center=0;overflow=False

            def cb(dim,tag,x,y,z,lc):
                nonlocal calls,ghost,max_depth,center,overflow,total_calls
                calls+=1;total_calls+=1
                if total_calls>MAX_EVALS:
                    overflow=True
                    return lc
                dx=x-field.C[0];dy=y-field.C[1];dz=z-field.C[2]
                r=(dx*dx+dy*dy+dz*dz)**.5
                if r<field.PORE_R-1e-12:
                    ghost+=1
                    max_depth=max(max_depth,(field.PORE_R-r)*1000)
                    if r<1e-15:
                        center+=1
                        return lc
                    q=field.PORE_R/r
                    k=direct.kappa(field.C[0]+q*dx,field.C[1]+q*dy,field.C[2]+q*dz)
                else:k=direct.kappa(x,y,z)
                return lc*(1-alpha*k)**(1/3)

            gmsh.model.mesh.setSizeCallback(cb)
            started=time.perf_counter()
            gmsh.model.mesh.generate(3)
            elapsed=time.perf_counter()-started
            gmsh.model.mesh.removeSizeCallback()
            if overflow:raise RuntimeError('P10HV_STOP: total callback limit')
            node_ids,coords,_=gmsh.model.mesh.getNodes()
            rr=np.linalg.norm(np.asarray(coords).reshape(-1,3)-np.asarray(field.C),axis=1)
            physical_inside=int(np.count_nonzero(rr<field.PORE_R-1e-12))
            if physical_inside:raise RuntimeError('P10HV_STOP: actual mesh node in pore')
            types,tags,_=gmsh.model.mesh.getElements(3)
            if set(map(int,types))!={11}:
                raise RuntimeError('P10HV_STOP: mixed/non-Tet10 3D types')
            nt=sum(map(len,tags))
            mesh=HERE/f'P10HV_ALPHA_{int(round(alpha*100)):02d}_M2_UNVERIFIED.msh'
            gmsh.write(str(mesh))
            row={'alpha':alpha,'status':'CANDIDATE_UNVERIFIED',
                 'nominal_local_volume_ratio_at_kappa1':1-alpha,
                 'native_3d_wall_s':round(elapsed,3),
                 'callback_count':calls,'ghost_queries':ghost,
                 'max_ghost_inward_mm':max_depth,'exact_pore_center_queries':center,
                 'physical_mesh_nodes_inside_pore':physical_inside,
                 'mesh_nodes':len(node_ids),'tet10':nt,
                 'mesh_filename':mesh.name,'mesh_sha256':hashlib.sha256(mesh.read_bytes()).hexdigest(),
                 'mesh_bytes':mesh.stat().st_size}
            rows.append(row)
            print('P10HV case',alpha,'Tet10',nt,'nodes',len(node_ids),'calls',calls,flush=True)
        report={'protocol':'P10HV_R1_PREDECLARED_THREE_ALPHA_3D_REAL_CAD_SCAN',
                'status':'THREE_NATIVE_3D_CANDIDATES_COMPLETE_NO_FEM_NOT_ACCEPTED',
                'original_geo_sha256':GEO_SHA,'gmsh_version':gmsh.__version__,
                'source':'unchanged signed M0/M1 4D mechanical κ C2',
                'alpha_cases':list(ALPHAS),'total_callback_count':total_calls,
                'results':rows,'accepted_M2':False,'FEM_attempts':0,
                'independent_QP343_729_D025_still_pending':True}
        REPORT.write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
        print('P10HV_ALL_CANDIDATES_COMPLETE_NO_FEM',flush=True)
    finally:gmsh.finalize()


if __name__=='__main__':
    try:main()
    except Exception:
        ERROR.write_text(traceback.format_exc(),encoding='utf-8')
        print('P10HV_WORKER_STOP',ERROR)
        sys.exit(2)
