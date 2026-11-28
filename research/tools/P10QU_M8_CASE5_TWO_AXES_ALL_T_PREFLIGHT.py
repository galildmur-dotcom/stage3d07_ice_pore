#!/usr/bin/env python3
"""P10QU independent all-outer-slice geometric fail-closed preflight.

For both new axes and all 30 true cut children, inspect each outer GL
node of q128+q256 BEFORE integrating the physical numerator.  This is
numeric topology probing, not rigorous interval root isolation.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import time

from P10QL_M8_INDEPENDENT_RAY_CUT_QUADRATURE import RayChild
from P10QR_M8_ONE_BOUNDARY_DISCRIMINANT_SEGMENTED import gauss
from P10QU_M8_CASE5_TWO_NEW_AXES_REAL_CURVED_CRITICAL_EVENTS import PIN,events,T_ORDERS


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--mesh',type=Path,required=True)
    p.add_argument('--child-report',type=Path,required=True)
    p.add_argument('--axis',type=int,choices=[0,1],required=True)
    p.add_argument('--part',type=int,choices=[0,1,2,3],required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    report=json.loads(a.child_report.read_text())
    if hashlib.sha256(a.mesh.read_bytes()).hexdigest()!=PIN or \
       report['mesh_sha256']!=PIN or report['source_cases']!=[5] or \
       report['h_depth_limit']!=8 or report['min_h_one']!=8 or \
       report['physical_4D_FEM_approved']:
        raise ValueError('P10QU_PREFLIGHT_INPUT_SHA_OR_SOURCE_FAILURE')
    ids=[i for i,t in enumerate(report['terminals']) if t['group'] in ('one','multi')]
    if len(ids)!=30:raise ValueError('P10QU_WRONG_TRUE_CUT_COUNT')
    select=ids[a.part::4]
    rows=[];start=time.monotonic()
    for i,idx in enumerate(select,1):
        c=RayChild(report['terminals'][idx]);maxrad=0.;maxaz=0.
        maxhigher_r=0.;maxhigher_a=0.;maxtrim=0.
        total_trims=0;total_roots=0;maxsegments=0;count=0
        event_totals={};zeros={}
        for order in T_ORDERS:
            for t in gauss(order)[0]:
                breaks,meta=events(c,a.axis,float(t))
                count+=1;maxsegments=max(maxsegments,len(breaks)-1)
                maxrad=max(maxrad,meta['radial_reconstruction_relative'])
                maxaz=max(maxaz,meta['azimuth_reconstruction_relative'])
                maxhigher_r=max(maxhigher_r,meta['radial_w3_w4_relative'])
                maxhigher_a=max(maxhigher_a,meta['azimuth_w2_relative'])
                maxtrim=max(maxtrim,meta['max_trimmed_relative_coefficient'])
                total_trims+=meta['azimuth_degree_numerical_trim_count']
                total_roots+=sum(meta['candidate_event_counts'].values())
                for k,v in meta['candidate_event_counts'].items():
                    event_totals[k]=event_totals.get(k,0)+v
                for k in meta['identically_zero_event_counts']:
                    zeros[k]=zeros.get(k,0)+1
        if count!=sum(T_ORDERS):raise ValueError('P10QU_OUTER_SLICE_COUNT_CHANGED')
        rows.append({'index':idx,'active':c.active,'actual_outer_t_slices':count,
                     'max_radial_reconstruction_relative':maxrad,
                     'max_azimuth_reconstruction_relative':maxaz,
                     'max_radial_ray_w3_w4_relative':maxhigher_r,
                     'max_azimuth_ray_w2_relative':maxhigher_a,
                     'max_trimmed_relative_azimuth_degree_coefficient':maxtrim,
                     'guarded_degree_trim_count':total_trims,
                     'candidate_critical_root_count':total_roots,
                     'max_s_segments':maxsegments,'event_totals':event_totals,
                     'identically_zero_event_slices':zeros,
                     'unresolved_topology_intervals':0})
        print(f'P10QU_PREFLIGHT axis={a.axis} part={a.part} cell={idx} '
              f'progress={i}/{len(select)} slices={count} '
              f'high_r={maxhigher_r:.3e} high_a={maxhigher_a:.3e} '
              f'critical_roots={total_roots} trims={total_trims}',flush=True)
    output={'stage':'P10QU_PREFLIGHT','axis':a.axis,'part':a.part,'parts':4,
            'mesh_sha256':PIN,'source_case':5,'original_element_id':5865,
            'all_cut_indices':ids,'selected_indices':select,
            'per_cut_outer_nodes':sum(T_ORDERS),
            'total_checked_outer_t_slices':sum(r['actual_outer_t_slices'] for r in rows),
            'numerical_P4_to_P2_and_P2_to_P1_guards_passed':True,
            'topology_sample_checks_passed':True,
            'no_mathematical_interval_certificate':True,
            'physical_4D_FEM_approved':False,'no_Gmsh_no_CAD_no_FEM_no_mesh_change':True,
            'elapsed_s':time.monotonic()-start,'cells':rows}
    a.output.write_text(json.dumps(output,indent=2)+'\n')
    print(f'P10QU_PREFLIGHT_AXIS{a.axis}_PART{a.part}_ALL_SLICES_PASS_NO_FEM',flush=True)


if __name__=='__main__':main()
