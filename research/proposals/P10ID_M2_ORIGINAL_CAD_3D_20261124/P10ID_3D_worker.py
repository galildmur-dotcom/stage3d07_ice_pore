#!/usr/bin/env python3
"""P10ID: one controlled original CAD 3D Tet10 M2 *candidate*, no FEM."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import time
import traceback
import sys

import numpy as np
import gmsh
import P10IB_2D_worker as base
import p10hy_surface_smoothness_audit as wall
import p10hc_continuous_kappa_geo as field
from p10hk_direct_kappa_callback_benchmark import DirectKappa

HERE = Path(__file__).resolve().parent
OUTPUT = HERE / 'P10ID_M2_3D_UNVERIFIED.msh'
REPORT = HERE / 'P10ID_WORKER_RESULT.json'
ERROR = HERE / 'P10ID_WORKER_ERROR.txt'
MAX_CALLS = 1500000


def main():
    for name, sha in (("P10GT_HXT10.geo",base.GEO_SHA),
                      ("P10GT_HXT10.msh",base.M1_SHA),
                      ("P10HA_SPATIAL_KAPPA_1200_BINS.csv",base.CSV_SHA),
                      ("P10HA_KAPPA_QA.json",base.QA_SHA)):
        base.check_sha(name,sha)
    source, values, _, _, _, qa = field.load_centers(
        HERE/'P10HA_SPATIAL_KAPPA_1200_BINS.csv',
        HERE/'P10HA_KAPPA_QA.json')
    src, v = wall.source(HERE/'P10HA_SPATIAL_KAPPA_1200_BINS.csv')
    base.need(np.max(np.abs(src-source))<1e-14 and np.max(np.abs(v-values))<1e-14,
              'incompatible source C2 field')
    dirs, ks, seed_info = base.seed_directions(src,v)
    base.need(gmsh.__version__=='4.15.2','require Gmsh4.15.2')
    gmsh.initialize()
    try:
        gmsh.option.setNumber('General.Terminal',1)
        gmsh.open(str(HERE/'P10GT_HXT10.geo'))
        base.need(len(gmsh.model.getEntities(3))==2,'original 2 ice CAD volumes changed')
        base.need(list(map(int,gmsh.model.getEntitiesForPhysicalGroup(2,8)))==[8],
                  'pore physical CAD entity changed')
        base.need(gmsh.model.getType(2,8)=='Sphere','pore must be original OCC sphere')
        base.need(abs(gmsh.option.getNumber('Mesh.MeshSizeFactor')-.9378887276834518)<1e-12,
                  'original sizing factor changed')
        tags=[]
        for direction in dirs:
            xyz=list(map(float,base.C+.001*direction))
            base.need(bool(gmsh.model.isInside(2,8,xyz)),'off-CAD candidate point')
            tags.append(gmsh.model.occ.addPoint(*xyz,meshSize=0))
        gmsh.model.occ.synchronize()
        base.need(list(map(int,gmsh.model.getEntitiesForPhysicalGroup(2,8)))==[8],
                  'pore physical CAD entity lost on synchronization')
        gmsh.model.mesh.embed(0,tags,2,8)
        direct=DirectKappa(source,values,qa['mechanical_only_25_36_shared_smoothing_denominator'])
        calls=0;ghost=0;overflow=False
        def sizing(dim,tag,x,y,z,lc):
            nonlocal calls,ghost,overflow
            calls+=1
            if calls>MAX_CALLS:
                overflow=True
                return lc
            p=np.array([x,y,z]);delta=p-base.C;r=np.linalg.norm(delta)
            if r<.001-1e-12:
                ghost+=1
                if r<1e-15:return lc
                p=base.C+(.001/r)*delta
            return lc*(1-base.ALPHA*direct.kappa(*p))**(1/3)
        gmsh.model.mesh.setSizeCallback(sizing)
        start=time.monotonic()
        gmsh.model.mesh.generate(3)
        wall_s=time.monotonic()-start
        gmsh.model.mesh.removeSizeCallback()
        base.need(not overflow,'size callback count overflow')
        types,ids,_=gmsh.model.mesh.getElements(3)
        base.need(set(map(int,types))=={11},'all volume elements must be Tet10')
        tet10=sum(map(len,ids))
        base.need(tet10>0,'no Tet10')
        for tag in tags:
            nodes,_,_=gmsh.model.mesh.getNodes(0,tag)
            base.need(len(nodes)==1,'embedded geometric point lost')
        ptypes,pids,_=gmsh.model.mesh.getElements(2,8)
        base.need(set(map(int,ptypes))=={9},'pore should be Tri6')
        gmsh.write(str(OUTPUT))
        REPORT.write_text(json.dumps({
            'protocol':'P10ID_R1_ONE_ORIGINAL_CAD_3D_TET10_NO_FEM',
            'status':'M2_3D_CANDIDATE_UNVERIFIED',
            'alpha':base.ALPHA,'gmsh_version':gmsh.__version__,
            'original_CAD_SHA256':base.GEO_SHA,'M1_SHA256':base.M1_SHA,
            'pore_surface_CAD_tag':8,'embedded_point_count':len(tags),
            'embedded_tags':tags,'kappa_at_seeds':list(map(float,ks)),
            'source_seed_gap':seed_info,'pore_Tri6':sum(map(len,pids)),
            'tet10':tet10,'mesh_seconds':wall_s,'callback_count':calls,
            'ghost_callback_count':ghost,
            'mesh_filename':OUTPUT.name,
            'mesh_SHA256':hashlib.sha256(OUTPUT.read_bytes()).hexdigest(),
            'FEM_attempts':0,'accepted_M2':False},ensure_ascii=False,indent=2)+'\n',encoding='utf8')
        print('P10ID_3D_MESH_ONLY_CANDIDATE_CREATED_NO_FEM',flush=True)
    finally:
        gmsh.finalize()


if __name__=='__main__':
    try:main()
    except Exception:
        ERROR.write_text(traceback.format_exc(),encoding='utf8')
        print('P10ID_STOP: worker exception, send report/log/error',flush=True)
        sys.exit(2)
