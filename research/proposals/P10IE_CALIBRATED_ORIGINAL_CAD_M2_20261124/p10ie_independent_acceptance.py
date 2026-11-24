#!/usr/bin/env python3
"""P10IE read-only comparison against pinned M1 and original P10ID control."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path

import p10ic_tet10_quality_audit as audit
import p10hv_independent_scan as scan

HERE=Path(__file__).resolve().parent
SRC={
    'M1':('P10GT_HXT10.msh','47460969be26c2bd0a15e0b1425806fa350aa09aa2b4ac9f80605b433fc65ca7'),
    'P10ID':('P10ID_M2_3D_UNVERIFIED.msh','8acba5a9b3185429c200989015a7dfffb2b19452170db9d508da3e59ea0102f5'),
    'P10IE':('P10IE_M2_PATCH_CALIBRATED_3D_UNVERIFIED.msh','d1ec65ffcc6e8fac7da925ecd66bbb9508450cf2ea837521442f57f45674c78b'),
}

def qregions(path):
    xyz,tet,_=scan.read_msh(path.read_bytes())
    v27=scan.evaluate(xyz,tet,3,None)
    return {
        '343':scan.groups(scan.evaluate(xyz,tet,7,v27['volume'])),
        '729':scan.groups(scan.evaluate(xyz,tet,9,v27['volume'])),
    }

def main():
    stats={};q={}
    for name,(filename,sha) in SRC.items():
        p=HERE/filename
        if hashlib.sha256(p.read_bytes()).hexdigest()!=sha:
            raise RuntimeError('SHA mismatch '+name)
        stats[name]=audit.audit(p)
        q[name]=qregions(p)
    v=stats['P10IE']['gmsh_curved_element_qualities']
    a=stats['P10IE']['independent_curved_Tet10_quadrature']
    checks={
        'minSICN_ge_0p20':v['minSICN']['min']>=.20,
        'minSJ_ge_0p40':v['minSJ']['min']>=.40,
        'gamma_ge_0p15':v['gamma']['min']>=.15,
        'Gmsh_minDetJac_positive':v['minDetJac']['min']>0,
        'independent_27_343_729_positive':a['positive_at_all_sampled_QP'],
        'CAD_volume_closure_le_1e6':abs(a['CAD_volume_closure_rel_729'])<=1e-6,
        '343_to_729_supported_Veff_variation_le_1pct':a['max_relative_Veff_343_729_over_supported_regions']<=.01,
        'near_polar_north_Neff_ge_30':a['north_high_kappa_near_Neff']>=30,
        'near_polar_south_Neff_ge_30':a['south_high_kappa_near_Neff']>=30,
        'physical_surface_tags_2_to_9':stats['P10IE']['physical_surface_tags']==list(range(2,10)),
    }
    physical={}
    for key in ('near_p0_N','near_p0_S','r0_p0_N','r0_p0_S'):
        physical[key]={}
        for order in ('343','729'):
            old=q['M1'][order][key]
            cur=q['P10IE'][order][key]
            control=q['P10ID'][order][key]
            ratio=cur['Veff']/old['Veff']
            physical[key][order]={
                'M1_Neff':old['Neff'],'P10ID_Neff':control['Neff'],
                'P10IE_Neff':cur['Neff'],
                'P10ID_over_M1':control['Veff']/old['Veff'],
                'P10IE_over_M1':ratio,
                'P10IE_reduction_percent':100*(1-ratio),
                'D029_target_region_0p50_to_0p75':.5<=ratio<=.75,
            }
    combined=[physical[k]['729'] for k in ('near_p0_N','near_p0_S')]
    result={
        'protocol':'P10IE_R1_INDEPENDENT_3D_TET10_729QP_QA',
        'source_sha256':{k:v[1] for k,v in SRC.items()},
        'all_D031_quality_checks':checks,
        'GEOMETRY_QUALITY_GO':all(checks.values()),
        'fixed_physical_region_ratios':physical,
        'D029_ADAPTATION_TARGET_IN_AGGREGATED_SUPPORT_REGIONS':all(
            x['D029_target_region_0p50_to_0p75'] and x['P10IE_Neff']>=30
            for x in combined),
        'high_kappa_ge_0p8_mask_still_low_support_in_M1':True,
        'PHYSICS_CONVERGENCE_PROVEN':False,
        'FEM_attempts':0,
    }
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
