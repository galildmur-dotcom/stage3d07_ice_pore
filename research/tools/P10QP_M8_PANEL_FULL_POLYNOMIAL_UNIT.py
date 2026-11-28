#!/usr/bin/env python3
"""Check the exact same composite Duffy panel implementation on full cubics.

The panel worker integrates cut=True by default. This independent unit wraps
the same RayChild.moment_on_ray with cut=False; all full P2-Tet10 moments are
analytically known. This does not validate polynomial root classification.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import P10PX_M8_CONSERVATIVE_TET10_TRIAGE as m8
from P10QL_M8_INDEPENDENT_RAY_CUT_QUADRATURE import RayChild
from P10QP_M8_HELDOUT_Q256_PANEL_COMPARISON import panel_integrate


class FullRayWrapper:
    def __init__(self,c):self.c=c
    def moment_on_ray(self,axis,s,t):return self.c.moment_on_ray(axis,s,t,cut=False)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--mesh',type=Path,required=True)
    p.add_argument('--child-report',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    sha=hashlib.sha256(a.mesh.read_bytes()).hexdigest()
    r=json.loads(a.child_report.read_text())
    if sha!=m8.PINNED_M8_SHA256 or r['mesh_sha256']!=sha or \
       r['source_cases']!=[5] or r['min_h_one']!=8 or \
       r['h_depth_limit']!=8 or r['physical_4D_FEM_approved']:
        raise ValueError('P10QP_FULL_POLYNOMIAL_UNIT_WRONG_GEOMETRY')
    tests=[]
    for idx in (26,20,31):
        c=RayChild(r['terminals'][idx]);wrap=FullRayWrapper(c)
        methods=[]
        for panels,n in ((2,64),(4,32)):
            v=panel_integrate(wrap,2,panels,n)
            err_g=abs(v['cut_gradient_m3']-c.exact_full_gradient)/max(abs(c.exact_full_gradient),1e-25)
            err_v=abs(v['cut_volume_m3']-c.exact_full_volume)/c.exact_full_volume
            if max(err_g,err_v)>1e-10:
                raise ValueError('P10QP_PANEL_JACOBIAN_OR_GAUSS_FULL_MOMENT_FAIL')
            methods.append({'panels':panels,'n_per_panel':n,
                            'full_gradient_relative_error':err_g,
                            'full_volume_relative_error':err_v})
        tests.append({'index':idx,'group':r['terminals'][idx]['group'],
                      'active_boundary_indices':c.active,'methods':methods})
    out={'stage':'P10QP','mesh_sha256':sha,
         'scope':'composite Duffy transverse panel exact smooth full polynomial unit, not cut roots',
         'cases':tests,'all_6_full_moments_pass_1e_minus_10':True,
         'physical_4D_FEM_approved':False,'no_Gmsh_no_CAD_no_FEM_no_mesh_change':True}
    a.output.write_text(json.dumps(out,indent=2)+'\n')
    print('P10QP_COMPOSITE_PANEL_FULL_CURVED_TET10_MOMENTS_PASS_NOT_CUT_CERTIFICATION')
    for v in tests:print(v)


if __name__=='__main__':main()
