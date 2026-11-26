#!/usr/bin/env python3
"""P10NG: 729QP local Tet10 geometry around failed pore-boundary tets; READ ONLY."""
import hashlib,json,sys
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'research/tools'))
from p10nf_m13_pore_tri6_face_audit_readonly import read,SOURCES
from p10hv_independent_scan import rule,EDGE

OUT=ROOT/'p10ng_m13_jacobian/P10NG_M13_R1_R2_CURVED_TET10_LOCAL_729QP.json'
N,D,W=rule(9)

def evaluate(nodes,conn):
    p=np.asarray([nodes[i] for i in conn],dtype=float)
    mat=np.einsum('ic,qij->qcj',p,D,optimize=True)
    sv=np.linalg.svd(mat,compute_uv=False)
    det=np.linalg.det(mat)
    if np.any(det<=0):raise ValueError('nonpositive sampled curved detJ')
    a,b,c,d=p[:4]
    vec=np.stack([b-a,c-a,d-a],axis=1)
    det4=float(np.linalg.det(vec))
    normal=np.cross(b-a,c-a)
    h=float(abs(np.dot(normal,d-a))/np.linalg.norm(normal))
    face_edges=[np.linalg.norm(p[i]-p[j]) for i,j in ((0,1),(1,2),(2,0))]
    devi=[float(np.linalg.norm(p[i+4]-(p[a]+p[b])/2)) for i,(a,b) in enumerate(EDGE)]
    return {'corner_abs_detJ_m3':abs(det4),'corner_face_height_mm':h*1000,
       'height_over_mean_face_edge':h/np.mean(face_edges),
       'min_detJ_729':float(det.min()),'max_detJ_729':float(det.max()),
       'detJ_min_over_corner_abs':float(det.min()/abs(det4)),
       'detJ_max_over_corner_abs':float(det.max()/abs(det4)),
       'detJ_max_over_min':float(det.max()/det.min()),
       'min_sigma3_over_sigma1_729':float(np.min(sv[:,-1]/sv[:,0])),
       'p01_sigma3_over_sigma1_729':float(np.percentile(sv[:,-1]/sv[:,0],1)),
       'median_sigma3_over_sigma1_729':float(np.median(sv[:,-1]/sv[:,0])),
       'max_midside_deviation_mm':max(devi)*1000,
       'midside_deviation_mm':[x*1000 for x in devi],
       'relative_curved_volume_to_straight':float(np.sum(det*W)*6/abs(det4))}

def main():
    if OUT.exists():raise RuntimeError('P10NG output already exists; no overwrite')
    result={'protocol':'P10NG_READONLY_LOCAL_CURVED_TET10_729QP',
       'status':'PASS_READONLY_NO_GMSH_NO_MESH_NO_FEM_NO_MARKER',
       'quadrature_points_per_tet':729,'meshes':{},'mesh_generation_attempts':0,'FEM_attempts':0}
    for name,path,locator,sha in SOURCES:
        assert hashlib.sha256(path.read_bytes()).hexdigest()==sha
        q=json.loads(locator.read_text(encoding='utf-8-sig'))
        assert q['mesh_sha256']==sha
        nodes,tets,faces=read(path)
        fvertices=set(k for key in faces for k in key)
        boundary={tag:cn for tag,cn in tets.items() if sum(n in fvertices for n in cn[:4])>=3}
        cent={tag:np.mean([nodes[k] for k in cn[:4]],axis=0) for tag,cn in boundary.items()}
        bad=[]
        for row in (r for r in q['elements'] if r['below_threshold']):
            tag=row['element_tag'];p=np.asarray(row['centroid_m'])
            assert tag in boundary and np.linalg.norm(cent[tag]-p)<1e-10
            candidates=sorted((float(np.linalg.norm(x-p)),t) for t,x in cent.items() if t!=tag)
            neighbors=candidates[:24]
            cohort=[evaluate(nodes,boundary[t]) for _,t in neighbors]
            actual=evaluate(nodes,boundary[tag])
            rank={}
            for feature in ('min_sigma3_over_sigma1_729','detJ_min_over_corner_abs',
                            'height_over_mean_face_edge','relative_curved_volume_to_straight'):
                vals=np.array([x[feature] for x in cohort])
                rank[feature]={'nearby_24_median':float(np.median(vals)),
                               'nearby_24_min':float(vals.min()),
                               'nearby_24_max':float(vals.max()),
                               'fraction_nearby_24_at_or_below_bad_value':float(np.mean(vals<=actual[feature]))}
            bad.append({'tag':tag,'centroid_m':row['centroid_m'],
                        'wall_distance_mm':row['wall_distance_mm'],'mu':row['mu_cos_theta'],
                        'canonical_minSICN':row['quality']['minSICN'],
                        'canonical_minSJ':row['quality']['minSJ'],
                        'geometry_729':actual,'local_neighborhood':rank,
                        'nearby_boundary_Tet10_24_max_centroid_dist_mm':neighbors[-1][0]*1000})
        result['meshes'][name]={'sha256':sha,'bad':bad,
               'pore_boundary_tet_count_corner_face_proxy':len(boundary)}
    OUT.parent.mkdir()
    OUT.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
