#!/usr/bin/env python3
"""Independently re-evaluate P4/P2 joint crossings in Cartesian physical XYZ."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np

import P10QI_M8_REFERENCE_GRADIENT_POLYNOMIAL_PREFLIGHT as qi
from P10QL_M8_INDEPENDENT_RAY_CUT_QUADRATURE import (
    CENTRE,MM,RADIAL)
from P10QS_M8_TWO_BOUNDARY_RESULTANT_PREFLIGHT import PIN,TWO,TEST_T


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--mesh',type=Path,required=True)
    p.add_argument('--child-report',type=Path,required=True)
    p.add_argument('--resultant-report',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    sha=hashlib.sha256(a.mesh.read_bytes()).hexdigest()
    src=json.loads(a.child_report.read_text())
    report=json.loads(a.resultant_report.read_text())
    if sha!=PIN or src['mesh_sha256']!=PIN or report['mesh_sha256']!=PIN or \
       report['stage']!='P10QS' or report['axis']!=2 or \
       report['all_seven_two_boundary_indices']!=list(TWO) or \
       report['fixed_outer_t_test_slices']!=list(TEST_T) or \
       report['physical_4D_FEM_approved'] or len(report['cells'])!=7:
        raise ValueError('P10QS_CROSS_AUDIT_RESULTANT_SOURCE_WRONG')
    actual=[];raw_total=0;masked_total=0;max_rad=0.;max_az=0.
    for expected,c in zip(TWO,report['cells']):
        idx=c['index'];term=src['terminals'][idx]
        if idx!=expected or term['group']!='multi' or \
           [i for i,v in enumerate(term['status']) if v==0]!=[0,4] or \
           len(c['fixed_t_slices'])!=len(TEST_T):
            raise ValueError('P10QS_CROSS_AUDIT_WRONG_PHYSICAL_MULTI_CELL')
        xyz=np.asarray(term['nodes'],dtype=float)
        rbin,phibin=term['radial_bin'],term['phi_bin']
        angle=-math.pi+math.pi*phibin/6
        for t,row in zip(TEST_T,c['fixed_t_slices']):
            if row['t']!=t or row['P4_transverse_interpolation_relative']>1e-9 or \
               row['P2_transverse_interpolation_relative']>1e-9:
                raise ValueError('P10QS_CROSS_AUDIT_BAD_POLYNOMIAL_INTERPOLATION')
            raw_total+=row['raw_real_candidate_count']
            masked_total+=row['physical_masked_crossing_count']
            if len(row['masked_candidates'])!=row['physical_masked_crossing_count']:
                raise ValueError('P10QS_CROSS_AUDIT_MASK_COUNT_WRONG')
            for z in row['masked_candidates']:
                s,w=z['s'],z['w']
                if not 0<s<1 or not 0<w<1:
                    raise ValueError('P10QS_CROSS_AUDIT_JOINT_EVENT_OUTSIDE_DOMAIN')
                u=np.array([[s,(1-s)*t,(1-s)*(1-t)*w]])
                coords=(qi.shape_at(u)@xyz)[0]
                X,Y,Z=(coords-CENTRE)*MM
                radial=(1+RADIAL[rbin])**2-(X*X+Y*Y+Z*Z)
                az=math.sin(angle)*X-math.cos(angle)*Y
                max_rad=max(max_rad,abs(radial));max_az=max(max_az,abs(az))
                if abs(radial)>1e-6 or abs(az)>1e-7 or \
                   abs(radial-z['radial_residual'])>1e-8 or \
                   abs(az-z['azimuth_residual'])>1e-9:
                    raise ValueError('P10QS_CROSS_AUDIT_CANDIDATE_NOT_ACTUAL_PHYSICAL_INTERSECTION')
                actual.append({'index':idx,'t':t,'s':s,'w':w,
                               'independent_physical_radial_residual':float(radial),
                               'independent_physical_azimuth_residual':float(az)})
    out={'stage':'P10QS','scope':'physical XYZ independent mask reevaluation, NOT all crossings certified',
         'mesh_sha256':PIN,'source_child_sha256':hashlib.sha256(a.child_report.read_bytes()).hexdigest(),
         'source_resultant_sha256':hashlib.sha256(a.resultant_report.read_bytes()).hexdigest(),
         'seven_real_two_active_cells':list(TWO),'fixed_t_samples':list(TEST_T),
         'algebraic_real_candidate_count':raw_total,
         'physical_verified_crossing_count':masked_total,
         'max_independent_radial_residual':max_rad,
         'max_independent_azimuth_residual':max_az,
         'physical_verified_candidates':actual,
         'cannot_claim_all_resultant_roots_or_continuous_t_sweep':True,
         'physical_4D_FEM_approved':False,'no_Gmsh_no_CAD_no_FEM_no_mesh_change':True}
    if masked_total!=len(actual) or raw_total<masked_total:
        raise ValueError('P10QS_CROSS_AUDIT_INCONSISTENT_COUNTS')
    a.output.write_text(json.dumps(out,indent=2)+'\n')
    print('P10QS_REAL_TWO_BOUNDARY_RESULTANT_INDEPENDENT_PHYSICAL_MASK_QA_PASS',
          'candidates',raw_total,'verified',masked_total,
          'max_rad',f'{max_rad:.3e}','max_az',f'{max_az:.3e}')
    print('P10QS_RESULTANT_NOT_A_CERTIFIED_QUADRATURE_NO_FEM')


if __name__=='__main__':main()
