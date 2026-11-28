#!/usr/bin/env python3
"""Freeze P10QP target cells using ONLY prior P10QO axes 0 and 1.

Axis 2 at q256 has never been observed; this is not a global M8 QA.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

PIN='40949482ac74d80ae7ac44c88af527a705650d34c1ffcd0de7cd01dc2bd2fa8d'


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--axis0',type=Path,required=True)
    p.add_argument('--axis1',type=Path,required=True)
    p.add_argument('--top',type=int,default=12)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    r=[json.loads(path.read_text()) for path in (a.axis0,a.axis1)]
    if a.top!=12 or any(x['mesh_sha256']!=PIN or x['stage']!='P10QO' or
         x['source_case']!=5 or x['axis']!=i or x['orders']!=[16,32,64,128] or
         x['physical_4D_FEM_approved'] or len(x['cells'])!=30 for i,x in enumerate(r)):
        raise ValueError('P10QP_TRAINING_DATA_OR_LOCKED_SCOPE_MISMATCH')
    if [(x['index'],x['group']) for x in r[0]['cells']]!=[(x['index'],x['group']) for x in r[1]['cells']] or \
       r[0]['child_input_sha256']!=r[1]['child_input_sha256']:
        raise ValueError('P10QP_TRAINING_IDENTITIES_INCONSISTENT')
    ranks=[]
    for left,right in zip(r[0]['cells'],r[1]['cells']):
        dif=[]
        for term in (left,right):
            dif.append(abs(term['order']['128']['cut_gradient_m3']-
                           term['order']['64']['cut_gradient_m3']))
        ranks.append({'index':left['index'],'group':left['group'],
                      'axis0_abs_delta_m3':dif[0],'axis1_abs_delta_m3':dif[1],
                      'training_two_axis_score_m3':sum(dif)})
    ranks.sort(key=lambda x:(-x['training_two_axis_score_m3'],x['index']))
    total=sum(x['training_two_axis_score_m3'] for x in ranks)
    chosen=ranks[:a.top]
    out={'stage':'P10QP','mesh_sha256':PIN,'source_case':5,'original_element_id':5865,
         'training_only_axes':[0,1],
         'training_orders':[64,128],'unseen_order_to_predict':256,
         'never_used_axis2_or_q256_for_selection':True,
         'selection_rule':'top 12 sum of absolute q64-to-q128 gradient changes on axes 0 and 1',
         'selected_indices_ranked':[x['index'] for x in chosen],
         'selected_score_coverage_fraction':sum(x['training_two_axis_score_m3'] for x in chosen)/total,
         'excluded_score_fraction':sum(x['training_two_axis_score_m3'] for x in ranks[a.top:])/total,
         'ranked_all_30':ranks,
         'training_source_sha256':{str(i):hashlib.sha256(path.read_bytes()).hexdigest()
                                    for i,path in enumerate((a.axis0,a.axis1))},
         'locked_panel_candidates':[
             {'panel_s':2,'panel_t':2,'nodes_per_panel_direction':64,'total_transverse_points':16384},
             {'panel_s':4,'panel_t':4,'nodes_per_panel_direction':32,'total_transverse_points':16384}],
         'uniform_comparators':[128,256],
         'empirical_relative_L1_target':1e-6,
         'no_error_bound_certified':True,'physical_4D_FEM_approved':False,
         'no_Gmsh_no_CAD_no_FEM_no_mesh_change':True}
    a.output.write_text(json.dumps(out,indent=2)+'\n')
    print('P10QP_FROZEN_TARGETS_NOT_FEM',out['selected_indices_ranked'])
    print('P10QP_TRAINING_TWO_AXIS_COVERAGE',out['selected_score_coverage_fraction'])


if __name__=='__main__':main()
