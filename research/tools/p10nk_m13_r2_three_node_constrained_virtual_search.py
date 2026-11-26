#!/usr/bin/env python3
"""P10NK: 3-node shared-edge conforming near-pore optimization, read-only 729QP."""
import hashlib,itertools,json,sys
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'research/tools'))
from p10nf_m13_pore_tri6_face_audit_readonly import read,SOURCES
from p10hv_independent_scan import rule,EDGE

OUT=ROOT/'p10nk_m13_three_nodes/P10NK_M13_R2_THREE_NODE_CONSTRAINED_729QP.json'
C=np.array([0.,0.,.03]);R=.001
N,D,W=rule(9)
NODES=(8680,8681,9115)
GRID_MM=({0.0,.005,.01,.015},{-.005,0.,.005},{-.005,0.,.005})

def geom(p):
    J=np.einsum('nic,qij->nqcj',p,D,optimize=True)
    s=np.linalg.svd(J,compute_uv=False)
    det=np.linalg.det(J)
    return {'min_sigma':np.min(s[:,:,-1]/s[:,:,0],axis=1),
            'min_det':np.min(det,axis=1),'volumes':(det*W[None,:]).sum(axis=1)}

def main():
    if OUT.exists():raise RuntimeError('P10NK output exists: no overwrite')
    name,path,locator,expected=SOURCES[1]
    assert name=='R2' and hashlib.sha256(path.read_bytes()).hexdigest()==expected
    nodes,tets,surface=read(path)
    faces=set(k for tri in surface for k in tri)
    assert all(n not in faces for n in NODES)
    affected={tag:conn for tag,conn in tets.items() if set(NODES)&set(conn[:4])}
    assert len(affected)>28 and 9478 in affected
    tags=list(affected)
    base=np.array([[nodes[k] for k in affected[tag]] for tag in tags])
    # Build sparse nodal coefficients for delta in millimeters.
    dirs=np.array([(nodes[n]-C)/np.linalg.norm(nodes[n]-C) for n in NODES])
    # Retain P10NJ face-centroid radial direction for the pivot; other two
    # follow their local radial directions, all away from cavity.
    badcn=affected[9478]
    face_mid=np.mean([nodes[k] for k in badcn[:4] if k in faces],axis=0)
    dirs[0]=(face_mid-C)/np.linalg.norm(face_mid-C)
    displacements=np.zeros((len(tags),10,3,len(NODES)))
    touched_midnodes={}
    for row,tag in enumerate(tags):
        conn=affected[tag]
        for ni,pivot in enumerate(NODES):
            if pivot in conn[:4]:
                local=conn[:4].index(pivot)
                displacements[row,local,:,ni]+=dirs[ni]*.001
            for edge,(i,j) in enumerate(EDGE):
                if pivot in (conn[i],conn[j]):
                    displacements[row,4+edge,:,ni]+=dirs[ni]*.0005
        # Shared edge midside must receive identical displacement regardless
        # of which neighboring tetrahedron references it.
        for i,node in enumerate(conn):
            if i>=4:
                v=displacements[row,i]
                previous=touched_midnodes.setdefault(node,v)
                if not np.array_equal(previous,v):
                    raise RuntimeError('shared midside inconsistency '+str(node))
    changed_nodes=set(NODES)|{k for k,v in touched_midnodes.items() if np.any(v)}
    assert not changed_nodes & faces
    closure=[tag for tag,conn in tets.items() if tag not in affected and any(k in changed_nodes for k in conn)]
    assert not closure,('nonincident tets share moved nodes',closure[:15])
    initial=geom(base)
    assert np.all(initial['min_det']>0)
    target_index=tags.index(9478)
    baseline=float(initial['min_sigma'].min())
    assert tags[int(np.argmin(initial['min_sigma']))]==9478
    allresults=[]
    combos=sorted(itertools.product(*[sorted(x) for x in GRID_MM]))
    for combo in combos:
        x=np.array(combo)
        p=base+np.einsum('nicj,j->nic',displacements,x,optimize=True)
        g=geom(p)
        ratios=g['volumes']/initial['volumes']
        positive=bool(np.all(g['min_det']>0))
        individual_volume_ok=bool(np.min(ratios)>=.9 and np.max(ratios)<=1.1)
        result={'node_delta_mm':dict(zip(map(str,NODES),map(float,x))),
            'positive_detJ_729_all':positive,
            'all_individual_volume_ratios_in_0p9_1p1':individual_volume_ok,
            'min_sigma_ratio_all':float(g['min_sigma'].min()),
            'minimum_improvement_factor':float(g['min_sigma'].min()/baseline),
            'worst_tet_tag':tags[int(np.argmin(g['min_sigma']))],
            'target_9478_sigma_ratio':float(g['min_sigma'][target_index]),
            'volume_ratio_min_max':[float(ratios.min()),float(ratios.max())],
            'star_total_curved_volume_ratio':float(g['volumes'].sum()/initial['volumes'].sum()),
            'worsened_individual_sigma_count':int(np.count_nonzero(g['min_sigma']<initial['min_sigma']-1e-12)),
            'max_individual_relative_sigma_drop':float(np.max(np.maximum(0,1-g['min_sigma']/initial['min_sigma']))),
            'feasible':positive and individual_volume_ok}
        allresults.append(result)
    feasible=[v for v in allresults if v['feasible']]
    best=max(feasible,key=lambda v:(v['min_sigma_ratio_all'],-v['max_individual_relative_sigma_drop']))
    # Pareto alternatives to the best chosen with no more than 10% local volume
    # change. Do not claim canonical minSJ would pass.
    output={'protocol':'P10NK_M13_R2_READONLY_THREE_NODE_CONSTRAINED_729QP',
      'status':'PASS_SOURCE_ONLY_NO_GMSH_NO_MESH_NO_FEM',
      'mesh_sha256':expected,'pore_nodes_fixed':True,
      'globally_shared_midside_positions_consistent':True,
      'affected_Tet10_count':len(tags),'changed_node_count':len(changed_nodes),
      'pivot_and_neighbor_nodes':NODES,'candidate_count':len(allresults),
      'feasible_count':len(feasible),'baseline_worst_tet':9478,
      'baseline_worst_sigma_ratio':baseline,'local_volume_bounds':[.9,1.1],
      'best_feasible':best,'all_candidates':allresults,
      'limitations':['729QP singular ratio is not Gmsh minSJ/minSICN',
        'Global Gmsh mesh not written; possible local interpolation and mesher optimization differences',
        'Only chosen three radial degrees of freedom tested; no multi-direction global optimum claimed'],
      'mesh_generation_attempts':0,'FEM_attempts':0}
    OUT.parent.mkdir()
    OUT.write_text(json.dumps(output,indent=2)+'\n')
    print(json.dumps({'affected_Tet10':len(tags),'changed_nodes':len(changed_nodes),
      'candidates':len(allresults),'feasible':len(feasible),
      'best':best},indent=2))

if __name__=='__main__':main()
