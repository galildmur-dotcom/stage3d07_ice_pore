#!/usr/bin/env python3
"""Read-only quality GO and distinct regional D-029 target status for P10ID."""
from __future__ import annotations
import json
import math
from pathlib import Path

import p10ic_tet10_quality_audit as quality
import p10hv_independent_scan as scan

HERE=Path(__file__).resolve().parent
OLD=HERE/'P10GT_HXT10.msh'
NEW=HERE/'P10ID_M2_3D_UNVERIFIED.msh'
EXPECTED='8acba5a9b3185429c200989015a7dfffb2b19452170db9d508da3e59ea0102f5'

def regions(path):
    xyz,tets,_=scan.read_msh(path.read_bytes())
    q27=scan.evaluate(xyz,tets,3,None)
    return scan.groups(scan.evaluate(xyz,tets,9,q27['volume']))

def main():
    old=quality.audit(OLD)
    new=quality.audit(NEW)
    if not old['matches_pinned_original_M1'] or new['file_sha256']!=EXPECTED:
        raise RuntimeError('Unexpected original M1 or candidate M2 fingerprint')
    vals=new['gmsh_curved_element_qualities']
    q=new['independent_curved_Tet10_quadrature']
    checks={
        'all_minSICN_ge_0p20':vals['minSICN']['min']>=.20,
        'all_minSJ_ge_0p40':vals['minSJ']['min']>=.40,
        'all_gamma_ge_0p15':vals['gamma']['min']>=.15,
        'adaptive_Gmsh_minDetJac_positive':vals['minDetJac']['min']>0,
        'independent_27_343_729_detJ_positive':q['positive_at_all_sampled_QP'],
        'total_curved_CAD_volume_error_le_1e6':abs(q['CAD_volume_closure_rel_729'])<=1e-6,
        'supported_343_to_729_Veff_variation_le_1pct':q['max_relative_Veff_343_729_over_supported_regions']<=.01,
        'north_high_kappa_near_Neff_ge_30':q['north_high_kappa_near_Neff']>=30,
        'south_high_kappa_near_Neff_ge_30':q['south_high_kappa_near_Neff']>=30,
        'physical_surface_tags_2_to_9':new['physical_surface_tags']==list(range(2,10)),
    }
    a,b=regions(OLD),regions(NEW)
    ratios={}
    for key in ('r0_p0_N','r0_p0_S','near_p0_N','near_p0_S'):
        ratios[key]={
            'name':key,
            'M1_Neff':a[key]['Neff'],
            'M2_Neff':b[key]['Neff'],
            'M1_Veff_m3':a[key]['Veff'],
            'M2_Veff_m3':b[key]['Veff'],
            'M2_over_M1':b[key]['Veff']/a[key]['Veff'],
            'D029_target_0p50_to_0p75':.5<=b[key]['Veff']/a[key]['Veff']<=.75,
        }
    result={
        'protocol':'P10ID_INDEPENDENT_TET10_M2_QA_V1',
        'M1_SHA256':old['file_sha256'],
        'candidate_SHA256':new['file_sha256'],
        'approved_D030_numeric_quality_checks':checks,
        'GEOMETRY_QUALITY_GO':all(checks.values()),
        'M2_candidate_tet10':new['tet10_count'],
        'M1_tet10':old['tet10_count'],
        'candidate_pore_Tri6':new['pore_Tri6_count'],
        'M1_pore_Tri6':old['pore_Tri6_count'],
        'quality_M1':old['gmsh_curved_element_qualities'],
        'quality_candidate':vals,
        'local_fixed_region_volume_ratios':ratios,
        'ADAPTATION_TARGET_D029_NOT_DEMONSTRATED':not all(
            ratios[k]['D029_target_0p50_to_0p75'] for k in ('r0_p0_N','r0_p0_S')),
        'P10HA_kappa_is_provisional_not_full_goal_error':True,
        'independent_3D_physics_convergence_proven':False,
        'FEM_attempts':0,
    }
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
