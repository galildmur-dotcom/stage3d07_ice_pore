#!/usr/bin/env python3
"""P10NC: canonical read-only Gmsh D031 for pinned M13 R2, no meshing/FEM."""
import hashlib,json,sys
from pathlib import Path

HERE=Path(__file__).resolve().parent
MESH=HERE/'P10NA_M13_R2_CANDIDATE_UNVERIFIED.msh'
SHA='57403ba43fa299417d519046cebdf50fa4968b670c071a8b7882748b50f51e9c'
OUT=HERE/'P10NC_M13_R2_GMSH_QUALITY_RESULT.json'

def main():
    import numpy as np
    import gmsh
    if OUT.exists():raise RuntimeError('D031 result exists; cannot overwrite')
    if gmsh.__version__!='4.15.2':raise RuntimeError('Gmsh Python API 4.15.2 required')
    if hashlib.sha256(MESH.read_bytes()).hexdigest()!=SHA:raise RuntimeError('M13 R2 SHA mismatch')
    gmsh.initialize()
    try:
        gmsh.option.setNumber('General.Terminal',0)
        gmsh.open(str(MESH))
        tags,_=gmsh.model.mesh.getElementsByType(11)
        if len(tags)!=18004:raise RuntimeError('M13 R2 Tet10 count mismatch')
        qualities={}
        for kind in ('minSICN','minSJ','gamma','minDetJac'):
            vals=np.asarray(gmsh.model.mesh.getElementQualities(tags,qualityName=kind),dtype=float)
            if len(vals)!=len(tags) or not np.isfinite(vals).all():
                raise RuntimeError('invalid Gmsh quality values: '+kind)
            qualities[kind]={'min':float(vals.min()),'p01':float(np.percentile(vals,1)),
                 'median':float(np.median(vals)),'nonpositive':int(np.count_nonzero(vals<=0))}
        physical=sorted(int(tag) for dim,tag in gmsh.model.getPhysicalGroups(2))
        passed=(physical==list(range(2,10)) and qualities['minSICN']['min']>=.20
           and qualities['minSJ']['min']>=.40 and qualities['gamma']['min']>=.15
           and qualities['minDetJac']['min']>0)
        result={'protocol':'P10NC_M13_R2_INDEPENDENT_GMSH_READONLY_D031',
            'status':'D031_QUALITY_PASS' if passed else 'D031_QUALITY_HOLD',
            'gmsh_version':gmsh.__version__,'mesh_sha256':SHA,'Tet10':len(tags),
            'physical_surface_tags':physical,'qualities':qualities,
            'quality_thresholds':{'minSICN':.20,'minSJ':.40,'gamma':.15,'minDetJac':0.},
            'quality_gate_pass':passed,'mesh_generation_attempts':0,
            'FEM_attempts':0,'one_shot_marker_uses':0}
        OUT.write_text(json.dumps(result,indent=2)+'\n')
        print(json.dumps(result,indent=2),flush=True)
    finally:gmsh.finalize()

if __name__=='__main__':
    try:main()
    except Exception as error:
        print('P10NC_READONLY_STOP '+repr(error),flush=True)
        sys.exit(2)
