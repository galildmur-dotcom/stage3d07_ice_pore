#!/usr/bin/env python3
"""P10KT: inspect existing M8 R3 Tet10 Gmsh qualities without meshing or FEM."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
M8=HERE/'P10KR_M8_R3_CANDIDATE_UNVERIFIED.msh'
EXPECTED='40949482ac74d80ae7ac44c88af527a705650d34c1ffcd0de7cd01dc2bd2fa8d'
OUT=HERE/'P10KT_M8_R3_GMSH_QUALITY_RESULT.json'

def main():
    import gmsh
    import numpy as np
    if gmsh.__version__!='4.15.2':raise RuntimeError('Gmsh Python 4.15.2 required')
    if hashlib.sha256(M8.read_bytes()).hexdigest()!=EXPECTED:
        raise RuntimeError('M8 R3 mesh SHA mismatch')
    if OUT.exists():raise RuntimeError('result already exists; move or review it before new audit')
    gmsh.initialize()
    try:
        gmsh.option.setNumber('General.Terminal',0)
        gmsh.open(str(M8))
        tags,_=gmsh.model.mesh.getElementsByType(11)
        if len(tags)!=12546:raise RuntimeError('Tet10 count mismatch')
        qualities={}
        for kind in ('minSICN','minSJ','gamma','minDetJac'):
            values=np.asarray(gmsh.model.mesh.getElementQualities(tags,qualityName=kind),dtype=float)
            if len(values)!=len(tags) or not np.isfinite(values).all():
                raise RuntimeError('invalid quality values: '+kind)
            qualities[kind]={'min':float(values.min()),'p01':float(np.percentile(values,1)),
                             'median':float(np.median(values)),
                             'nonpositive':int(np.count_nonzero(values<=0))}
        physical=sorted(int(p[1]) for p in gmsh.model.getPhysicalGroups(2))
        result={'protocol':'P10KT_M8_R3_INDEPENDENT_GMSH_READONLY_D031',
                'status':'READONLY_QUALITY_MEASURED_NO_MESH_NO_FEM',
                'gmsh_version':gmsh.__version__,'mesh_sha256':EXPECTED,
                'Tet10':len(tags),'physical_surface_tags':physical,
                'qualities':qualities,
                'quality_thresholds':{'minSICN':.20,'minSJ':.40,'gamma':.15,'minDetJac':0.},
                'quality_gate_pass':qualities['minSICN']['min']>=.20 and
                                    qualities['minSJ']['min']>=.40 and
                                    qualities['gamma']['min']>=.15 and
                                    qualities['minDetJac']['min']>0 and
                                    physical==list(range(2,10)),
                'mesh_generation_attempts':0,'FEM_attempts':0}
        OUT.write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
        print(json.dumps(result,indent=2),flush=True)
    finally:
        gmsh.finalize()

if __name__=='__main__':
    try:main()
    except Exception as exc:
        print('P10KT_READONLY_STOP '+repr(exc),flush=True)
        sys.exit(2)
