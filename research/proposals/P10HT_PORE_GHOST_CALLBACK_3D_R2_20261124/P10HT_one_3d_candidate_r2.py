#!/usr/bin/env python3
"""P10HT R2: one 3D candidate with nonphysical Gmsh pore-probe extension.

Physical C2 κ is EXACTLY unchanged for r>=R_pore; only size queries inside
the excluded cavity are radially projected to the wall for Gmsh's geometry
search. All physical mesh nodes must still lie in ice. No FEM or M2 acceptance.
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
MAX_CB=4000000
MESH=HERE/'P10HT_M2_CANDIDATE_UNVERIFIED.msh'
REPORT=HERE/'P10HT_WORKER_RESULT.json'
ERROR=HERE/'P10HT_WORKER_ERROR.txt'


def main():
    if hashlib.sha256((HERE/'P10GT_HXT10.geo').read_bytes()).hexdigest()!=GEO_SHA:
        raise RuntimeError('P10HT_STOP: original P10GT source fingerprint mismatch')
    import gmsh
    if gmsh.__version__!='4.15.2':raise RuntimeError('P10HT_STOP: Gmsh version not 4.15.2')
    source,v25,_,_,_,qa=field.load_centers(
        HERE/'P10HA_SPATIAL_KAPPA_1200_BINS.csv',HERE/'P10HA_KAPPA_QA.json')
    direct=DirectKappa(source,v25,qa['mechanical_only_25_36_shared_smoothing_denominator'])
    gmsh.initialize()
    calls=0;overflow=False;kmin=1.;kmax=0.
    inside_count=0;center_count=0;max_depth_mm=0.;ghost_samples=[];by_dim={}
    try:
        gmsh.option.setNumber('General.Terminal',1)
        gmsh.open(str(HERE/'P10GT_HXT10.geo'))
        if len(gmsh.model.getEntities(3))!=2:
            raise RuntimeError('P10HT_STOP: original two ice volumes absent')
        if abs(gmsh.option.getNumber('Mesh.MeshSizeFactor')-.9378887276834518)>1e-12:
            raise RuntimeError('P10HT_STOP: original size factor changed')

        def cb(dim,tag,x,y,z,lc):
            nonlocal calls,overflow,kmin,kmax,inside_count,center_count,max_depth_mm
            calls+=1
            if calls>MAX_CB:
                overflow=True
                return lc
            dx=x-field.C[0];dy=y-field.C[1];dz=z-field.C[2]
            r=(dx*dx+dy*dy+dz*dz)**.5
            if r<field.PORE_R-1e-12:
                inside_count+=1
                max_depth_mm=max(max_depth_mm,(field.PORE_R-r)*1000)
                if r<1e-15:
                    center_count+=1
                    if len(ghost_samples)<30:
                        ghost_samples.append([x,y,z,r,None,'CENTER_NO_DIRECTION_RETURN_BASE_LC'])
                    return lc
                # Extrapolate along the same radial direction only for
                # nonphysical Gmsh probes, NOT for physical ice material.
                q=field.PORE_R/r
                xp=field.C[0]+q*dx;yp=field.C[1]+q*dy;zp=field.C[2]+q*dz
                k=direct.kappa(xp,yp,zp)
                if len(ghost_samples)<30:
                    ghost_samples.append([x,y,z,r,k,'PROJECTED_TO_PORE_WALL'])
            else:
                k=direct.kappa(x,y,z)
            by_dim[str(dim)]=by_dim.get(str(dim),0)+1
            kmin=min(kmin,k);kmax=max(kmax,k)
            return lc*(1-field.ALPHA*k)**(1/3)

        gmsh.model.mesh.setSizeCallback(cb)
        begin=time.perf_counter()
        gmsh.model.mesh.generate(3)  # ONE bounded actual 3D candidate only
        wall=time.perf_counter()-begin
        gmsh.model.mesh.removeSizeCallback()
        if overflow:raise RuntimeError('P10HT_STOP: callback limit exceeded')
        tags,coord,_=gmsh.model.mesh.getNodes()
        points=np.asarray(coord).reshape(-1,3)
        rr=np.linalg.norm(points-np.array(field.C),axis=1)
        actual_inside=int(np.count_nonzero(rr<field.PORE_R-1e-12))
        if actual_inside:
            raise RuntimeError('P10HT_STOP: '+str(actual_inside)+' actual mesh nodes inside pore')
        types,ids,_=gmsh.model.mesh.getElements(3)
        if set(map(int,types))!={11}:
            raise RuntimeError('P10HT_STOP: 3D elements not exclusively Tet10')
        ntet=sum(map(len,ids))
        if ntet<100:raise RuntimeError('P10HT_STOP: unreasonable Tet10 count')
        gmsh.write(str(MESH))
        report={'protocol':'P10HT_R2_REAL_M1_C2_MECHANICAL_GMSH_PORE_GHOST_3D_CANDIDATE',
                'status':'NATIVE_3D_CANDIDATE_SAVED_PENDING_INDEPENDENT_D025',
                'gmsh_version':gmsh.__version__,
                'original_geo_sha256':GEO_SHA,
                'original_M1_msh_sha256':'47460969be26c2bd0a15e0b1425806fa350aa09aa2b4ac9f80605b433fc65ca7',
                'real_ice_kappa_changed':False,
                'ghost_policy':'radial constant extension to wall ONLY for Gmsh query r<R_pore; center returns base lc',
                'callback_count':calls,'callback_by_dimension':by_dim,
                'nonphysical_pore_probe_count':inside_count,
                'nonphysical_pore_center_probe_count':center_count,
                'deepest_nonphysical_probe_mm':max_depth_mm,
                'first_30_nonphysical_probe_samples':ghost_samples,
                'native_3d_wall_s':round(wall,3),
                'physical_mesh_nodes_inside_pore':actual_inside,
                'mesh_nodes':len(tags),'tet10_count':ntet,
                'callback_kappa_min_max':[kmin,kmax],
                'nominal_volume_ratio_at_kappa1':1-field.ALPHA,
                'candidate_mesh_sha256':hashlib.sha256(MESH.read_bytes()).hexdigest(),
                'candidate_mesh_bytes':MESH.stat().st_size,
                'accepted_M2':False,'curved_Tet10_QP343_729_D025_GO':False,
                'FEM_attempts':0}
        REPORT.write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
        print(report['status'],'Tet10',ntet,'nodes',len(tags),'ghost probes',inside_count)
    finally:
        gmsh.finalize()


if __name__=='__main__':
    try:main()
    except Exception:
        ERROR.write_text(traceback.format_exc(),encoding='utf-8')
        print('P10HT_WORKER_STOP',ERROR)
        sys.exit(2)
