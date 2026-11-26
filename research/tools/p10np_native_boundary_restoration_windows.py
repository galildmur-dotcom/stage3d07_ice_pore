#!/usr/bin/env python3
"""P10NP: restore exact boundary coordinates after in-memory HighOrderElastic."""
import hashlib,json,sys,traceback,time
from pathlib import Path
HERE=Path(__file__).resolve().parent
MESH=HERE/'P10NA_M13_R2_CANDIDATE_UNVERIFIED.msh'
SHA='57403ba43fa299417d519046cebdf50fa4968b670c071a8b7882748b50f51e9c'
OUT=HERE/'P10NP_BOUNDARY_RESTORATION_RESULT.json'
THRESH={'minSICN':.2,'minSJ':.4,'gamma':.15,'minDetJac':0.}

def snapshot(gmsh,np):
    ids,cn=gmsh.model.mesh.getElementsByType(11)
    ids=np.asarray(ids,dtype=np.int64)
    cn=np.asarray(cn,dtype=np.int64).reshape(-1,10)
    if len(ids)!=18004 or len(np.unique(ids))!=18004:raise RuntimeError('Tet10 population mismatch')
    tet={int(k):tuple(map(int,v)) for k,v in zip(ids,cn)}
    ntags,coords,_=gmsh.model.mesh.getNodes()
    nodes={int(k):tuple(map(float,v)) for k,v in zip(ntags,np.asarray(coords).reshape(-1,3))}
    if len(nodes)!=26099:raise RuntimeError('node population mismatch')
    surfaces={};boundary=set()
    for dim,phys in gmsh.model.getPhysicalGroups(2):
        for entity in gmsh.model.getEntitiesForPhysicalGroup(dim,phys):
            etypes,etags,ec=gmsh.model.mesh.getElements(dim,entity)
            for kind,taglist,connectivity in zip(etypes,etags,ec):
                if int(kind)==9:
                    for eid,conn in zip(taglist,np.asarray(connectivity,dtype=np.int64).reshape(-1,6)):
                        surfaces[int(eid)]=tuple(map(int,conn));boundary.update(map(int,conn))
    physical=sorted(int(t) for _,t in gmsh.model.getPhysicalGroups(2))
    if physical!=list(range(2,10)) or not boundary:raise RuntimeError('physical boundary missing')
    return {'ids':ids,'tet':tet,'nodes':nodes,'surface':surfaces,'boundary':boundary,'groups':physical}

def quality(gmsh,np,ids):
    result={}
    for name,limit in THRESH.items():
        vals=np.asarray(gmsh.model.mesh.getElementQualities(ids.tolist(),qualityName=name),dtype=float)
        if vals.shape!=ids.shape or not np.isfinite(vals).all():raise RuntimeError('bad metric '+name)
        idx=np.argsort(vals);bad=vals<=limit if name=='minDetJac' else vals<limit
        result[name]={'min':float(vals[idx[0]]),'worst_tag':int(ids[idx[0]]),
            'violating_tags':[int(n) for n in ids[bad]],'violating_count':int(bad.sum())}
    return result

def compare(original,later,np):
    v={'tet_id_sets_equal':original['tet'].keys()==later['tet'].keys(),
       'tet_connectivity_by_tag_equal':original['tet']==later['tet'],
       'surface_connectivity_by_tag_equal':original['surface']==later['surface'],
       'node_id_sets_equal':original['nodes'].keys()==later['nodes'].keys(),
       'surface_node_sets_equal':original['boundary']==later['boundary']}
    v['tet_connectivity_mismatch_count']=sum(original['tet'].get(k)!=later['tet'].get(k) for k in original['tet'])
    v['surface_connectivity_mismatch_count']=sum(original['surface'].get(k)!=later['surface'].get(k) for k in original['surface'])
    changed=[k for k in original['nodes'] if k in later['nodes'] and original['nodes'][k]!=later['nodes'][k]]
    bchanged=set(changed)&original['boundary']
    v['changed_node_count']=len(changed);v['changed_boundary_node_count']=len(bchanged)
    v['boundary_coordinates_exact']=not bchanged and v['surface_node_sets_equal']
    if changed:v['max_coordinate_displacement_mm']=float(max(np.linalg.norm(np.asarray(original['nodes'][k])-later['nodes'][k]) for k in changed)*1000)
    return v

def main():
    import gmsh,numpy as np
    if OUT.exists():raise RuntimeError('P10NP_STOP: output exists')
    if gmsh.__version__!='4.15.2':raise RuntimeError('Gmsh 4.15.2 required')
    if hashlib.sha256(MESH.read_bytes()).hexdigest()!=SHA:raise RuntimeError('source mesh SHA mismatch')
    report={'protocol':'P10NP_RESTORE_BOUNDARY_AFTER_HIGHORDER_ELASTIC','source_sha256':SHA,
        'status':'STARTED_NOT_M13_R3','optimized_mesh_written':False,'FEM_attempts':0,'marker_uses':0}
    gmsh.initialize()
    try:
        gmsh.option.setNumber('General.Terminal',1)
        gmsh.option.setNumber('Mesh.HighOrderFixBoundaryNodes',1)
        gmsh.option.setNumber('Mesh.HighOrderIterMax',50)
        gmsh.option.setNumber('Mesh.HighOrderPassMax',5)
        gmsh.option.setNumber('Mesh.HighOrderNumLayers',2)
        gmsh.open(str(MESH))
        before=snapshot(gmsh,np)
        report['before_quality']=quality(gmsh,np,before['ids'])
        print('P10NP_OPTIMIZE_START',flush=True)
        timer=time.monotonic()
        gmsh.model.mesh.optimize('HighOrderElastic',force=True)
        report['optimization_seconds']=time.monotonic()-timer
        after=snapshot(gmsh,np)
        report['after_optimizer']=compare(before,after,np)
        report['after_optimizer_quality']=quality(gmsh,np,after['ids'])
        # Restore every original surface node exactly, including all Tri6 midsides.
        changed_boundary=[k for k in before['boundary'] if k in after['nodes'] and before['nodes'][k]!=after['nodes'][k]]
        for k in sorted(changed_boundary):
            coord,param,dim,entity=gmsh.model.mesh.getNode(k)
            gmsh.model.mesh.setNode(k,list(before['nodes'][k]),param)
        restored=snapshot(gmsh,np)
        report['restored_boundary_node_count']=len(changed_boundary)
        report['after_restore']=compare(before,restored,np)
        report['after_restore_quality']=quality(gmsh,np,restored['ids'])
        safe=all(report['after_restore'][key] for key in ('tet_id_sets_equal','tet_connectivity_by_tag_equal',
            'surface_connectivity_by_tag_equal','node_id_sets_equal','surface_node_sets_equal','boundary_coordinates_exact'))
        report['structurally_safe']=safe
        report['D031_pass_after_boundary_restore']=all(q['violating_count']==0 for q in report['after_restore_quality'].values())
        report['status']='DIAGNOSTIC_PASS_ALL_GATES' if safe and report['D031_pass_after_boundary_restore'] else 'DIAGNOSTIC_HOLD'
    except Exception as e:
        report['status']='DIAGNOSTIC_ERROR';report['error']=repr(e);report['traceback']=traceback.format_exc()[-3000:]
    finally:gmsh.finalize()
    with OUT.open('x',encoding='utf-8') as f:json.dump(report,f,indent=2);f.write('\n')
    print('P10NP_DONE',report['status'],'result',OUT.name,flush=True)

if __name__=='__main__':
    try:main()
    except Exception as e:print('P10NP_STOP',repr(e),flush=True);sys.exit(2)
