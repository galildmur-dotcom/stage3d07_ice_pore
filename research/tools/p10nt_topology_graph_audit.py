#!/usr/bin/env python3
"""P10NT: anchored graph refinement for Tet10 vertex topology, no FEM/mesh write."""
import collections
import hashlib
import json
import sys
import time
import traceback
from pathlib import Path

import numpy as np
from p10nq_native_geometry_correspondence_windows import MESH, SHA, sample
from p10nr_coordinate_topology import boundary_index, match_by_position, classify
from p10ns_volume_audit import EDGES

OUTPUT = Path(__file__).resolve().parent / 'P10NT_VOLUME_GRAPH_CORRESPONDENCE_RESULT.json'


def topology(snap):
    neighbors=collections.defaultdict(set)
    incident=collections.Counter()
    vertices=set()
    for t in snap['tets'].values():
        c=t[:4]
        vertices.update(c)
        for i in c:incident[i]+=1
        for k,(i,j) in enumerate(EDGES):
            a,b=c[i],c[j]
            neighbors[a].add(b)
            neighbors[b].add(a)
    return vertices,neighbors,incident


def unique_anchor_labels(before,after,vb,va):
    bnd_b=boundary_index(before)&vb
    bnd_a=boundary_index(after)&va
    anchor=match_by_position(before,after,bnd_b,bnd_a)
    return ({old:f'A{i}' for i,old in enumerate(sorted(anchor))},
            {new:f'A{i}' for i,new in enumerate(anchor[n] for n in sorted(anchor))},
            anchor)


def digest(parts):
    return hashlib.sha256('|'.join(parts).encode('utf-8')).hexdigest()


def refine(snap_a,snap_b,max_rounds=12):
    vb,nb,ib=topology(snap_a)
    va,na,ia=topology(snap_b)
    anchors_b,anchors_a,anchor_map=unique_anchor_labels(snap_a,snap_b,vb,va)
    labels_b={n:anchors_b.get(n,f'I:{len(nb[n])}:{ib[n]}') for n in vb}
    labels_a={n:anchors_a.get(n,f'I:{len(na[n])}:{ia[n]}') for n in va}
    rounds=[]
    for k in range(max_rounds+1):
        cb,ca=collections.Counter(labels_b.values()),collections.Counter(labels_a.values())
        unique=sum(m==1 for m in cb.values())
        rounds.append({'round':k,'unique_colors_before':unique,
                       'color_histogram_equal':cb==ca,
                       'unresolved_vertices_before':sum(m for m in cb.values() if m>1),
                       'distinct_colors_before':len(cb)})
        if cb!=ca:
            return {'status':'COLOR_MULTIPLICITY_MISMATCH','anchors':len(anchor_map),
                    'rounds':rounds,'vertex_bijection':None}
        if unique==len(vb) and len(vb)==len(va):
            inverse={label:node for node,label in labels_a.items()}
            mapping={node:inverse[label] for node,label in labels_b.items()}
            return {'status':'UNIQUE_GRAPH_LABEL_BIJECTION','anchors':len(anchor_map),
                    'rounds':rounds,'vertex_bijection':mapping}
        if k==max_rounds:break
        next_b={n:digest([labels_b[n]]+sorted(labels_b[m] for m in nb[n])) for n in vb}
        next_a={n:digest([labels_a[n]]+sorted(labels_a[m] for m in na[n])) for n in va}
        labels_b,labels_a=next_b,next_a
    return {'status':'AMBIGUOUS_GRAPH_LABELS','anchors':len(anchor_map),
            'rounds':rounds,'vertex_bijection':None}


def verify_elements(before,after,mapping):
    def signature(snap, remap=None):
        out={}
        duplicate=0
        for eid,conn in snap['tets'].items():
            key=tuple(sorted(remap[v] if remap is not None else v for v in conn[:4]))
            if key in out:duplicate+=1
            out[key]=(eid,conn)
        if duplicate:raise ValueError(f'duplicate tetrahedra: {duplicate}')
        return out
    old,new=signature(before,mapping),signature(after)
    shared=old.keys()&new.keys()
    delta=[]
    boundary_old=boundary_index(before)
    boundary_new=boundary_index(after)
    shifted_boundary_mid=0
    edge_mismatch=0
    for key in shared:
        co=old[key][1];cn=new[key][1]
        oe={tuple(sorted((mapping[co[i]],mapping[co[j]]))):co[4+k]
            for k,(i,j) in enumerate(EDGES)}
        ne={tuple(sorted((cn[i],cn[j]))):cn[4+k]
            for k,(i,j) in enumerate(EDGES)}
        if oe.keys()!=ne.keys():edge_mismatch+=1;continue
        for edge in oe:
            a,b=oe[edge],ne[edge]
            d=float(np.linalg.norm(before['nodes'][a]-after['nodes'][b]))
            delta.append(d)
            if d>=1e-12 and (a in boundary_old or b in boundary_new):
                shifted_boundary_mid+=1
    cd=np.array([np.linalg.norm(before['nodes'][a]-after['nodes'][b])
                 for a,b in mapping.items()])
    return {'tet_count_before':len(old),'tet_count_after':len(new),
            'matched_tet_vertex_sets':len(shared),
            'missing_after_vertex_mapping':len(old.keys()-new.keys()),
            'extra_after_vertex_mapping':len(new.keys()-old.keys()),
            'edge_association_mismatch_tets':edge_mismatch,
            'verified_vertex_topology_preserved':len(shared)==len(old)==len(new) and edge_mismatch==0,
            'corner_displacement_max_mm':float(cd.max())*1000,
            'corner_displacement_p95_mm':float(np.percentile(cd,95))*1000,
            'corner_displacement_median_mm':float(np.median(cd))*1000,
            'mid_edge_occurrences':len(delta),
            'mid_edge_displacement_max_mm':max(delta,default=0)*1000,
            'mid_edge_displacement_p95_mm':float(np.percentile(delta,95))*1000 if delta else None,
            'shifted_boundary_mid_edge_occurrences':shifted_boundary_mid}


