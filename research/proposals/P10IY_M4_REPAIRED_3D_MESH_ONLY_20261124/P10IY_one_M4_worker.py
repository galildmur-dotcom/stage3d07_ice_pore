#!/usr/bin/env python3
"""One P10IY distinct M4 mesh-only hypothesis after P10IV D031 STOP (NO FEM)."""
from __future__ import annotations
import hashlib
import json
import math
from pathlib import Path
import time
import numpy as np

import p10hc_continuous_kappa_geo as old_field
from p10hk_direct_kappa_callback_benchmark import DirectKappa
from p10in_continuous_m3 import ContinuousKappa, C, R, smoothstep5
from p10iu_continuous_m4 import Field, rows
from p10ix_c2_m4_repair_preflight import local_patch

HERE=Path(__file__).resolve().parent
OUT=HERE/'P10IY_M4_R2_CANDIDATE_UNVERIFIED.msh'
OLD_N=.1390288217133428
OLD_S=.11663130879448864
NEW_N=.1032039542729587
NEW_S=.20008119936294466
NEW_GENERIC=.1435943053641514
M4_GENERIC=.1435943053641514
M4_N=.11445576719134759
M4_S=.12998093714900827
M4_N_REPAIR=.18
M4_BAD_PATCH=.10
WALL_DIRECTION=np.array([.0004027639149993809,.0007521467195290092,
                         .029551810068792664])-C
WALL_DIRECTION=WALL_DIRECTION/np.linalg.norm(WALL_DIRECTION)
MAX_CALLBACKS=1500000
# Identical pinned 10 CAD seeds used by the accepted P10IE M2.
SEED_DIRECTIONS=np.asarray([
 [0.26941639574807263,-0.3072105205978578,0.9127083333333333],
 [-0.44259957737323596,-0.029009508941602872,-0.89625],
 [-0.3664985668021997,-0.04825045168171063,0.9291666666666667],
 [-0.13134391727355096,-0.38692670321280165,0.9127083333333333],
 [-0.3415222951421483,0.14146316650066504,-0.9291666666666667],
 [-0.3518912793613243,-0.27001567548838806,0.89625],
 [-0.03210374145325526,-0.09457457261178873,0.995],
 [-0.20560787249210954,0.013476251945206928,0.9785416666666666],
 [-0.3573941704668299,0.3134262755102313,-0.8797916666666666],
 [-0.08304296248882778,-0.05548753356456836,-0.995]])


def old_patch(dmm,mu):
    # Exactly P10IE's C1 old M2 patch: preserve the M2 size proxy.
    q=lambda t:np.clip(t,0.,1.)**2*(3-2*np.clip(t,0.,1.))
    weight=q((abs(mu)-.6)/.2)*(1-q((dmm-.3)/.7))
    return math.exp(-(OLD_N if mu>=0 else OLD_S)*weight)


