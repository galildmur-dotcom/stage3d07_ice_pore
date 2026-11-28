#!/usr/bin/env python3
"""One P10IE isolated C1 polar-patch corrected original-CAD 3D candidate; no FEM."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import sys
import time
import traceback
import numpy as np
import gmsh
import P10IB_2D_worker as pinned
import p10hc_continuous_kappa_geo as field
import p10hy_surface_smoothness_audit as wall
from p10hk_direct_kappa_callback_benchmark import DirectKappa
from p10ie_fixed_patch_size_calibration import corrected_factor

HERE=Path(__file__).resolve().parent
OUT=HERE/'P10IE_M2_PATCH_CALIBRATED_3D_UNVERIFIED.msh'
RESULT=HERE/'P10IE_WORKER_RESULT.json'
ERROR=HERE/'P10IE_WORKER_ERROR.txt'
DELTA_N=0.1390288217133428
DELTA_S=0.11663130879448864
MAX_CALLS=1500000

def main():
    for n,s in [('P10GT_HXT10.geo',pinned.GEO_SHA),
                ('P10GT_HXT10.msh',pinned.M1_SHA),
                ('P10HA_SPATIAL_KAPPA_1200_BINS.csv',pinned.CSV_SHA),
                ('P10HA_KAPPA_QA.json',pinned.QA_SHA)]:pinned.check_sha(n,s)
    src,val,_,_,_,qa=field.load_centers(
        HERE/'P10HA_SPATIAL_KAPPA_1200_BINS.csv',
        HERE/'P10HA_KAPPA_QA.json')
    source,v=wall.source(HERE/'P10HA_SPATIAL_KAPPA_1200_BINS.csv')
    pinned.need(np.max(np.abs(source-src))<1e-14 and np.max(np.abs(v-val))<1e-14,
                'C2 source mismatch')
    dirs,ks,seedinfo=pinned.seed_directions(source,v)
    pinned.need(gmsh.__version__=='4.15.2','wrong gmsh version')
    gmsh.initialize()
    try:
        gmsh.option.setNumber('General.Terminal',1)
        gmsh.open(str(HERE/'P10GT_HXT10.geo'))
        pinned.need(len(gmsh.model.getEntities(3))==2,'unexpected original ice volumes')
        pinned.need(list(map(int,gmsh.model.getEntitiesForPhysicalGroup(2,8)))==[8],
                    'original CAD pore tag changed')
        pinned.need(gmsh.model.getType(2,8)=='Sphere','wrong pore CAD type')
        tags=[]
        for d in dirs:
            xyz=list(map(float,pinned.C+.001*d))
            pinned.need(bool(gmsh.model.isInside(2,8,xyz)),'off-sphere embedded point')
            tags.append(gmsh.model.occ.addPoint(*xyz,meshSize=0))
        gmsh.model.occ.synchronize()
        pinned.need(list(map(int,gmsh.model.getEntitiesForPhysicalGroup(2,8)))==[8],
                    'original CAD lost surface group')
        gmsh.model.mesh.embed(0,tags,2,8)
        direct=DirectKappa(src,val,qa['mechanical_only_25_36_shared_smoothing_denominator'])
        ncalls=0;ghost=0;overflow=False;fmin=1.
        def callback(dim,tag,x,y,z,lc):
            nonlocal ncalls,ghost,overflow,fmin
            ncalls+=1
            if ncalls>MAX_CALLS:
                overflow=True;return lc
            p=np.array([x,y,z]);v=p-pinned.C;r=np.linalg.norm(v)
            if r<.001-1e-12:
                ghost+=1
                if r<1e-15:return lc
                p=pinned.C+.001*v/r
            k=direct.kappa(*p)
            dmm=max(r-.001,0)*1000
            mu=(p[2]-.03)/np.linalg.norm(p-pinned.C)
            extra=corrected_factor(DELTA_N,DELTA_S,dmm,mu)
            fmin=min(fmin,extra)
            return lc*(1-pinned.ALPHA*k)**(1/3)*extra
        gmsh.model.mesh.setSizeCallback(callback)
        start=time.monotonic()
        gmsh.model.mesh.generate(3)
        wall_s=time.monotonic()-start
        gmsh.model.mesh.removeSizeCallback()
        pinned.need(not overflow,'callback overflow')
        typ,ids,_=gmsh.model.mesh.getElements(3)
        pinned.need(set(map(int,typ))=={11},'volume must be Tet10')
        tcount=sum(map(len,ids))
        for tag in tags:
            ids0,_,_=gmsh.model.mesh.getNodes(0,tag)
            pinned.need(len(ids0)==1,'lost embedded point')
        ty2,id2,_=gmsh.model.mesh.getElements(2,8)
        pinned.need(set(map(int,ty2))=={9},'pore must have Tri6')
        gmsh.write(str(OUT))
        RESULT.write_text(json.dumps({
            'protocol':'P10IE_ONE_C1_POLAR_PATCH_CORRECTED_M2_3D_MESH_ONLY',
            'status':'CANDIDATE_UNVERIFIED',
            'gmsh_version':gmsh.__version__,'original_CAD_SHA256':pinned.GEO_SHA,
            'M1_SHA256':pinned.M1_SHA,'P10ID_control_SHA256':
                '8acba5a9b3185429c200989015a7dfffb2b19452170db9d508da3e59ea0102f5',
            'alpha':pinned.ALPHA,'log_delta_north':DELTA_N,'log_delta_south':DELTA_S,
            'patch_angular_abs_mu_ramp':[.6,.8],
            'patch_radial_taper_mm':[.3,1.0],
            'actual_min_extra_size_factor':fmin,
            'embedded_point_count':len(tags),'pore_Tri6':sum(map(len,id2)),
            'tet10':tcount,'mesh_seconds':wall_s,'callback_count':ncalls,
            'ghost_callback_count':ghost,'mesh_SHA256':hashlib.sha256(OUT.read_bytes()).hexdigest(),
            'mesh_filename':OUT.name,'FEM_attempts':0,'accepted_M2':False,
        },indent=2)+'\n',encoding='utf8')
        print('P10IE_ONE_C1_PATCHED_3D_MESH_CREATED_NO_FEM',flush=True)
    finally:gmsh.finalize()

if __name__=='__main__':
    try:main()
    except Exception:
        ERROR.write_text(traceback.format_exc(),encoding='utf8')
        print('P10IE_WORKER_STOP',flush=True)
        sys.exit(2)
