#!/usr/bin/env python3
"""P10NQ: native Gmsh optimizer geometric point-cloud correspondence audit."""
import hashlib,json,sys,time,traceback
from pathlib import Path
import numpy as np

HERE=Path(__file__).resolve().parent
MESH=HERE/'P10NA_M13_R2_CANDIDATE_UNVERIFIED.msh'
SHA='57403ba43fa299417d519046cebdf50fa4968b670c071a8b7882748b50f51e9c'
OUTPUT=HERE/'P10NQ_GEOMETRY_CORRESPONDENCE_RESULT.json'
C=np.array([0.,0.,.03]);R=.001

def sample(gmsh):
    ids,conn=gmsh.model.mesh.getElementsByType(11)
    ids=np.asarray(ids,dtype=np.int64)
    if len(ids)!=18004 or len(np.unique(ids))!=18004:raise RuntimeError('Tet10 count/tags mismatch')
    tet={int(e):tuple(map(int,row)) for e,row in zip(ids,np.asarray(conn,dtype=np.int64).reshape(-1,10))}
    nids,coords,_=gmsh.model.mesh.getNodes()
    nodes={int(k):np.asarray(x,dtype=float) for k,x in zip(nids,np.asarray(coords).reshape(-1,3))}
    if len(nodes)!=26099:raise RuntimeError('node count mismatch')
    faces={};by_phys={}
    for dim,phys in gmsh.model.getPhysicalGroups(2):
        members=set();elements={}
        for entity in gmsh.model.getEntitiesForPhysicalGroup(dim,phys):
            types,etags,conns=gmsh.model.mesh.getElements(dim,int(entity))
            for kind,tags,flat in zip(types,etags,conns):
                if int(kind)==9:
                    for eid,cn in zip(tags,np.asarray(flat,dtype=np.int64).reshape(-1,6)):
                        cn=tuple(map(int,cn));elements[int(eid)]=cn;members.update(cn);faces[int(eid)]=cn
        by_phys[int(phys)]={'node_ids':members,'elements':elements}
    if sorted(by_phys)!=list(range(2,10)):raise RuntimeError('physical surfaces missing')
    return {'nodes':nodes,'tets':tet,'faces':faces,'by_phys':by_phys}

def distances(a,b):
    """Bidirectional nearest-neighbor distances without SciPy dependency."""
    a=np.asarray(a,dtype=float);b=np.asarray(b,dtype=float)
    amin=np.full(len(a),np.inf);bmin=np.full(len(b),np.inf)
    for start in range(0,len(a),128):
        z=a[start:start+128]
        # Direct differences avoid catastrophic cancellation at submicron scales.
        squared=np.sum((z[:,None,:]-b[None,:,:])**2,axis=2)
        amin[start:start+len(z)]=np.sqrt(np.min(squared,axis=1))
        bmin=np.minimum(bmin,np.sqrt(np.min(squared,axis=0)))
    return amin,bmin

def cloud(before,after,keys_b,keys_a):
    points_b=np.array([before['nodes'][n] for n in sorted(keys_b)])
    points_a=np.array([after['nodes'][n] for n in sorted(keys_a)])
    ab,ba=distances(points_b,points_a)
    radii_b=np.linalg.norm(points_b-C,axis=1)
    radii_a=np.linalg.norm(points_a-C,axis=1)
    return {'before_nodes':len(points_b),'after_nodes':len(points_a),
        'directed_Hausdorff_mm_before_to_after':float(ab.max()*1000),
        'directed_Hausdorff_mm_after_to_before':float(ba.max()*1000),
        'nearest_95pct_mm_before_to_after':float(np.percentile(ab,95)*1000),
        'nearest_95pct_mm_after_to_before':float(np.percentile(ba,95)*1000),
        'exact_coordinate_nearest_count_before_to_after':int((ab<1e-12).sum()),
        'exact_coordinate_nearest_count_after_to_before':int((ba<1e-12).sum()),
        'max_radius_deviation_original_sphere_mm_before':float(np.max(np.abs(radii_b-R))*1000),
        'max_radius_deviation_original_sphere_mm_after':float(np.max(np.abs(radii_a-R))*1000)}

