#!/usr/bin/env python3
"""Two matched native 2D surface meshes, baseline vs direct κ, original CAD.

No 3D, no FEM, no M2, no .msh writes. External guard kills at 180 s.
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

SHA='f1227074616375c28706e1e55cddde370b9a9fca069aab88513b4313c8239f51'
REPORT=HERE/'P10HR_RESULT.json'
ERROR=HERE/'P10HR_WORKER_ERROR.txt'
MAX_CALLBACK=500000


def stats(v):
    a=np.asarray(v,float)
    if not len(a):return {'count':0}
    return {'count':int(len(a)),'mean':float(a.mean()),
            'median':float(np.median(a)),'p05':float(np.percentile(a,5)),
            'p95':float(np.percentile(a,95)),'max':float(a.max())}


def audit(gmsh,label,direct,call_count,elapsed):
    ids,coords,_=gmsh.model.mesh.getNodes()
    xyz=dict(zip(map(int,ids),np.asarray(coords).reshape(-1,3)))
    tri_count=0; wall_tri=[]; wall_nodes=set();by_physical={}
    for _,surf in gmsh.model.getEntities(2):
        groups=gmsh.model.getPhysicalGroupsForEntity(2,surf)
        types,_,flat=gmsh.model.mesh.getElements(2,surf)
        for typ,values in zip(types,flat):
            if typ not in (2,9):raise RuntimeError('P10HR_STOP: non-triangle surface element')
            w=3 if typ==2 else 6
            con=np.asarray(values,dtype=np.int64).reshape(-1,w)
            tri_count+=len(con)
            for p in groups:by_physical[str(p)]=by_physical.get(str(p),0)+len(con)
            if 8 in groups:
                wall_tri.extend(con[:,:3].tolist())
                wall_nodes.update(map(int,con.ravel()))
    if not wall_tri:raise RuntimeError('P10HR_STOP: no real pore wall Tri6')
    wall_xyz=np.asarray([xyz[i] for i in sorted(wall_nodes)])
    wall_r=np.linalg.norm(wall_xyz-np.asarray(field.C),axis=1)
    if np.any(wall_r<field.PORE_R-1e-12):
        raise RuntimeError('P10HR_STOP: wall node in pore')
    wall_k=np.array([direct.kappa(*p) for p in wall_xyz])
    wall_mu=(wall_xyz[:,2]-field.C[2])/wall_r
    region={'north_mu_ge_0p8':wall_mu>=.8,'south_mu_le_m0p8':wall_mu<=-.8,
            'nonpolar_abs_mu_lt_0p8':abs(wall_mu)<.8}
    # Edge lengths from true surface corner endpoints: an empirical diagnostic
    # of actual triangulation, not a curved edge metric or volume D-025 proof.
    edge_by_region={key:[] for key in region}
    tris_by_region={key:0 for key in region}
    for tri in wall_tri:
        v=np.asarray([xyz[i] for i in tri]);mid=v.mean(axis=0)
        μ=(mid[2]-field.C[2])/np.linalg.norm(mid-np.asarray(field.C))
        g='north_mu_ge_0p8' if μ>=.8 else 'south_mu_le_m0p8' if μ<=-.8 else 'nonpolar_abs_mu_lt_0p8'
        tris_by_region[g]+=1
        edge_by_region[g].extend([np.linalg.norm(v[i]-v[j])*1000 for i,j in ((0,1),(1,2),(2,0))])
    return {'label':label,'elapsed_s':round(elapsed,4),
            'callback_calls':call_count,'all_nodes':len(ids),
            'triangles_all':tri_count,'triangles_by_physical_tag':by_physical,
            'pore_wall_triangles':len(wall_tri),'pore_wall_nodes':len(wall_nodes),
            'wall_node_kappa':stats(wall_k),
            'wall_pole_groups':{key:{'node_count':int(np.count_nonzero(mask)),
                                     'kappa':stats(wall_k[mask]),
                                     'triangle_count_by_corner_centroid':tris_by_region[key],
                                     'straight_corner_edge_mm':stats(edge_by_region[key])}
                                for key,mask in region.items()},
            'wall_nodes_sphere_max_radial_error_mm':float(np.max(abs(wall_r-field.PORE_R))*1000)}


def main():
    geo=HERE/'P10GT_HXT10.geo'
    if hashlib.sha256(geo.read_bytes()).hexdigest()!=SHA:raise RuntimeError('P10HR_STOP: pinned original CAD source SHA')
    import gmsh
    if gmsh.__version__!='4.15.2':raise RuntimeError('P10HR_STOP: Gmsh version mismatch')
    src,v25,_,_,_,qa=field.load_centers(HERE/'P10HA_SPATIAL_KAPPA_1200_BINS.csv',HERE/'P10HA_KAPPA_QA.json')
    direct=DirectKappa(src,v25,qa['mechanical_only_25_36_shared_smoothing_denominator'])
    gmsh.initialize()
    count=0; overflow=False
    try:
        gmsh.option.setNumber('General.Terminal',1)
        gmsh.open(str(geo))
        if len(gmsh.model.getEntities(3))!=2:raise RuntimeError('P10HR_STOP: CAD topology')
        start=time.perf_counter()
        gmsh.model.mesh.generate(2)
        base=audit(gmsh,'original_Field7_baseline',direct,0,time.perf_counter()-start)
        # Explicit complete mesh clearing before a separately observed adaptive
        # run on unchanged CAD, without clearing the original Field[7].
        gmsh.model.mesh.clear()

        def callback(dim,tag,x,y,z,lc):
            nonlocal count,overflow
            count+=1
            if count>MAX_CALLBACK:
                overflow=True
                return lc
            k=direct.kappa(x,y,z)
            return lc*(1-field.ALPHA*k)**(1/3)

        gmsh.model.mesh.setSizeCallback(callback)
        start=time.perf_counter()
        gmsh.model.mesh.generate(2)
        sec=time.perf_counter()-start
        gmsh.model.mesh.removeSizeCallback()
        if overflow:raise RuntimeError('P10HR_STOP: 500k callback cap')
        adapted=audit(gmsh,'original_Field7_times_direct_mechanical_kappa',direct,count,sec)
        info={'protocol':'P10HR_R1_MATCHED_REAL_P10GT_CAD_2D_BASELINE_VS_KAPPA',
              'status':'MATCHED_2D_PAIR_CREATED_NEEDS_INDEPENDENT_VERDICT',
              'gmsh_version':gmsh.__version__,'original_geo_sha256':SHA,
              'nominal_volume_factor_at_kappa1':1-field.ALPHA,
              'baseline':base,'adapted':adapted,
              'pore_wall_triangle_ratio_adapt_over_base':adapted['pore_wall_triangles']/base['pore_wall_triangles'],
              'total_triangle_ratio_adapt_over_base':adapted['triangles_all']/base['triangles_all'],
              'warning':'Actual Q2 surface triangles are not 3D D-025 curved Tet10 volume proof.',
              'native_3D_M2_FEM_attempts':0,'D025_GO':False}
        REPORT.write_text(json.dumps(info,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
        print(info['status'],'pore triangles baseline/adapted',base['pore_wall_triangles'],adapted['pore_wall_triangles'])
    finally:
        gmsh.finalize()


if __name__=='__main__':
    try:main()
    except Exception:
        ERROR.write_text(traceback.format_exc(),encoding='utf-8')
        print('P10HR_WORKER_STOP',ERROR)
        sys.exit(2)
