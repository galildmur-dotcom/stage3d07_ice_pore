#!/usr/bin/env python3
"""P10HP one bounded original CAD 1D source/geometry test; never 2D/3D/FEM.

Run ONLY via P10HP_guard.py, which enforces an external wall-clock timeout.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
import sys
import time
import traceback

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from p10hk_direct_kappa_callback_benchmark import DirectKappa
import p10hc_continuous_kappa_geo as field

GEO_SHA='f1227074616375c28706e1e55cddde370b9a9fca069aab88513b4313c8239f51'
REPORT=HERE/'P10HP_RESULT.json'
ERROR=HERE/'P10HP_WORKER_ERROR.txt'
MAX_CALLBACK=300000


def main():
    geo=HERE/'P10GT_HXT10.geo'
    if hashlib.sha256(geo.read_bytes()).hexdigest()!=GEO_SHA:
        raise RuntimeError('P10HP_STOP: P10GT original Field7 source mismatch')
    import gmsh
    if gmsh.__version__!='4.15.2':raise RuntimeError('P10HP_STOP: expected Gmsh 4.15.2')
    src,v25,_,_,_,qa=field.load_centers(HERE/'P10HA_SPATIAL_KAPPA_1200_BINS.csv',HERE/'P10HA_KAPPA_QA.json')
    direct=DirectKappa(src,v25,qa['mechanical_only_25_36_shared_smoothing_denominator'])
    gmsh.initialize()
    n=0; overflow=False; count_by_dim={}; kmin=1.;kmax=0.;lcmin=float('inf');lcmax=0.
    first=[]
    try:
        gmsh.option.setNumber('General.Terminal',1)
        gmsh.open(str(geo))
        entities={str(i):len(gmsh.model.getEntities(i)) for i in range(4)}
        # Pinned CAD is partitioned into an outer ice volume and B6 shell.
        if int(entities['3'])!=2:raise RuntimeError('P10HP_STOP: expected two CAD volumes (outer + B6 shell)')
        # The exact original P10GT field, CAD and options are loaded. Global
        # MeshSizeFactor is not removed or silently changed.
        if abs(gmsh.option.getNumber('Mesh.MeshSizeFactor')-.9378887276834518)>1e-12:
            raise RuntimeError('P10HP_STOP: original factor differs')

        def cb(dim,tag,x,y,z,lc):
            nonlocal n,overflow,kmin,kmax,lcmin,lcmax
            n+=1
            if n>MAX_CALLBACK:
                overflow=True
                return lc
            # Gmsh may probe outside the real ice volume; keep the original
            # physical-domain hard guard, so such events are reported as STOP.
            κ=direct.kappa(x,y,z)
            h=direct.size(dim,tag,x,y,z,lc)
            count_by_dim[str(dim)]=count_by_dim.get(str(dim),0)+1
            kmin=min(kmin,κ);kmax=max(kmax,κ)
            lcmin=min(lcmin,lc);lcmax=max(lcmax,lc)
            if len(first)<80:first.append([dim,tag,x,y,z,lc,κ,h])
            return h

        gmsh.model.mesh.setSizeCallback(cb)
        start=time.monotonic()
        gmsh.model.mesh.generate(1)  # ONLY actual original CAD curves, 1D
        elapsed=time.monotonic()-start
        gmsh.model.mesh.removeSizeCallback()
        if overflow:raise RuntimeError('P10HP_STOP: native callback upper bound exceeded')
        tags,_,_=gmsh.model.mesh.getNodes()
        _,elems,_=gmsh.model.mesh.getElements(1)
        report={'protocol':'P10HP_R1_ONE_BOUNDED_REAL_P10GT_CAD_1D_DIRECT_C2_KAPPA',
                'status':'REAL_CAD_1D_CALLBACK_FINISHED_REQUIRES_INDEPENDENT_AUDIT',
                'gmsh_version':gmsh.__version__,'original_geo_sha256':GEO_SHA,
                'CAD_entities_by_dimension':entities,
                'native_1d_wall_s':round(elapsed,3),
                'native_1d_nodes':int(len(tags)),
                'native_1d_element_count':sum(len(t) for t in elems),
                'callback_count':n,'callback_counts_by_dimension':count_by_dim,
                'kappa_min_max':[kmin,kmax],
                'lc_min_max':[lcmin,lcmax],
                'first_80_dim_tag_xyz_lc_kappa_h':first,
                'native_2D_3D_FEM_attempts':0,'M2_mesh_attempts':0,
                'D025_GO':False}
        REPORT.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
        print(report['status'],'callback_count',n,'nodes',len(tags),'evidence',REPORT)
    finally:
        gmsh.finalize()


if __name__=='__main__':
    try:main()
    except Exception:
        ERROR.write_text(traceback.format_exc(),encoding='utf-8')
        print('P10HP_WORKER_STOP',ERROR)
        sys.exit(2)
