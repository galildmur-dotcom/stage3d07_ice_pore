#!/usr/bin/env python3
"""P10NI: in-memory fourth-vertex radial scan; preserve exact pore Tri6 nodes."""
import hashlib,json,sys
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'research/tools'))
from p10nf_m13_pore_tri6_face_audit_readonly import read,SOURCES
from p10hv_independent_scan import rule,EDGE

OUT=ROOT/'p10ni_m13_virtual_fourth_vertex/P10NI_M13_FOURTH_VERTEX_RADIAL_SCAN.json'
P_CENTER=np.array([0.,0.,.03]);R=.001
_,D,W=rule(9)
DELTAS_MM=(-.10,-.06,-.03,-.015,0.,.015,.03,.06,.10,.15,.20)

def metrics(p):
    J=np.einsum('ic,qij->qcj',p,D,optimize=True)
    singular=np.linalg.svd(J,compute_uv=False)
    det=np.linalg.det(J)
    return {'positive_detJ_729':bool((det>0).all()),
        'min_detJ_729':float(det.min()),
        'min_sigma3_over_sigma1_729':float(np.min(singular[:,-1]/singular[:,0])),
        'curved_volume_m3':float(np.sum(det*W))}

def main():
    if OUT.exists():raise RuntimeError('P10NI result exists; no overwrite')
    results={'protocol':'P10NI_IN_MEMORY_CAD_PORE_FACE_PRESERVED_FOURTH_VERTEX_SCAN',
       'status':'PASS_SOURCE_ONLY_NO_MESH_WRITES_NO_GMSH_NO_FEM_NO_MARKER',
       'warning':('Virtual local Tet10 variations do not update adjacent elements or enforce '
          'shared-node conformity, positive detJ between 729 samples or global mesh validity. '
          'Do not use these trial coordinates as a FEM mesh.'),
       'delta_mm':DELTAS_MM,'meshes':{},'mesh_generation_attempts':0,'FEM_attempts':0}
    summary=[]
    for name,mesh,locator,expected in SOURCES:
        assert hashlib.sha256(mesh.read_bytes()).hexdigest()==expected
        loc=json.loads(locator.read_text(encoding='utf-8-sig'))
        assert loc['mesh_sha256']==expected
        nodes,tets,surface=read(mesh)
        surf=set(i for key in surface for i in key)
        rows=[]
        for entry in (e for e in loc['elements'] if e['below_threshold']):
            cn=tets[entry['element_tag']]
            base=np.asarray([nodes[i] for i in cn])
            inner=[i for i in range(4) if cn[i] not in surf]
            assert len(inner)==1,(name,entry['element_tag'],inner)
            fourth=inner[0]
            face=[i for i in range(4) if i!=fourth]
            face_mid=base[face].mean(axis=0)
            radial=(face_mid-P_CENTER)/np.linalg.norm(face_mid-P_CENTER)
            results_delta=[]
            original=metrics(base)
            for dmm in DELTAS_MM:
                delta=radial*(dmm*.001)
                pp=base.copy();pp[fourth]+=delta
                # For each straight edge adjacent to the fourth corner, update
                # its midside point by one-half displacement. The three
                # curved pore-face edge midsides stay unchanged and on CAD.
                modified_mid=[]
                for k,(i,j) in enumerate(EDGE):
                    if fourth in (i,j):
                        pp[4+k]+=delta/2
                        modified_mid.append(4+k)
                assert len(modified_mid)==3
                assert np.array_equal(pp[face],base[face])
                assert all(np.array_equal(pp[4+k],base[4+k]) for k,(i,j) in enumerate(EDGE)
                           if fourth not in (i,j))
                m=metrics(pp)
                m.update({'delta_mm':dmm,
                    'fourth_corner_remains_in_ice':bool(np.linalg.norm(pp[fourth]-P_CENTER)>=R),
                    'sigma_ratio_factor_vs_original':m['min_sigma3_over_sigma1_729']/original['min_sigma3_over_sigma1_729'],
                    'volume_ratio_vs_original':m['curved_volume_m3']/original['curved_volume_m3']})
                results_delta.append(m)
            viable=[x for x in results_delta if x['positive_detJ_729'] and x['fourth_corner_remains_in_ice']]
            best=max(viable,key=lambda x:x['min_sigma3_over_sigma1_729'])
            rec={'tag':entry['element_tag'],'fourth_corner_index':fourth,
                'pore_face_corner_indices':face,
                'pore_face_normal_radial_direction':radial.tolist(),
                'original_729':original,'virtual_trials':results_delta,
                'best_sampled_virtual_trial':best}
            rows.append(rec)
            summary.append({'mesh':name,'tag':entry['element_tag'],
                'baseline_sigma':original['min_sigma3_over_sigma1_729'],
                'best_virtual_delta_mm':best['delta_mm'],
                'best_sigma':best['min_sigma3_over_sigma1_729'],
                'best_factor':best['sigma_ratio_factor_vs_original'],
                'best_volume_ratio':best['volume_ratio_vs_original']})
        results['meshes'][name]={'sha256':expected,'failed_tet_radial_trials':rows}
    OUT.parent.mkdir()
    OUT.write_text(json.dumps(results,indent=2)+'\n')
    print(json.dumps(summary,indent=2))

if __name__=='__main__':main()