def selftest():
    # Two tetrahedra share one interior vertex; only corners 1..4 are anchored.
    a={1:(0.,0.,0.),2:(1.,0.,0.),3:(0.,1.,0.),4:(0.,0.,1.),5:(.3,.3,.3)}
    b={101:a[1],102:a[2],103:a[3],104:a[4],105:(.31,.28,.34)}
    def make(points,tets,anchors):
        return {'nodes':{i:np.array(p,float) for i,p in points.items()},
                'tets':{j:tuple(c)+(0,)*6 for j,c in enumerate(tets)},
                'by_phys':{8:{'node_ids':set(anchors),'elements':{}}}}
    before=make(a,[(1,2,3,5),(1,2,4,5)],[1,2,3,4])
    after=make(b,[(101,102,103,105),(101,102,104,105)],[101,102,103,104])
    r=refine(before,after)
    assert r['status']=='UNIQUE_GRAPH_LABEL_BIJECTION'
    assert r['vertex_bijection'][5]==105
    assert len(r['vertex_bijection'])==5
    broken=make(b,[(101,102,103,105),(101,102,103,105)],[101,102,103,104])
    try:
        refine(before,broken)
    except ValueError:
        pass
    else:
        raise AssertionError('missing corner vertex was not detected')
    print('P10NT_SYNTHETIC_GRAPH_BIJECTION_PASS',flush=True)


def main():
    selftest()
    if '--selftest' in sys.argv:return
    import gmsh
    if OUTPUT.exists():raise RuntimeError('P10NT_STOP: output exists')
    if gmsh.__version__!='4.15.2':raise RuntimeError('Gmsh 4.15.2 required')
    if hashlib.sha256(MESH.read_bytes()).hexdigest()!=SHA:raise RuntimeError('M13 R2 SHA mismatch')
    report={'protocol':'P10NT_TET10_ANCHORED_GRAPH_CORRESPONDENCE',
            'source_sha256':SHA,'status':'STARTED',
            'FEM_attempts':0,'mesh_generation_attempts':0,
            'mesh_files_written':0,'marker_uses':0}
    gmsh.initialize()
    try:
        gmsh.option.setNumber('General.Terminal',1)
        gmsh.option.setNumber('Mesh.HighOrderFixBoundaryNodes',1)
        gmsh.option.setNumber('Mesh.HighOrderIterMax',50)
        gmsh.option.setNumber('Mesh.HighOrderPassMax',5)
        gmsh.option.setNumber('Mesh.HighOrderNumLayers',2)
        gmsh.open(str(MESH));before=sample(gmsh)
        t0=time.monotonic()
        gmsh.model.mesh.optimize('HighOrderElastic',force=True)
        report['optimizer_s']=time.monotonic()-t0
        after=sample(gmsh)
        report['boundary_tri6_preserved']=classify(before,after)['all_boundary_tri6_preserved']
        result=refine(before,after)
        mapping=result.pop('vertex_bijection')
        report['graph_refinement']=result
        if mapping is not None:
            report['volume_verification']=verify_elements(before,after,mapping)
        else:
            report['volume_verification']={'status':'INDETERMINATE_NO_UNIQUE_BIJECTION'}
        report['status']='AUDIT_COMPLETED_NO_R3_NO_FEM'
        report['acceptance']='DIAGNOSTIC_ONLY_NO_M13_GO'
    except Exception as e:
        report['status']='AUDIT_ERROR'
        report['error']=repr(e)
        report['traceback']=traceback.format_exc()[-4500:]
    finally:
        gmsh.finalize()
    with OUTPUT.open('x',encoding='utf-8') as f:
        json.dump(report,f,indent=2)
        f.write('\n')
    print('P10NT_DONE',report['status'],flush=True)
    if report['status']!='AUDIT_COMPLETED_NO_R3_NO_FEM':raise RuntimeError('P10NT_AUDIT_ERROR: see JSON')


if __name__=='__main__':
    try:main()
    except Exception as e:
        print('P10NT_STOP',repr(e),flush=True)
        sys.exit(2)