def main():
    import gmsh
    if not hasattr(gmsh,'initialize') or getattr(gmsh,'__version__',None)!='4.15.2':
        raise RuntimeError('Gmsh Python API 4.15.2 required; no mesh')
    src,values,_,_,_,qa=old_field.load_centers(
        HERE/'P10HA_SPATIAL_KAPPA_1200_BINS.csv',HERE/'P10HA_KAPPA_QA.json')
    old=DirectKappa(src,values,qa['mechanical_only_25_36_shared_smoothing_denominator'])
    new=ContinuousKappa(HERE/'P10HA_SPATIAL_KAPPA_1200_BINS.csv',
                        HERE/'P10IM_M3_KAPPA_HYPOTHESES_1200_BINS.csv')
    m4=Field(rows(HERE/'P10HA_SPATIAL_KAPPA_1200_BINS.csv'),
             rows(HERE/'P10IT_M2_M3_1200_BINS.csv'),'0.1')
    if abs(new.raw_center_max-.5976436567744664)>1e-12:
        raise RuntimeError('M3 calibrated new field drift')
    if abs(m4.raw_max-.5594154013460116)>1e-12:
        raise RuntimeError('M4 source-only continuous field drift')
    manifest=json.loads((HERE/'P10IX_C2_FIELD_PREFLIGHT.json').read_text())
    if (manifest['status']!='SOURCE_ONLY_CANDIDATE_NOT_NATIVE_GEOMETRY_GO'
            or abs(manifest['north_proposed_delta']-M4_N_REPAIR)>1e-12
            or abs(manifest['near_bad_wall_extra_log_size_max']-M4_BAD_PATCH)>1e-12):
        raise RuntimeError('P10IX source-only approved candidate drift')
    gmsh.initialize()
    try:
        gmsh.option.setNumber('General.Terminal',1)
        gmsh.option.setNumber('General.NumThreads',4)
        gmsh.open(str(HERE/'P10GT_HXT10.geo'))
        if len(gmsh.model.getEntities(3))!=2 or gmsh.model.getType(2,8)!='Sphere':
            raise RuntimeError('original rotated CAD mismatch')
        if list(map(int,gmsh.model.getEntitiesForPhysicalGroup(2,8)))!=[8]:
            raise RuntimeError('original pore physical tag mismatch')
        pts=[]
        for direction in SEED_DIRECTIONS:
            unit=direction/np.linalg.norm(direction)
            xyz=C+R*unit
            if not gmsh.model.isInside(2,8,list(map(float,xyz))):
                raise RuntimeError('pinned embedded seed off original pore CAD')
            pts.append(gmsh.model.occ.addPoint(*map(float,xyz),meshSize=0))
        gmsh.model.occ.synchronize()
        if list(map(int,gmsh.model.getEntitiesForPhysicalGroup(2,8)))!=[8]:
            raise RuntimeError('pore physical group lost after seed insertion')
        gmsh.model.mesh.embed(0,pts,2,8)
        calls=ghost=0
        maximum=1.0
        minimum=1.0
        def callback(dim,tag,x,y,z,lc):
            nonlocal calls,ghost,minimum,maximum
            calls+=1
            if calls>MAX_CALLBACKS:return lc
            position=np.asarray((x,y,z),dtype=float)
            v=position-C
            radius=np.linalg.norm(v)
            if radius<R-1e-12:
                ghost+=1
                if radius<1e-15:return lc
                position=C+R*v/radius
                v=position-C
                radius=R
            if radius<1e-15:return lc
            mu=float(v[2]/radius)
            dmm=max((radius-R)*1000.,0.)
            old_k=old.kappa(*position)
            old_factor=(1-.40*old_k)**(1/3)*old_patch(dmm,mu)
            new_k,new_factor,_=new.evaluate(position,NEW_N,NEW_S,NEW_GENERIC)
            _,polar_taper,m4_factor=m4.evaluate(position,M4_GENERIC,M4_N,M4_S)
            north_extra=(M4_N_REPAIR-M4_N)*polar_taper if mu>=0 else 0.
            bad_local=local_patch(position,WALL_DIRECTION)
            m4_factor*=math.exp(-north_extra-M4_BAD_PATCH*bad_local)
            ratio=old_factor*new_factor*m4_factor
            minimum=min(minimum,ratio)
            maximum=max(maximum,ratio)
            return lc*ratio
        gmsh.model.mesh.setSizeCallback(callback)
        started=time.monotonic()
        gmsh.model.mesh.generate(3)
        elapsed=time.monotonic()-started
        gmsh.model.mesh.removeSizeCallback()
        if calls>MAX_CALLBACKS:raise RuntimeError('callback budget exceeded')
        kinds,ids,_=gmsh.model.mesh.getElements(3)
        if set(map(int,kinds))!={11}:raise RuntimeError('Tet10 only required')
        tet_count=sum(map(len,ids))
        kinds2,ids2,_=gmsh.model.mesh.getElements(2,8)
        if set(map(int,kinds2))!={9}:raise RuntimeError('pore Tri6 only required')
        for p in pts:
            nodes,_,_=gmsh.model.mesh.getNodes(0,p)
            if len(nodes)!=1:raise RuntimeError('embedded seed lost')
        gmsh.write(str(OUT))
        result={'protocol':'P10IY_M4_SECOND_DISTINCT_GMSH_3D_MESH_ONLY',
                'status':'CANDIDATE_UNVERIFIED_NOT_ACCEPTED',
                'FEM_attempts':0,'old_M2_SHA256':
                  'd1ec65ffcc6e8fac7da925ecd66bbb9508450cf2ea837521442f57f45674c78b',
                'accepted_M3_sha256':'3d6ce765dced7d146ef5228be3b0a8210b4466ed08a0c9f5a20d1917dc2a8c3a',
                'source_P10IN_beta':.10,'P10IN_new_north_delta':NEW_N,
                'P10IN_new_south_delta':NEW_S,
                'P10IN_new_generic_delta':NEW_GENERIC,
                'source_P10IE_old_north_delta':OLD_N,'source_P10IE_old_south_delta':OLD_S,
                'source_P10IU_beta':.1,'M4_generic_delta':M4_GENERIC,
                'M4_north_delta':M4_N,'M4_south_delta':M4_S,
                'P10IX_north_repair_delta':M4_N_REPAIR,
                'P10IX_bad_wall_patch_log_size':M4_BAD_PATCH,
                'P10IX_bad_wall_direction':WALL_DIRECTION.tolist(),
                'prior_P10IV_M4_STOP_sha256':'00244c5f45c981fe2b05d7c60bcffe70a7e9eaac5b30eb2b9da66d137f84d50c',
                'original_CAD_sha256':hashlib.sha256((HERE/'P10GT_HXT10.geo').read_bytes()).hexdigest(),
                'gmsh_version':gmsh.__version__,'mesh_elapsed_s':elapsed,
                'Tet10':tet_count,'pore_Tri6':sum(map(len,ids2)),
                'embedded_CAD_points':len(pts),'size_callback_calls':calls,
                'inside_pore_projection_calls':ghost,
                'min_combined_relative_size_factor':minimum,
                'max_combined_relative_size_factor':maximum,
                'candidate_mesh_sha256':hashlib.sha256(OUT.read_bytes()).hexdigest()}
        (HERE/'P10IY_WORKER_RESULT.json').write_text(json.dumps(result,indent=2)+'\n')
        print('P10IY_M4_MESH_CREATED_UNVERIFIED_NO_FEM',tet_count,flush=True)
    finally:
        gmsh.finalize()


if __name__=='__main__':
    try:main()
    except Exception as e:
        (HERE/'P10IY_WORKER_ERROR.txt').write_text(type(e).__name__+': '+str(e)+'\n')
        print('P10IY_WORKER_STOP',repr(e),flush=True)
        raise
