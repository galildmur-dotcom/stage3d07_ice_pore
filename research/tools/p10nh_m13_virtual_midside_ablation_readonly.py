#!/usr/bin/env python3
"""P10NH: in-memory edge-wise midside flattening diagnostic, NEVER write changed mesh."""
import hashlib,json,sys
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'research/tools'))
from p10nf_m13_pore_tri6_face_audit_readonly import read,SOURCES
from p10hv_independent_scan import rule,EDGE
OUT=ROOT/'p10nh_m13_virtual_ablation/P10NH_M13_BAD_TET10_MIDSIDE_VIRTUAL_ABLATION.json'
_,D,_=rule(9)

def metrics(p):
    J=np.einsum('ic,qij->qcj',p,D,optimize=True)
    singular=np.linalg.svd(J,compute_uv=False)
    det=np.linalg.det(J)
    return {'min_detJ_729':float(det.min()),
        'min_sigma3_over_sigma1_729':float(np.min(singular[:,-1]/singular[:,0])),
        'detJ_max_over_min':float(det.max()/det.min()) if det.min()>0 else None}

def main():
    if OUT.exists():raise RuntimeError('P10NH no overwrite')
    result={'protocol':'P10NH_IN_MEMORY_MIDSIDE_ABLATION_ONLY',
        'status':'SOURCE_ONLY_GEOMETRY_EXPERIMENT_NO_MESH_WRITE_NO_GMSH_NO_FEM',
        'warning':'Virtual straightening of pore-edge midnodes violates spherical CAD; NEVER use as accepted FEM mesh',
        'meshes':{},'mesh_generation_attempts':0,'FEM_attempts':0}
    for name,path,locator,expected in SOURCES:
        assert hashlib.sha256(path.read_bytes()).hexdigest()==expected
        rec=json.loads(locator.read_text(encoding='utf-8-sig'))
        assert rec['mesh_sha256']==expected
        nodes,tets,surface=read(path)
        surf=set(i for triple in surface for i in triple)
        entries=[]
        for bad in (x for x in rec['elements'] if x['below_threshold']):
            tag=bad['element_tag'];conn=tets[tag];p=np.asarray([nodes[i] for i in conn])
            original=metrics(p)
            tests=[]
            for k,(a,b) in enumerate(EDGE):
                pp=p.copy();pp[4+k]=(pp[a]+pp[b])/2
                m=metrics(pp)
                tests.append({'gmsh_edge_ordinal':k,'corner_indices':[a,b],
                    'endpoints_both_on_pore':bool(conn[a] in surf and conn[b] in surf),
                    'original_midside_deviation_mm':float(np.linalg.norm(p[4+k]-pp[4+k])*1000),
                    'virtual_metrics_729':m,
                    'improvement_factor_min_sigma_ratio':m['min_sigma3_over_sigma1_729']/original['min_sigma3_over_sigma1_729']})
            # One physical face of this Tet10 follows the pore boundary: its
            # three corner edges have both endpoints on the CAD face.
            curved_surface=[k for k,(a,b) in enumerate(EDGE) if conn[a] in surf and conn[b] in surf]
            def flatten(keys):
                pp=p.copy()
                for k in keys:
                    a,b=EDGE[k];pp[4+k]=(pp[a]+pp[b])/2
                return metrics(pp)
            entries.append({'tag':tag,'original_729':original,
                'per_edge_virtual_flatten':tests,
                'pore_face_edges':curved_surface,
                'virtual_flatten_all_pore_face_edges':flatten(curved_surface),
                'virtual_flatten_all_other_edges':flatten([i for i in range(6) if i not in curved_surface]),
                'virtual_flatten_all_6_edges':flatten(range(6))})
        result['meshes'][name]={'mesh_sha256':expected,'bad_elements':entries}
    OUT.parent.mkdir()
    OUT.write_text(json.dumps(result,indent=2)+'\n')
    summary=[]
    for name,mesh in result['meshes'].items():
        for x in mesh['bad_elements']:
            best=sorted(x['per_edge_virtual_flatten'],key=lambda t:t['improvement_factor_min_sigma_ratio'],reverse=True)[:3]
            summary.append({'mesh':name,'tag':x['tag'],
                'baseline_sigma_ratio':x['original_729']['min_sigma3_over_sigma1_729'],
                'flatten_pore_edges_sigma_ratio':x['virtual_flatten_all_pore_face_edges']['min_sigma3_over_sigma1_729'],
                'flatten_other_edges_sigma_ratio':x['virtual_flatten_all_other_edges']['min_sigma3_over_sigma1_729'],
                'top_3_single_edges':[(e['gmsh_edge_ordinal'],round(e['improvement_factor_min_sigma_ratio'],3)) for e in best]})
    print(json.dumps(summary,indent=2))

if __name__=='__main__':main()
