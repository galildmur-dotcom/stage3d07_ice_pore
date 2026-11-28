#!/usr/bin/env python3
"""P10IA: no-Gmsh, no-FEM high-kappa spherical wall seed feasibility audit."""
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import p10hy_surface_smoothness_audit as wall
import p10hz_matched_wall_h_audit as matched

C=np.array([0.,0.,.03])
R_MM=1.0

def nearest_arc_mm(unit_dirs, existing, chunk=512):
    out=np.empty(len(unit_dirs))
    for i in range(0,len(unit_dirs),chunk):
        dots=unit_dirs[i:i+chunk]@existing.T
        out[i:i+chunk]=R_MM*np.arccos(np.clip(np.max(dots,axis=1),-1,1))
    return out

def select_seeds(dirs,kappa,base,minimum_distance_mm,dist_any=None,min_any_mm=0.0,max_seeds=128):
    if dist_any is None:dist_any=base
    eligible=np.flatnonzero((kappa>=.8)&(base>=minimum_distance_mm)&(dist_any>=min_any_mm))
    selected=[]
    current=base.copy()
    for _ in range(max_seeds):
        inds=eligible[current[eligible]>=minimum_distance_mm]
        if not len(inds):break
        # Highest missing spatial coverage, mild kappa tie-break.
        priority=current[inds]*(.75+.25*kappa[inds])
        idx=inds[np.argmax(priority)]
        selected.append(int(idx))
        d=R_MM*np.arccos(np.clip(dirs@dirs[idx],-1,1))
        current=np.minimum(current,d)
    return selected,current

def summary(x):
    return {'n':len(x),'min':float(x.min()),'median':float(np.median(x)),
            'p95':float(np.percentile(x,95)),'max':float(x.max())}

def main(csvpath,m1path):
    source,val=wall.source(csvpath)
    raw=m1path.read_bytes()
    assert hashlib.sha256(raw).hexdigest()=='47460969be26c2bd0a15e0b1425806fa350aa09aa2b4ac9f80605b433fc65ca7'
    base=matched.surface(raw)
    corner_ids=np.unique(base['faces'])
    existing=(base['nodes'][corner_ids]-C)/.001
    wall_all=np.unique(wall.read_faces(raw))
    all_wall_nodes=(base['nodes'][wall_all]-C)/.001
    dirs=matched.fixed_sphere_directions()
    kappa=wall.eval_kappa(source,val,C+dirs*.001)
    dist=nearest_arc_mm(dirs,existing)
    dist_to_any=nearest_arc_mm(dirs,all_wall_nodes)
    high=kappa>=.8
    result={'protocol':'P10IA_SOURCE_ONLY_M1_CAD_HIGH_KAPPA_WALL_SEED_FEASIBILITY',
            'no_new_mesh_or_FEM':True,'pinned_M1_SHA256':hashlib.sha256(raw).hexdigest(),
            'source': 'original P10HA mechanical C2 kappa',
            'wall_corner_nodes':len(existing),'wall_all_Tri6_nodes':len(all_wall_nodes),
            'fixed_probe_directions':len(dirs),
            'high_kappa_probe_count':int(np.sum(high)),
            'high_kappa_distance_to_nearest_M1_corner_mm':summary(dist[high]),
            'high_kappa_distance_to_nearest_any_M1_Tri6_node_mm':summary(dist_to_any[high]),
            'all_distance_to_nearest_M1_corner_mm':summary(dist),
            'thresholds':{}}
    for t in (.10,.12,.15,.18,.20,.24):
        selected,remain=select_seeds(dirs,kappa,dist,t,dist_to_any,.06)
        result['thresholds'][str(t)]={
            'minimum_seed_separation_mm':t,
            'minimum_distance_to_any_old_Tri6_node_mm':.06,
            'high_kappa_points_eligible_before_greedy':int(np.sum(high&(dist>=t)&(dist_to_any>=.06))),
            'seed_count':len(selected),
            'seed_kappa':summary(kappa[selected]) if selected else {'n':0},
            'selected_seed_min_distance_to_any_M1_Tri6_node_mm':float(dist_to_any[selected].min()) if selected else None,
            'max_high_kappa_distance_after_seeds_mm':float(remain[high].max()),
            'max_high_kappa_distance_before_mm':float(dist[high].max()),
            'seed_dirs_first12':[list(map(float,dirs[i])) for i in selected[:12]]
        }
    print(json.dumps(result,indent=2,ensure_ascii=False))

if __name__=='__main__':main(Path(sys.argv[1]),Path(sys.argv[2]))