def main():
    import gmsh
    if OUTPUT.exists():raise RuntimeError('P10NQ_STOP: output already exists')
    if gmsh.__version__!='4.15.2':raise RuntimeError('Gmsh 4.15.2 required')
    if hashlib.sha256(MESH.read_bytes()).hexdigest()!=SHA:raise RuntimeError('M13 R2 source SHA mismatch')
    report={'protocol':'P10NQ_GMSH_HIGHORDERELASTIC_GEOMETRY_CORRESPONDENCE',
        'status':'STARTED_NO_MESH_OUTPUT','source_sha256':SHA,
        'FEM_attempts':0,'gmsh_generation_attempts':0,'marker_uses':0}
    gmsh.initialize()
    try:
        gmsh.option.setNumber('General.Terminal',1)
        gmsh.option.setNumber('Mesh.HighOrderFixBoundaryNodes',1)
        gmsh.option.setNumber('Mesh.HighOrderIterMax',50)
        gmsh.option.setNumber('Mesh.HighOrderPassMax',5)
        gmsh.option.setNumber('Mesh.HighOrderNumLayers',2)
        gmsh.open(str(MESH));before=sample(gmsh)
        start=time.monotonic()
        print('P10NQ_HIGHORDER_ELASTIC_START',flush=True)
        gmsh.model.mesh.optimize('HighOrderElastic',force=True)
        report['optimizer_s']=time.monotonic()-start
        after=sample(gmsh)
        report['same_node_tags']=before['nodes'].keys()==after['nodes'].keys()
        report['same_tet_tags']=before['tets'].keys()==after['tets'].keys()
        report['same_surface_tags']=before['faces'].keys()==after['faces'].keys()
        report['tet_connectivity_mismatch_count']=sum(before['tets'].get(k)!=after['tets'].get(k) for k in before['tets'])
        report['tet_corner_sets_mismatch_count']=sum(set(before['tets'][k][:4])!=set(after['tets'][k][:4]) for k in before['tets'])
        report['tet_node_sets_mismatch_count']=sum(set(before['tets'][k])!=set(after['tets'][k]) for k in before['tets'])
        report['surface_connectivity_mismatch_count']=sum(before['faces'].get(k)!=after['faces'].get(k) for k in before['faces'])
        report['surface_corner_sets_mismatch_count']=sum(set(before['faces'][k][:3])!=set(after['faces'][k][:3]) for k in before['faces'])
        report['surface_node_sets_mismatch_count']=sum(set(before['faces'][k])!=set(after['faces'][k]) for k in before['faces'])
        bound_b={n for v in before['by_phys'].values() for n in v['node_ids']}
        bound_a={n for v in after['by_phys'].values() for n in v['node_ids']}
        report['boundary_point_cloud']=cloud(before,after,bound_b,bound_a)
        report['physical_surface_point_clouds']={str(p):cloud(before,after,before['by_phys'][p]['node_ids'],after['by_phys'][p]['node_ids']) for p in sorted(before['by_phys'])}
        # Genuine sphere check uses physical tag 8 only, not the outer block boundaries.
        pore=report['physical_surface_point_clouds']['8']
        report['pore_geometry_cloud_unchanged_at_1e_9_m']=bool(max(pore['directed_Hausdorff_mm_before_to_after'],pore['directed_Hausdorff_mm_after_to_before'])<=1e-6)
        report['diagnostic_disposition']='GEOMETRY_COMPARE_ONLY_NO_ACCEPTANCE'
        report['status']='AUDIT_COMPLETED_NO_R3_NO_FEM'
    except Exception as e:
        report['status']='AUDIT_ERROR';report['error']=repr(e);report['traceback']=traceback.format_exc()[-3000:]
    finally:gmsh.finalize()
    with OUTPUT.open('x',encoding='utf-8') as f:json.dump(report,f,indent=2);f.write('\n')
    print('P10NQ_DONE',report['status'],'result',OUTPUT.name,flush=True)

if __name__=='__main__':
    try:main()
    except Exception as e:print('P10NQ_STOP',repr(e),flush=True);sys.exit(2)
