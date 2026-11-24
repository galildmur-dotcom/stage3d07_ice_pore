#!/usr/bin/env python3
"""One original CAD 2D surface-only adaptive callback attempt, no 3D/FEM.

Native 2D Tri6 surface QA at actual nodes, including north/south/nonpolar pore.
Only run through external P10HQ_guard.py timeout=180 s.
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
MAX_CALLS=1000000
REPORT=HERE/'P10HQ_RESULT.json'
ERROR=HERE/'P10HQ_WORKER_ERROR.txt'


def stat(x):
    a=np.asarray(x,float)
    if not len(a):return {'count':0}
    return {'count':int(len(a)),'min':float(a.min()),'median':float(np.median(a)),
            'p95':float(np.percentile(a,95)),'max':float(a.max())}


def main():
    if hashlib.sha256((HERE/'P10GT_HXT10.geo').read_bytes()).hexdigest()!=GEO_SHA:
        raise RuntimeError('P10HQ_STOP: original P10GT source SHA')
    import gmsh
    if gmsh.__version__!='4.15.2':raise RuntimeError('P10HQ_STOP: Python Gmsh version')
    src,v25,_,_,_,qa=field.load_centers(HERE/'P10HA_SPATIAL_KAPPA_1200_BINS.csv',
                                       HERE/'P10HA_KAPPA_QA.json')
    direct=DirectKappa(src,v25,qa['mechanical_only_25_36_shared_smoothing_denominator'])
    gmsh.initialize()
    n=0;overflow=False; callbacks=[];klo=1.;khi=0.; lc_lo=float('inf');lc_hi=0.
    try:
        gmsh.option.setNumber('General.Terminal',1)
        gmsh.open(str(HERE/'P10GT_HXT10.geo'))
        entities={str(d):len(gmsh.model.getEntities(d)) for d in range(4)}
        if int(entities['3'])!=2 or int(entities['2'])!=8:
            raise RuntimeError('P10HQ_STOP: unexpected original CAD topology')

        def cb(dim,tag,x,y,z,lc):
            nonlocal n,overflow,klo,khi,lc_lo,lc_hi
            n+=1
            if n>MAX_CALLS:
                overflow=True
                return lc
            k=direct.kappa(x,y,z)
            h=lc*(1-field.ALPHA*k)**(1/3)
            klo=min(klo,k);khi=max(khi,k)
            lc_lo=min(lc_lo,lc);lc_hi=max(lc_hi,lc)
            if len(callbacks)<200:callbacks.append([dim,tag,x,y,z,lc,k,h])
            return h

        gmsh.model.mesh.setSizeCallback(cb)
        before=time.perf_counter()
        gmsh.model.mesh.generate(2)  # exactly one surface 2D run, NO 3D
        elapsed=time.perf_counter()-before
        gmsh.model.mesh.removeSizeCallback()
        if overflow:raise RuntimeError('P10HQ_STOP: >1m callback guard')

        ids,coord,_=gmsh.model.mesh.getNodes()
        xyz=dict(zip(map(int,ids),np.asarray(coord).reshape(-1,3)))
        physical={}
        node_of_wall=set()
        n_tri=0
        for _,surf in gmsh.model.getEntities(2):
            ptags=gmsh.model.getPhysicalGroupsForEntity(2,surf)
            phy=','.join(map(str,ptags)) or 'UNMARKED'
            types,elem_tags,connectivity=gmsh.model.mesh.getElements(2,surf)
            localtri=0
            for tid,tags,flat in zip(types,elem_tags,connectivity):
                if tid not in (2,9):
                    raise RuntimeError('P10HQ_STOP: unexpected element type '+str(tid))
                width=3 if tid==2 else 6
                con=np.asarray(flat,dtype=np.int64).reshape(-1,width)
                localtri+=len(con)
                if 8 in ptags:
                    node_of_wall.update(map(int,con.ravel()))
            n_tri+=localtri
            physical.setdefault(phy,{'surface_tags':[],'triangle_count':0})
            physical[phy]['surface_tags'].append(int(surf))
            physical[phy]['triangle_count']+=localtri

        if not node_of_wall:raise RuntimeError('P10HQ_STOP: no physical PORE_WALL surface 8 triangles')
        wall_xyz=np.array([xyz[i] for i in sorted(node_of_wall)])
        radius=np.linalg.norm(wall_xyz-np.array(field.C),axis=1)
        mu=(wall_xyz[:,2]-field.C[2])/radius
        outside=radius<field.PORE_R-1e-12
        if np.any(outside):
            raise RuntimeError('P10HQ_STOP: actual wall nodes inside pore')
        vals=np.array([direct.kappa(*v) for v in wall_xyz])
        masks={'north_mu_ge_0p8':mu>=.8,'south_mu_le_m0p8':mu<=-.8,
               'nonpolar_abs_mu_lt_0p8':abs(mu)<.8}
        groups={g:{'kappa':stat(vals[mask]),
                   'distance_from_ideal_pore_wall_mm':stat(abs(radius[mask]-field.PORE_R)*1000)}
                for g,mask in masks.items()}
        report={'protocol':'P10HQ_R1_ONE_BOUNDED_REAL_P10GT_CAD_2D_CALLBACK',
                'status':'REAL_CAD_2D_CALLBACK_FINISHED_NEEDS_INDEPENDENT_QA',
                'gmsh_version':gmsh.__version__,'original_geo_sha256':GEO_SHA,
                'CAD_entities_by_dimension':entities,'wall_s':round(elapsed,3),
                'callback_count':n,'callback_kappa_min_max':[klo,khi],
                'callback_lc_min_max':[lc_lo,lc_hi],
                'all_mesh_nodes':len(ids),'triangles_total':n_tri,
                'surface_triangles_by_physical_tag':physical,
                'pore_wall_nodes':len(node_of_wall),
                'pore_wall_groups':groups,
                'first_200_callbacks':callbacks,
                'no_native_3D_or_FEM':True,'no_M2':True,
                'D025_343_729_GO':False}
        REPORT.write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
        print(report['status'],'callbacks',n,'triangles',n_tri,'wall_nodes',len(node_of_wall))
    finally:
        gmsh.finalize()


if __name__=='__main__':
    try:main()
    except Exception:
        ERROR.write_text(traceback.format_exc(),encoding='utf-8')
        print('P10HQ_WORKER_STOP',ERROR)
        sys.exit(2)
