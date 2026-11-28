#!/usr/bin/env python3
"""Independent P10QH review of immutable M8, P10QG/P10QH QA contracts.

This audit deliberately does not import the new P10QH algorithm modules.
Read-only, no CAD, no mesh generation, no FEM.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


SHA='40949482ac74d80ae7ac44c88af527a705650d34c1ffcd0de7cd01dc2bd2fa8d'


def require(check,reason):
    if not check:
        raise AssertionError(f'P10QH_INDEPENDENT_AUDIT_STOP_{reason}')


def lookup(cases,level,radial,polar):
    found=[x for x in cases if x.get('bezier_subdivision_levels')==level
           and x['radial_bin']==radial and x['mu_bin']==polar]
    require(len(found)==1,'CASE_NOT_UNIQUE')
    return found[0]


def old(cases,radial,polar):
    found=[x for x in cases if x['radial_bin']==radial and x['mu_bin']==polar]
    require(len(found)==1,'OLD_CASE_NOT_UNIQUE')
    return found[0]


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for opt in ('mesh','p10qg-depth11','p10qg-depth15','p10qh-depth11','p10qh-depth15','p10qh-gradient','output'):
        p.add_argument('--'+opt,required=True,type=Path)
    v=vars(p.parse_args())
    require(hashlib.sha256(v['mesh'].read_bytes()).hexdigest()==SHA,'M8_PIN')
    g11,g15,h11,h15,gradient=[json.loads(v[key].read_text()) for key in
          ('p10qg_depth11','p10qg_depth15','p10qh_depth11','p10qh_depth15','p10qh_gradient')]
    for record in (g11,g15,h11,h15,gradient):
        require(record['mesh_sha256']==SHA,'REPORT_M8_PIN')
        require(not record.get('physical_4D_FEM_approved',False),'PHYSICAL_FEM_PREMATURE')
        require(not record.get('fem_started',False) and not record.get('physical_FEM_run',False),'UNEXPECTED_FEM')
        require(not record.get('gmsh_generated',False) and not record.get('Gmsh_run',False),'UNEXPECTED_GMSH')
    require(g11['max_depth']==11 and g15['max_depth']==15,'PRIOR_DEPTH')
    require(h11['max_spherical_depth']==11 and h15['max_spherical_depth']==15,'NEW_DEPTH')
    require(h11['levels']==[0,1,2] and h15['levels']==[2],'NEW_REFINEMENT_LEVELS')
    require(h11['unique_real_curved_faces']==25911 and h15['near_pore_candidate_faces']==10017,'REAL_TET10_FACES')
    require(len(gradient['runs'])==8 and len(gradient['holdouts'])==4,'GRADIENT_HOLDOUT_COUNT')
    comparisons=[];improved=0
    for r in (0,4):
        for mu in (0,9):
            c0=lookup(h11['cases'],0,r,mu)
            c1=lookup(h11['cases'],1,r,mu)
            c2=lookup(h11['cases'],2,r,mu)
            p11=old(g11['cases'],r,mu)
            p15=old(g15['cases'],r,mu)
            n15=lookup(h15['cases'],2,r,mu)
            require(abs(c0['pure_volume_fraction']-p11['certified_pure_volume_fraction_of_ideal'])<1e-12,'DEPTH11_NEGATIVE_CONTROL')
            require(c0['spherical_boxes_visited']==p11['subboxes_visited'],'DEPTH11_CELL_COUNT_NEGATIVE_CONTROL')
            for x in (c0,c1,c2,n15):
                require(abs(x['pure_volume_fraction']+x['unresolved_volume_fraction']-1)<2e-11,'VOLUME_PARTITION')
                require(x['independent_pure_box_locator_checks']>=12,'INDEPENDENT_LOCATOR_FALSIFICATION')
            require(c0['pure_volume_fraction']<=c1['pure_volume_fraction']+1e-12 and
                    c1['pure_volume_fraction']<=c2['pure_volume_fraction']+1e-12,'SUBPATCH_MONOTONICITY')
            require(c2['pure_volume_fraction']<=n15['pure_volume_fraction']+1e-12,'DEPTH_MONOTONICITY')
            gain=n15['pure_volume_fraction']-p15['certified_pure_volume_fraction_of_ideal']
            require(gain>0,'NO_DEPTH15_GAIN')
            require(n15['spherical_boxes_visited']<p15['subboxes_visited'],'NO_DEPTH15_CELL_REDUCTION')
            improved+=1
            comparison={'radial_bin':r,'mu_bin':mu,
                        'P10QG_depth15_pure_fraction':p15['certified_pure_volume_fraction_of_ideal'],
                        'P10QH_depth15_pure_fraction':n15['pure_volume_fraction'],
                        'absolute_pure_fraction_gain_percentage_points':100*gain,
                        'relative_pure_fraction_multiplier':n15['pure_volume_fraction']/p15['certified_pure_volume_fraction_of_ideal'],
                        'P10QG_boxes':p15['subboxes_visited'],
                        'P10QH_boxes':n15['spherical_boxes_visited'],
                        'relative_box_count_reduction':1-n15['spherical_boxes_visited']/p15['subboxes_visited']}
            comparisons.append(comparison)
    equal=gradient['equal_work_cases'];require(len(equal)==4,'GRADIENT_CASES')
    for x in equal:
        require(x['equal_nodes']<=24000 and x['equal_nodes']>=216,'GRADIENT_WORK_BUDGET')
        require(x['width_indicator_rel']>=0 and x['face_indicator_rel']>=0,'GRADIENT_INDICATOR_SIGN')
    gg=gradient['face_policy_L1_abs_signed_q32_discrepancy']
    require(gg['L1_absolute_relative_to_q32_L1']+1e-15>=gg['signed_absolute_relative_to_q32_L1'],'SIGNED_CANCELLATION_NOT_L1')
    report={'stage':'P10QH','status':'PASS_INDEPENDENT_DEPTH11_DEPTH15_GEOMETRIC_GRADIENT_CONTRACT_AUDIT',
            'mesh_sha256':SHA,'mesh_unchanged':True,'physical_FEM_performed':False,
            'checked_depth11_original_algorithm_regression':True,
            'checked_subpatch_refinement_monotonicity':True,
            'checked_depth15_improvement_and_less_work':True,
            'checked_equal_gradient_quadrature_work':True,
            'improved_polar_cases':improved,'comparison_depth15':comparisons,
            'conclusions_limited_to_manufactured_gradient_and_conservative_floating_broad_phase':True,
            'physical_4D_FEM_approved':False}
    v['output'].write_text(json.dumps(report,indent=2)+'\n')
    print('P10QH_INDEPENDENT_AUDIT_PASS',flush=True)


if __name__=='__main__':
    main()
