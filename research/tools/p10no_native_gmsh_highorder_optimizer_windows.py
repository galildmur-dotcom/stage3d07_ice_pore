#!/usr/bin/env python3
"""P10NO: native Gmsh optimizer diagnostic; never FEM or accept mesh automatically."""
import hashlib,json,sys,time,traceback
from pathlib import Path

HERE=Path(__file__).resolve().parent
SOURCE=HERE/'P10NA_M13_R2_CANDIDATE_UNVERIFIED.msh'
SHA='57403ba43fa299417d519046cebdf50fa4968b670c071a8b7882748b50f51e9c'
THRESHOLDS={'minSICN':.2,'minSJ':.4,'gamma':.15,'minDetJac':0.}

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def snapshot(gmsh,np):
    tags,conn=gmsh.model.mesh.getElementsByType(11)
    tags=np.asarray(tags,dtype=np.int64)
    conn=np.asarray(conn,dtype=np.int64).reshape(-1,10)
    if len(tags)!=18004 or len(set(tags.tolist()))!=18004:raise RuntimeError('Tet10 count/tags mismatch')
    ntags,coords,_=gmsh.model.mesh.getNodes()
    ntags=np.asarray(ntags,dtype=np.int64)
    coords=np.asarray(coords,dtype=float).reshape(-1,3)
    if len(ntags)!=26099:raise RuntimeError('node population mismatch')
    nodes={int(k):v for k,v in zip(ntags,coords)}
    if len(nodes)!=len(ntags):raise RuntimeError('duplicate node tags')
    groups=sorted(int(g) for d,g in gmsh.model.getPhysicalGroups(2))
    if groups!=list(range(2,10)):raise RuntimeError('physical surface group mismatch')
    # Collect every node of every physical 2D surface, including Tri6 midsides.
    boundary=set(); surface_elements={}
    for dim,phys in gmsh.model.getPhysicalGroups(2):
        for entity in gmsh.model.getEntitiesForPhysicalGroup(dim,phys):
            etypes,etags,conns=gmsh.model.mesh.getElements(dim,entity)
            for kind,ids,connectivity in zip(etypes,etags,conns):
                if int(kind)==9:
                    ar=np.asarray(connectivity,dtype=np.int64).reshape(-1,6)
                    for element,cn in zip(ids,ar):
                        boundary.update(map(int,cn))
                        surface_elements[int(element)]=tuple(map(int,cn))
    if not boundary:raise RuntimeError('surface node set not found')
    return {'tags':tags,'conn':conn,'nodes':nodes,'boundary':boundary,
        'surface_elements':surface_elements,'physical_surface_tags':groups}

def quality(gmsh,np,tags):
    q={}
    for name,threshold in THRESHOLDS.items():
        vals=np.asarray(gmsh.model.mesh.getElementQualities(tags.tolist(),qualityName=name),dtype=float)
        if vals.shape!=tags.shape or not np.isfinite(vals).all():raise RuntimeError('bad quality: '+name)
        order=np.argsort(vals)
        bad=vals<=threshold if name=='minDetJac' else vals<threshold
        q[name]={'min':float(vals[order[0]]),'worst_tag':int(tags[order[0]]),
                 'violating_count':int(np.count_nonzero(bad)),
                 'violating_tags':[int(tag) for tag in tags[bad]],
                 'p01':float(np.percentile(vals,1)),
                 'worst_five':[{'tag':int(tags[i]),'value':float(vals[i])} for i in order[:5]]}
    return q

def main(method):
    import numpy as np
    import gmsh
    if method not in ('HighOrder','HighOrderElastic'):raise RuntimeError('unsupported method')
    if gmsh.__version__!='4.15.2':raise RuntimeError('exact Gmsh Python API 4.15.2 required')
    if sha(SOURCE)!=SHA:raise RuntimeError('source SHA mismatch')
    output=HERE/f'P10NO_{method.upper()}_RESULT.json'
    if output.exists():raise RuntimeError('result exists; no overwrite')
    record={'protocol':'P10NO_NATIVE_GMSH_OPTIMIZATION_EXPERIMENT',
        'method':method,'status':'STARTED_DIAGNOSTIC_NOT_M13_R3',
        'source_sha256':SHA,'gmsh_version':'4.15.2',
        'gmsh_generation_attempts':0,'FEM_attempts':0,'marker_uses':0}
    gmsh.initialize()
    try:
        gmsh.option.setNumber('General.Terminal',1)
        gmsh.option.setNumber('Mesh.HighOrderFixBoundaryNodes',1)
        gmsh.option.setNumber('Mesh.HighOrderIterMax',50)
        gmsh.option.setNumber('Mesh.HighOrderPassMax',5)
        gmsh.option.setNumber('Mesh.HighOrderNumLayers',2)
        gmsh.open(str(SOURCE))
        before=snapshot(gmsh,np)
        record['before_quality']=quality(gmsh,np,before['tags'])
        print('P10NO_OPTIMIZE_START',method,flush=True)
        start=time.monotonic()
        try:
            # Force=True is required to test optimization of imported discrete entities.
            gmsh.model.mesh.optimize(method,force=True)
            record['optimize_returned']=True
        except Exception as ex:
            record['optimize_returned']=False
            record['optimizer_error']=repr(ex)
        record['optimizer_elapsed_seconds']=time.monotonic()-start
        after=snapshot(gmsh,np)
        record['connectivity_unchanged']=bool(np.array_equal(before['tags'],after['tags']) and np.array_equal(before['conn'],after['conn']))
        record['surface_connectivity_unchanged']=before['surface_elements']==after['surface_elements']
        record['node_ids_unchanged']=before['nodes'].keys()==after['nodes'].keys()
        record['boundary_node_ids_unchanged']=before['boundary']==after['boundary']
        record['boundary_coordinates_unchanged_exact']=bool(
            before['boundary']==after['boundary'] and
            all(np.array_equal(before['nodes'][k],after['nodes'][k]) for k in before['boundary']))
        changed=[k for k in before['nodes'] if k in after['nodes'] and not np.array_equal(before['nodes'][k],after['nodes'][k])]
        record['changed_node_count']=len(changed)
        record['changed_boundary_node_count']=len(set(changed)&before['boundary'])
        record['after_quality']=quality(gmsh,np,after['tags'])
        record['quality_gate_pass']=all(item['violating_count']==0 for item in record['after_quality'].values())
        safe=all(record[k] for k in ('connectivity_unchanged','surface_connectivity_unchanged',
            'node_ids_unchanged','boundary_node_ids_unchanged','boundary_coordinates_unchanged_exact'))
        record['structurally_safe']=safe
        # No optimized MSH is written: evidence-only test, even if quality passes.
        record['status']='DIAGNOSTIC_PASS_ALL_GATES' if safe and record['quality_gate_pass'] else 'DIAGNOSTIC_HOLD'
        record['optimized_mesh_written']=False
    except Exception as ex:
        record['status']='DIAGNOSTIC_ERROR'
        record['error']=repr(ex)
        record['traceback']=traceback.format_exc()[-3000:]
    finally:
        gmsh.finalize()
    with output.open('x',encoding='utf-8') as f:json.dump(record,f,indent=2);f.write('\n')
    print('P10NO_METHOD_DONE',method,record['status'],'result',output.name,flush=True)

if __name__=='__main__':
    try:main(sys.argv[1])
    except Exception as ex:print('P10NO_STOP',repr(ex),flush=True);sys.exit(2)
