#!/usr/bin/env python3
"""P10QM: independent h8/h10/h12 multi-boundary volume and Bernstein QA.

The M8 curved P2 geometry and manufactured P2 FE field remain unchanged.
This is a floating-coefficient conservative pilot, NOT directed rounding.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

import P10PX_M8_CONSERVATIVE_TET10_TRIAGE as m8

FILES={8:Path('P10QK_M8_HYBRID_CHILDREN_CASE4_H8_ONE8_QA.json'),
       10:Path('P10QM_M8_HYBRID_CHILDREN_CASE4_H10_ONE8_QA.json'),
       12:Path('P10QM_M8_HYBRID_CHILDREN_CASE4_H12_ONE8_QA.json')}


def audit(rep,h):
    if rep['stage']!='P10QK' or rep['mesh_sha256']!=m8.PINNED_M8_SHA256 or \
       rep['min_h_one']!=8 or rep['h_depth_limit']!=h or rep['source_cases']!=[4] or \
       rep['mesh_changed'] or rep['physical_4D_FEM_approved']:
        raise ValueError('P10QM_H_DEPTH_M8_PIN_OR_SCOPE_INVALID')
    case=rep['cases'][0];ts=rep['terminals'];count=case['group_counts']
    if case['original_element_id']!=6008 or len(ts)!=sum(count.get(k,0) for k in ('inside','one','multi')):
        raise ValueError('P10QM_TERMINAL_PARTITION_INCOMPLETE')
    for t in ts:
        active=sum(v==0 for v in t['status'])
        group='inside' if active==0 else ('one' if active==1 else 'multi')
        if group!=t['group'] or any(v not in (0,1) for v in t['status']) or active>2 or \
           t['h_depth']>h or (group=='multi' and t['h_depth']!=h) or \
           (group=='one' and t['h_depth']<8):
            raise ValueError('P10QM_BAD_CONSERVATIVE_BOUNDARY_CLASS')
    bounds=case['residual_multi_gradient_enclosure_m3']
    multi=[t for t in ts if t['group']=='multi']
    if not math.isclose(bounds[0],sum(t['unknown_cut_gradient_lower_m3'] for t in multi),
                        rel_tol=2e-12,abs_tol=1e-25) or \
       not math.isclose(bounds[1],sum(t['unknown_cut_gradient_upper_m3'] for t in multi),
                        rel_tol=2e-12,abs_tol=1e-25):
        raise ValueError('P10QM_BERNSTEIN_BOUNDS_SUM_INCONSISTENT')
    root=case['root_volume_m3']
    outside=case['group_physical_volume_fraction']['outside']*root
    partition=sum(t['exact_full_volume_m3'] for t in ts)+outside
    if abs(partition-root)/root>3e-10 or case['full_mass_partition_closure']>3e-10:
        raise ValueError('P10QM_PHYSICAL_CURVED_VOLUME_MASS_NOT_CONSERVED')
    return {'h_max':h,'count':count,'physical_volume_fractions':case['group_physical_volume_fraction'],
            'physical_curved_volume_closure':abs(partition-root)/root,
            'multi_boundary_gradient_bernstein_bounds_m3':bounds,
            'total_open_cut_count':len(multi)+count['one']}


def main():
    mesh=Path('P10PO_M21_NARROW_POLES_HIGHORDERELASTIC_ALL_QA_20261128/M8.msh')
    if hashlib.sha256(mesh.read_bytes()).hexdigest()!=m8.PINNED_M8_SHA256:
        raise ValueError('P10QM_M8_MESH_CHANGED')
    reports=[audit(json.loads(FILES[h].read_text()),h) for h in (8,10,12)]
    bounds=[r['multi_boundary_gradient_bernstein_bounds_m3'][1] for r in reports]
    vol=[r['physical_volume_fractions']['multi'] for r in reports]
    if not(bounds[0]>bounds[1]>bounds[2]>0 and vol[0]>vol[1]>vol[2]>0):
        raise ValueError('P10QM_H_GEOMETRIC_UNCERTAINTY_NOT_MONOTONE')
    result={'stage':'P10QM','date_utc':'2026-11-28',
            'mesh_sha256':m8.PINNED_M8_SHA256,
            'scope':'one genuine M8 source case4, original element6008, h8 h10 h12',
            'status':'POSITIVE_MONOTONE_GEOMETRIC_REFINEMENT_WITH_NONRIGOROUS_FLOAT_BERNSTEIN_BOUNDS',
            'levels':reports,
            'h8_to_h12_multi_volume_fraction_reduction_factor':vol[0]/vol[2],
            'h8_to_h12_multi_gradient_bound_reduction_factor':bounds[0]/bounds[2],
            'Bernstein_bounds_are_not_directed_rounded':True,
            'physical_FEM_approved':False,'mesh_or_Gmsh_or_CAD_or_FEM_executed':False}
    Path('P10QM_M8_H8_H10_H12_BERNSTEIN_BUDGET_QA.json').write_text(json.dumps(result,indent=2)+'\n')
    print('P10QM_INDEPENDENT_H8_H10_H12_GEOMETRIC_BUDGET_PASS_PHYSICS_FAIL_CLOSED',flush=True)


if __name__=='__main__':main()
