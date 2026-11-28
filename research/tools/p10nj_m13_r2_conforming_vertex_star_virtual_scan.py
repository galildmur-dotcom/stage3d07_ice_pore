#!/usr/bin/env python3
"""P10NJ: shared-node conforming virtual displacement of R2 bad Tet10 vertex star."""
import hashlib,json,sys
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'research/tools'))
from p10nf_m13_pore_tri6_face_audit_readonly import read,SOURCES
from p10hv_independent_scan import rule,EDGE

OUT=ROOT/'p10nj_m13_vertex_star/P10NJ_M13_R2_CONFORMING_VERTEX_STAR_VIRTUAL_SCAN.json'
C=np.array([0.,0.,.03]);R=.001
_,D,W=rule(9)
DELTAS_MM=(-.030,-.015,-.005,0.,.005,.010,.015,.020,.030,.050,.075)

def geom(p):
    J=np.einsum('nic,qij->nqcj',p,D,optimize=True)
    s=np.linalg.svd(J,compute_uv=False)
    det=np.linalg.det(J)
    return {'min_singular_ratio':np.min(s[:,:,-1]/s[:,:,0],axis=1),
            'min_detJ':det.min(axis=1),
            'volume':(det*W[None,:]).sum(axis=1)}

def main():
    if OUT.exists():raise RuntimeError('P10NJ no overwrite')
    name,mesh,locator,expected=SOURCES[1]
    assert name=='R2' and hashlib.sha256(mesh.read_bytes()).hexdigest()==expected
    loc=json.loads(locator.read_text(encoding='utf-8-sig'))
    assert loc['mesh_sha256']==expected and loc['failed_element_count_unique']==1
    bad=next(r for r in loc['elements'] if r['below_threshold'])
    assert bad['element_tag']==9478
    nodes,tets,surface=read(mesh)
    surface_nodes=set(i for _,c in surface.values() for i in c)
    target=tets[9478]
    inner=[k for k in target[:4] if k not in surface_nodes]
    assert len(inner)==1
    pivot=inner[0]
    incident={tag:conn for tag,conn in tets.items() if pivot in conn[:4]}
    assert len(incident)>1
    pore_corners=[k for k in target[:4] if k!=pivot]
    midpoint=np.mean([nodes[k] for k in pore_corners],axis=0)
    direction=(midpoint-C)/np.linalg.norm(midpoint-C)
    # Map each incident Tet10 corner edge to its *shared global* midnode.
    moved_mid=set()
    for tag,conn in incident.items():
        fourth=conn[:4].index(pivot)
        for k,(i,j) in enumerate(EDGE):
            if fourth in (i,j):moved_mid.add(conn[4+k])
    assert pivot not in surface_nodes and not moved_mid & surface_nodes
    affected_nodes={pivot}|moved_mid
    # Check closure: no element outside pivot star shares an affected midnode.
    # Otherwise its high-order geometry would also require updating.
    outside=[tag for tag,cn in tets.items() if tag not in incident and any(k in affected_nodes for k in cn)]
    assert not outside,('non-star elements share changed nodes',outside[:20])
    ids=list(incident)
    original=np.array([[nodes[k] for k in incident[tag]] for tag in ids])
    initial=geom(original)
    target_i=ids.index(9478)
    assert np.all(initial['min_detJ']>0)
    results=[]
    for dmm in DELTAS_MM:
        delta=direction*dmm*.001
        changed={pivot:nodes[pivot]+delta}
        changed.update({k:nodes[k]+delta/2 for k in moved_mid})
        if any(np.linalg.norm(p-C)<R for p in changed.values()):
            physically_valid=False
        else:physically_valid=True
        p=np.array([[changed.get(k,nodes[k]) for k in incident[tag]] for tag in ids])
        stat=geom(p)
        volumes=stat['volume']/initial['volume']
        vmin=float(volumes.min());vmax=float(volumes.max())
        results.append({'delta_mm':dmm,'off_pore_corner_remains_in_ice':physically_valid,
           'all_729_detJ_positive':bool(np.all(stat['min_detJ']>0)),
           'star_min_sigma_ratio':float(stat['min_singular_ratio'].min()),
           'star_min_sigma_ratio_factor_vs_base':float(stat['min_singular_ratio'].min()/initial['min_singular_ratio'].min()),
           'star_min_detJ':float(stat['min_detJ'].min()),
           'target_9478_min_sigma_ratio':float(stat['min_singular_ratio'][target_i]),
           'target_9478_sigma_ratio_factor_vs_base':float(stat['min_singular_ratio'][target_i]/initial['min_singular_ratio'][target_i]),
           'target_9478_volume_ratio':float(volumes[target_i]),
           'star_min_individual_volume_ratio':vmin,
           'star_max_individual_volume_ratio':vmax,
           'star_total_volume_ratio':float(stat['volume'].sum()/initial['volume'].sum()),
           'star_elements_worse_sigma_than_baseline_count':int(np.count_nonzero(stat['min_singular_ratio']<initial['min_singular_ratio']-1e-12)),
           'star_min_sigma_worst_tet_tag':int(ids[int(np.argmin(stat['min_singular_ratio']))])})
    result={'protocol':'P10NJ_READONLY_VIRTUAL_CONFORMING_NODE_STAR_M13_R2',
      'status':'PASS_SOURCE_ONLY_NO_MESH_WRITE_NO_GMSH_NO_FEM_NO_MARKER',
      'warning':'Shared-node conformity in pivot star is enforced, pore nodes fixed; virtual positions do not form an approved full mesh. 729QP positivity not a proof between sample points. Canonical Gmsh minSJ unmeasured.',
      'mesh_sha256':expected,'pivot_corner_node_tag':pivot,'affected_star_Tet10_count':len(ids),
      'affected_incident_edge_midnodes_count':len(moved_mid),
      'changed_nodes_all_off_pore':True,'star_tet_tags':ids,
      'pivot_radial_direction':direction.tolist(),'baseline_worst_tag':int(ids[np.argmin(initial['min_singular_ratio'])]),
      'baseline_star_min_sigma_ratio':float(initial['min_singular_ratio'].min()),
      'baseline_target_9478_sigma_ratio':float(initial['min_singular_ratio'][target_i]),
      'delta_trials':results,'mesh_generation_attempts':0,'FEM_attempts':0}
    OUT.parent.mkdir()
    OUT.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'pivot_node':pivot,'star_Tet10':len(ids),'midnodes':len(moved_mid),
      'baseline':result['baseline_star_min_sigma_ratio'],
      'trials':[{k:t[k] for k in ('delta_mm','star_min_sigma_ratio','target_9478_sigma_ratio_factor_vs_base','star_min_individual_volume_ratio','star_max_individual_volume_ratio','star_elements_worse_sigma_than_baseline_count')} for t in results]},indent=2))

if __name__=='__main__':main()
