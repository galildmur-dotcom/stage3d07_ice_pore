#!/usr/bin/env python3
"""P10MX: independent Gmsh 4.15.2 read-only D031 of fixed M13 A mesh."""
import hashlib
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
MESH=HERE/'P10MV_M13_R1_CANDIDATE_UNVERIFIED.msh'
SHA='3c0b292007dce69cb70559a215ce7367b6c33fc1f7c46a6ca3396041481a1b1e'
RESULT=HERE/'P10MX_M13_R1_GMSH_QUALITY_RESULT.json'

def main():
    import numpy as np
    import gmsh
    if RESULT.exists(): raise RuntimeError('D031 evidence already exists: no overwrite')
    if gmsh.__version__!='4.15.2': raise RuntimeError('exact Gmsh Python API 4.15.2 required')
    if hashlib.sha256(MESH.read_bytes()).hexdigest()!=SHA: raise RuntimeError('M13 mesh SHA drift')
    gmsh.initialize()
    try:
        gmsh.option.setNumber('General.Terminal',0)
        gmsh.open(str(MESH))
        tags,_=gmsh.model.mesh.getElementsByType(11)
        if len(tags)!=18048:raise RuntimeError('M13 Tet10 count drift')
        quals={}
        for name in ('minSICN','minSJ','gamma','minDetJac'):
            vals=np.asarray(gmsh.model.mesh.getElementQualities(tags,qualityName=name),dtype=float)
            if len(vals)!=len(tags) or not np.isfinite(vals).all():
                raise RuntimeError('invalid quality: '+name)
            quals[name]={'min':float(vals.min()),'p01':float(np.percentile(vals,1)),
                         'median':float(np.median(vals)),
                         'nonpositive':int(np.count_nonzero(vals<=0))}
        faces=sorted(int(t) for d,t in gmsh.model.getPhysicalGroups(2))
        passed=(quals['minSICN']['min']>=.20 and quals['minSJ']['min']>=.40
                and quals['gamma']['min']>=.15 and quals['minDetJac']['min']>0
                and faces==list(range(2,10)))
        result={'protocol':'P10MX_M13_A_R1_INDEPENDENT_READONLY_GMSH_D031',
                'status':'D031_QUALITY_PASS' if passed else 'D031_QUALITY_HOLD',
                'gmsh_version':gmsh.__version__,'mesh_sha256':SHA,'Tet10':int(len(tags)),
                'physical_surface_tags':faces,'qualities':quals,
                'quality_thresholds':{'minSICN':.20,'minSJ':.40,'gamma':.15,'minDetJac':0.},
                'quality_gate_pass':passed,'mesh_generation_attempts':0,
                'FEM_attempts':0,'one_shot_marker_uses':0}
        RESULT.write_text(json.dumps(result,indent=2)+'\n')
        print(json.dumps(result,indent=2),flush=True)
    finally:
        gmsh.finalize()

if __name__=='__main__':
    try:main()
    except Exception as error:
        print('P10MX_READONLY_STOP '+repr(error),flush=True)
        sys.exit(2)
