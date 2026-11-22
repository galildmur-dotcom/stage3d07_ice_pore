#!/usr/bin/env python3
"""P10FG: compute P10FB M2 fixed-3D polar Veff against published P10ER M1 baseline."""
import argparse
import csv
import json
from pathlib import Path

from p10ed_verify_original_m1_m2_raw_spatial import parse_msh2, rule27
from p10er_three_raw_msh_local_topology_forensics import (
    mesh_diagnostics, zones, assert_partition_closure,
)

M2_SHA = 'ff6500e2da4f4697e1788669e2404d33cdeb9435c1230cf14f5cc7619f1f6a44'
P10ER_BASELINE = Path(__file__).resolve().parents[1] / (
    'research/evidence/P10ER_THREE_RAW_MESHES_20261122/derived/'
    'P10ER_FIXED_POLAR_SUBREGION_7_9QP.csv')


def compute(msh: Path):
    mesh = parse_msh2(msh, M2_SHA)
    N, D, W = rule27()
    defs = zones()
    audit, sample, _, _ = mesh_diagnostics(mesh, 'P10FB_M2', N, D, W, defs)
    assert_partition_closure({'P10FB_M2':sample},defs)
    with P10ER_BASELINE.open(newline='',encoding='utf-8') as f:
        baseline={(row['region'],int(row['order'])):row for row in csv.DictReader(f)}
    out=[]
    for order in (7,9):
        for v in sample[order]:
            key=(v['region'],order)
            old=float(baseline[key]['M1_v_eff_m3'])
            ratio=v['effective_cell_volume_m3']/old
            out.append({'region':v['region'],'order':order,
                        'm1_v_eff_m3':old,
                        'm2_v_eff_m3':v['effective_cell_volume_m3'],
                        'm2_over_m1':ratio,
                        'm2_region_vol_m3':v['region_volume_m3'],
                        'm2_fractional_tets':v['fractional_tet_count'],
                        'm2_qp_hits':v['qp_hits']})
    selected={r['region']:r for r in out if r['order']==9 and
              r['region'] in ('north_polar_0_100um','south_polar_0_100um',
                              'north_off_0_100um','south_off_0_100um')}
    status='GO' if all(.75<=selected[z]['m2_over_m1']<=.85 for z in
                       ('north_polar_0_100um','south_polar_0_100um')) else 'STOP'
    return {'mesh':'P10FB_M2','m2_sha256':M2_SHA,
            'm1_baseline':'P10ER_FIXED_POLAR_SUBREGION_7_9QP.csv',
            'm1_raw_recomputed_here':False,
            'm2_tet10':len(mesh['tet10']),
            'm2_curved_geometry':audit['original_geometry'],
            'm2_adjacent_cell_smoothness':audit['face_smoothness_diagnostics'],
            'selected_729qp':selected,'polar_D025_diagnostic':status,
            'rows':out}


def main():
    a=argparse.ArgumentParser()
    a.add_argument('--m2',type=Path,required=True)
    a.add_argument('--out',type=Path,required=True)
    opt=a.parse_args()
    result=compute(opt.m2)
    opt.out.write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print('P10FG_POLAR_D025_DIAGNOSTIC',result['polar_D025_diagnostic'])
    for z in ('north_polar_0_100um','south_polar_0_100um'):
        print(z,result['selected_729qp'][z]['m2_over_m1'])


if __name__=='__main__':
    main()
