#!/usr/bin/env python3
"""Pinned native Gmsh 4.15.2 quality comparison; no mesh generation or FEM."""
import hashlib,json,sys
from pathlib import Path

HERE=Path(__file__).resolve().parent
OUT=HERE/'P10NM_M13_CONSTRAINED_DIAGNOSTIC_GMSH_RESULT.json'
THRESH={'minSICN':.20,'minSJ':.40,'gamma':.15,'minDetJac':0.}

def main():
    import gmsh
    import numpy as np
    if OUT.exists():raise RuntimeError('P10NM_STOP: existing result will not be overwritten')
    if gmsh.__version__!='4.15.2':raise RuntimeError('P10NM_STOP: gmsh 4.15.2 required')
    m=json.loads((HERE/'P10NM_MANIFEST.json').read_text(encoding='utf-8'))
    jobs=[('original',m['original_file'],m['original_sha256'])]
    jobs += [(f"trial_{r['id']:02d}",r['file'],r['sha256']) for r in m['experiments'] if 'file' in r]
    for _,name,digest in jobs:
        if hashlib.sha256((HERE/name).read_bytes()).hexdigest()!=digest:
            raise RuntimeError('P10NM_STOP: file SHA256 mismatch: '+name)
    scans={}
    gmsh.initialize()
    try:
        gmsh.option.setNumber('General.Terminal',0)
        for label,name,digest in jobs:
            gmsh.clear()
            gmsh.open(str(HERE/name))
            tags,_=gmsh.model.mesh.getElementsByType(11)
            tags=np.asarray(tags,dtype=np.int64)
            if len(tags)!=m['Tet10'] or len(np.unique(tags))!=len(tags):
                raise RuntimeError('P10NM_STOP: invalid Tet10 population: '+label)
            groups=sorted(int(t) for d,t in gmsh.model.getPhysicalGroups(2))
            quality={}
            for kind,limit in THRESH.items():
                values=np.asarray(gmsh.model.mesh.getElementQualities(tags.tolist(),qualityName=kind),dtype=float)
                if values.shape!=tags.shape or not np.isfinite(values).all():
                    raise RuntimeError('P10NM_STOP: invalid quality '+kind)
                failed=values<=limit if kind=='minDetJac' else values<limit
                order=np.argsort(values)
                quality[kind]={'min':float(values[order[0]]),'worst_tag':int(tags[order[0]]),
                    'p01':float(np.percentile(values,1)),'median':float(np.median(values)),
                    'below_threshold_count':int(failed.sum()),
                    'below_threshold_tags':[int(t) for t in tags[failed]],
                    'worst_five':[{'tag':int(tags[i]),'quality':float(values[i])} for i in order[:5]]}
            passed=groups==list(range(2,10)) and all(q['below_threshold_count']==0 for q in quality.values())
            scans[label]={'filename':name,'sha256':digest,'Tet10':len(tags),
                'physical_surface_tags':groups,'qualities':quality,'D031_pass':passed}
            print('P10NM_NATIVE_PROGRESS',label,'D031_pass',passed,
                'minSICN',quality['minSICN']['min'],'minSJ',quality['minSJ']['min'],flush=True)
    finally:
        gmsh.finalize()
    candidate_ids=[label for label in scans if label!='original']
    passing=[label for label in candidate_ids if scans[label]['D031_pass']]
    result={'protocol':'P10NM_GMSH_4_15_2_CANONICAL_QUALITY_SWEEP_READONLY',
        'status':'DIAGNOSTIC_ONLY_NO_R3_NO_FEM', 'gmsh_version':'4.15.2',
        'thresholds':THRESH,'results':scans,'passing_diagnostic_ids':passing,
        'gmsh_generation_attempts':0,'FEM_attempts':0,'marker_uses':0}
    with OUT.open('x',encoding='utf-8') as f:json.dump(result,f,indent=2);f.write('\n')
    print('P10NM_NATIVE_DONE candidates',len(candidate_ids),'passing',len(passing),
        'RESULT',OUT.name,flush=True)

if __name__=='__main__':
    try:main()
    except Exception as e:
        print('P10NM_STOP',repr(e),flush=True)
        sys.exit(2)
