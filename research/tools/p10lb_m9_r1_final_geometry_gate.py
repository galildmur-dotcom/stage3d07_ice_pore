#!/usr/bin/env python3
"""Read-only acceptance gate for actual M9 R1 after P10KZ and canonical P10LA."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path

M9_SHA='a40aca54636a752afe4d7babe9d03e741b2e988b9ad3dbb6f356728bff035a58'
M8_SHA='40949482ac74d80ae7ac44c88af527a705650d34c1ffcd0de7cd01dc2bd2fa8d'

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--mesh',required=True,type=Path)
    ap.add_argument('--d029',required=True,type=Path)
    ap.add_argument('--d031',required=True,type=Path)
    ap.add_argument('--output',required=True,type=Path)
    a=ap.parse_args()
    assert not a.output.exists()
    assert sha(a.mesh)==M9_SHA
    d29=json.loads(a.d029.read_text(encoding='utf8'))
    d31=json.loads(a.d031.read_text(encoding='utf8'))
    assert d29['m9']['mesh_sha256']==M9_SHA and d29['m8']['mesh_sha256']==M8_SHA
    assert d29['D029_PASS'] and d29['CAD_PASS'] and d29['curved_detJ_positive_PASS'] and d29['physical_tags_PASS']
    assert d29['full_GEOMETRY_GO'] is False
    assert d31['protocol']=='P10LA_M9_R1_INDEPENDENT_GMSH_READONLY_D031'
    assert d31['gmsh_version']=='4.15.2' and d31['mesh_sha256']==M9_SHA and d31['Tet10']==13166
    assert d31['physical_surface_tags']==list(range(2,10)) and d31['quality_gate_pass'] is True
    targets={'minSICN':.20,'minSJ':.40,'gamma':.15,'minDetJac':0.}
    assert all(d31['qualities'][name]['nonpositive']==0 and
               d31['qualities'][name]['min']>threshold if name=='minDetJac' else
               d31['qualities'][name]['min']>=threshold
               for name,threshold in targets.items())
    for pole in ('near_p0_N','near_p0_S'):
        rec=d29['D029_poles'][pole]
        assert rec['pass'] and .75<=rec['729']['Veff_ratio']<=.85
    record={'protocol':'P10LB_M9_R1_FINAL_D029_D031_GEOMETRY_ACCEPTANCE',
        'status':'GEOMETRY_GO_ONLY_NO_FEM',
        'M8_reference_mesh_sha256':M8_SHA,'mesh_sha256':M9_SHA,
        'mesh_nodes':19236,'Tet10':13166,'pore_Tri6':734,
        'source_d029_json_sha256':sha(a.d029),'source_d031_json_sha256':sha(a.d031),
        'D029_adaptation_target_GO':True,'D031_geometry_quality_GO':True,
        'D029_poles_729':{p:d29['D029_poles'][p]['729'] for p in ('near_p0_N','near_p0_S')},
        'D031_quality_minima':{k:float(d31['qualities'][k]['min']) for k in targets},
        'curved_min_detJ_27_343_729':d29['m9']['min_curved_detJ_27_343_729'],
        'CAD_closure_rel_729':d29['m9']['CAD_closure_rel_729'],
        'mesh_generation_attempts_in_this_audit':0,'FEM_attempts':0,
        'spatial_convergence_proven':False,
        'next_step':'separately pinned M9 full4D Windows one-shot, no existing marker reuse'}
    a.output.write_text(json.dumps(record,indent=2,ensure_ascii=False)+'\n',encoding='utf8')
    print(json.dumps(record,indent=2,ensure_ascii=False))

if __name__=='__main__':main()
