#!/usr/bin/env python3
"""P10QT preflight: every actual 128/256 Gauss t slice of 8 remaining cuts.

Checks polynomial-degree reduction, true P4/P2 interpolation and topology
probes before launching full cut quadrature. No physical FEM.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from P10QL_M8_INDEPENDENT_RAY_CUT_QUADRATURE import RayChild
from P10QT_M8_RADIAL_AND_TWO_BOUNDARY_CRITICAL_INTEGRATOR import (
    PIN,ALL,projected_events,gauss)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--mesh',type=Path,required=True)
    p.add_argument('--child-report',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    sha=hashlib.sha256(a.mesh.read_bytes()).hexdigest()
    child=json.loads(a.child_report.read_text())
    if sha!=PIN or child['mesh_sha256']!=PIN or child['source_cases']!=[5] or \
       child['min_h_one']!=8 or child['h_depth_limit']!=8 or child['physical_4D_FEM_approved']:
        raise ValueError('P10QT_FULL_SLICE_PREFLIGHT_WRONG_M8_SOURCE')
    rows=[];numdenoise=0;maxdrop=0.;unresolved=0;maxseg=0;maxhigher=0.
    for idx in ALL:
        c=RayChild(child['terminals'][idx]);per=[]
        for n in (128,256):
            count=0;denoise=0;max_discarded=0.;maxinterp_rad=0.;maxinterp_az=0.;wrong=0;maxinterval=0;highray=0.
            for t in gauss(n)[0]:
                breaks,m=projected_events(c,float(t))
                count+=1;denoise+=m['numerical_azimuth_degree_denoising_applied']
                max_discarded=max(max_discarded,m['max_dropped_relative_azimuth_degree_coefficient'])
                maxinterp_rad=max(maxinterp_rad,m['interpolation_error_radial_P4'])
                maxinterp_az=max(maxinterp_az,m['interpolation_error_azimuth_P2'])
                highray=max(highray,m['max_higher_w_coeff_radial'])
                wrong+=m['unresolved_probe_intervals']
                maxinterval=max(maxinterval,len(breaks)-1)
            if count!=n or maxinterval>16 or wrong>0:
                raise ValueError('P10QT_PREFLIGHT_UNRESOLVED_OR_OVER_BUDGET')
            per.append({'order':n,'outer_slices_tested':count,
                        'guarded_azimuth_degree_denoising_slices':denoise,
                        'max_dropped_azimuth_coefficient_relative':max_discarded,
                        'max_radial_P4_fit_relative':maxinterp_rad,
                        'max_azimuth_P2_fit_relative':maxinterp_az,
                        'max_high_order_radial_w_coefficient_relative':highray,
                        'max_s_intervals':maxinterval,'unresolved_topology_probes':wrong})
            numdenoise+=denoise;maxdrop=max(maxdrop,max_discarded)
            unresolved+=wrong;maxseg=max(maxseg,maxinterval)
            maxhigher=max(maxhigher,highray)
        rows.append({'index':idx,'active':c.active,'orders':per})
        print('P10QT_PREFLIGHT_CELL',idx,'t_slices',384,'denoised',sum(x['guarded_azimuth_degree_denoising_slices'] for x in per),flush=True)
    out={'stage':'P10QT','mesh_sha256':PIN,'source_case':5,
         'all_remaining_eight_cut_indices':list(ALL),
         'total_outer_t_slices_tested':len(ALL)*(128+256),
         'guarded_small_degree_coefficient_removals':numdenoise,
         'max_relative_removed_coefficient':maxdrop,
         'max_high_order_radial_w_coefficient_relative':maxhigher,
         'max_s_smooth_intervals':maxseg,
         'unresolved_topology_probe_intervals':unresolved,
         'double_precision_root_enclosure_not_certified':True,
         'no_high_order_cut_quadrature_in_this_preflight':True,
         'physical_4D_FEM_approved':False,'no_Gmsh_no_CAD_no_FEM_no_mesh_change':True,
         'cells':rows}
    a.output.write_text(json.dumps(out,indent=2)+'\n')
    print('P10QT_ALL_REAL_P2_P1_T_SLICES_PREFLIGHT_PASS_NO_FEM')


if __name__=='__main__':main()
