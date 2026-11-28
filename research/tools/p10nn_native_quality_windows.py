#!/usr/bin/env python3
"""P10NN independent read-only Gmsh quality comparison (no mesh generation/FEM)."""
import hashlib,json,sys
from pathlib import Path

HERE=Path(__file__).resolve().parent
OUTPUT=HERE/'P10NN_M13_DIRECTIONAL_GMSH_QUALITY_RESULT.json'
LIMITS={'minSICN':.20,'minSJ':.40,'gamma':.15,'minDetJac':0.}

def main():
    import gmsh
    import numpy as np
    if OUTPUT.exists():raise RuntimeError('P10NN_STOP: output exists; no overwrite')
    if gmsh.__version__!='4.15.2':raise RuntimeError('P10NN_STOP: requires Gmsh 4.15.2')
    m=json.loads((HERE/'P10NN_MANIFEST.json').read_text())
    jobs=[('original',m['original_file'],m['original_sha256'])]
    jobs += [(f'trial_{i:02d}',s['file'],s['sha256']) for i,s in enumerate(m['selected'],1)]
    for _,name,expected in jobs:
        if hashlib.sha256((HERE/name).read_bytes()).hexdigest()!=expected:
            raise RuntimeError('P10NN_STOP: file SHA256 mismatch: '+name)
    results={}
    gmsh.initialize()
    try:
        gmsh.option.setNumber('General.Terminal',0)
        for label,name,digest in jobs:
            gmsh.clear();gmsh.open(str(HERE/name))
            tags,_=gmsh.model.mesh.getElementsByType(11)
            tags=np.asarray(tags,dtype=np.int64)
            if len(tags)!=18004 or len(np.unique(tags))!=18004:
                raise RuntimeError('P10NN_STOP: Tet10 population mismatch')
            groups=sorted(int(t) for d,t in gmsh.model.getPhysicalGroups(2))
            quality={}
            for metric,limit in LIMITS.items():
                v=np.asarray(gmsh.model.mesh.getElementQualities(tags.tolist(),qualityName=metric),dtype=float)
                if v.shape!=tags.shape or not np.all(np.isfinite(v)):
                    raise RuntimeError('P10NN_STOP: invalid metric: '+metric)
                fail=v<=limit if metric=='minDetJac' else v<limit
                order=np.argsort(v)
                quality[metric]={'min':float(v[order[0]]),'worst_tag':int(tags[order[0]]),
                    'p01':float(np.percentile(v,1)),'median':float(np.median(v)),
                    'below_threshold_count':int(fail.sum()),
                    'below_threshold_tags':[int(t) for t in tags[fail]],
                    'worst_five':[{'tag':int(tags[i]),'value':float(v[i])} for i in order[:5]]}
            passed=groups==list(range(2,10)) and all(q['below_threshold_count']==0 for q in quality.values())
            results[label]={'filename':name,'sha256':digest,'Tet10':len(tags),
                'physical_surface_tags':groups,'qualities':quality,'D031_pass':passed}
            print('P10NN_PROGRESS',label,'D031',passed,'minSICN',quality['minSICN']['min'],
                'minSJ',quality['minSJ']['min'],flush=True)
    finally:gmsh.finalize()
    passing=[k for k,v in results.items() if k!='original' and v['D031_pass']]
    result={'protocol':'P10NN_NATIVE_GMSH_4_15_2_CANONICAL_DIAGNOSTIC_READONLY',
        'status':'DIAGNOSTIC_ONLY_NO_R3_NO_FEM','thresholds':LIMITS,
        'gmsh_version':'4.15.2','results':results,'passing_diagnostic_ids':passing,
        'gmsh_generation_attempts':0,'FEM_attempts':0,'marker_uses':0}
    with OUTPUT.open('x',encoding='utf-8') as f:json.dump(result,f,indent=2);f.write('\n')
    print('P10NN_DONE',len(jobs)-1,'diagnostics, passing',len(passing),'RESULT',OUTPUT.name,flush=True)

if __name__=='__main__':
    try:main()
    except Exception as e:print('P10NN_STOP',repr(e),flush=True);sys.exit(2)
