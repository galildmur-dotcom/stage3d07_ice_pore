#!/usr/bin/env python3
"""P10QS: real curved M8 P4 radial + linear azimuth joint-event resultant.

Source-only numerical feasibility preflight on the seven two-active h8 cells.
For fixed t, G(s,w)=b(s)w+c(s) on this axis; the polynomial resultant is
Res_w(F4,G1)=sum_k F_k(s)*(-c(s))^k*b(s)^(4-k).
Candidates are masked by the ACTUAL two physical constraints and w in [0,1].
Ordinary floating-point interpolation/roots are NOT interval certified.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np

import P10PX_M8_CONSERVATIVE_TET10_TRIAGE as m8
import P10QI_M8_REFERENCE_GRADIENT_POLYNOMIAL_PREFLIGHT as qi
from P10QL_M8_INDEPENDENT_RAY_CUT_QUADRATURE import RayChild

PIN='40949482ac74d80ae7ac44c88af527a705650d34c1ffcd0de7cd01dc2bd2fa8d'
TEST_T=(.1,.3,.5,.7,.9)
AXIS=2
TWO=(13,14,20,21,31,37,38)
P=np.polynomial.polynomial


def physical_ray(c:RayChild,s,t):
    others=[i for i in (0,1,2) if i!=AXIS]
    wmax=(1-s)*(1-t)
    refs=np.zeros((3,3));refs[:,others[0]]=s;refs[:,others[1]]=(1-s)*t
    refs[:,AXIS]=[0.,.5*wmax,wmax]
    phys=c.physical_poly(qi.shape_at(refs)@c.nodes)
    radial=np.pad(np.asarray(c.constraint(phys,0),dtype=float),(0,5))[:5]
    az=np.pad(np.asarray(c.constraint(phys,4),dtype=float),(0,3))[:3]
    return radial,az


def reconstruct(c:RayChild,t:float):
    # Chebyshev-Lobatto nodes for degree-4 transverse interpolation.
    nodes=np.array([0.,.1464466094067262,.5,.8535533905932737,1.])
    radial=np.stack([physical_ray(c,float(s),t)[0] for s in nodes],axis=0)
    f=np.stack([P.polyfit(nodes,radial[:,k],4) for k in range(5)])
    aznodes=np.array([0.,.5,1.])
    azdata=np.stack([physical_ray(c,float(s),t)[1] for s in aznodes],axis=0)
    g=np.stack([P.polyfit(aznodes,azdata[:,k],2) for k in range(3)])
    sf=max(float(np.max(abs(f))),1e-30)
    sg=max(float(np.max(abs(g))),1e-30)
    errf=0.;errg=0.
    for s in (.08,.26,.41,.67,.91):
        realf,realg=physical_ray(c,s,t)
        fitf=np.array([P.polyval(s,x) for x in f])
        fitg=np.array([P.polyval(s,x) for x in g])
        errf=max(errf,float(np.max(abs(realf-fitf)))/sf)
        errg=max(errg,float(np.max(abs(realg-fitg)))/sg)
    if max(errf,errg)>1e-9:
        raise ValueError('P10QS_P4_P2_TRUE_CURVED_INTERPOLATION_FAIL')
    # Expected azimuth: exactly linear in ray w for this selected axis.
    if np.max(abs(g[2]))/sg>1e-9:
        raise ValueError('P10QS_AZIMUTH_NOT_LINEAR_RAY_REQUIRES_GENERAL_RESULTANT')
    return f/sf,g/sg,errf,errg


def mulpow(a,n):
    p=np.array([1.])
    for _ in range(n):p=P.polymul(p,a)
    return p


def resultant(f,g):
    b=g[1];c=g[0]
    res=np.array([0.])
    for k in range(5):
        term=P.polymul(f[k],P.polymul(mulpow(-c,k),mulpow(b,4-k)))
        res=P.polyadd(res,term)
    return res


def real_roots_unit(poly):
    z=np.asarray(poly,dtype=float)
    scale=float(max(abs(z)))
    if scale<1e-14:return [],True
    while len(z)>1 and abs(z[-1])<2e-9*scale:z=z[:-1]
    roots=P.polyroots(z/scale) if len(z)>1 else []
    out=[]
    for r in roots:
        if abs(r.imag)<1e-5 and 1e-8<r.real<1-1e-8:
            v=float(r.real)
            residual=abs(P.polyval(v,z))/scale
            if residual<2e-4:out.append((v,residual))
    return out,False


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--mesh',type=Path,required=True)
    p.add_argument('--child-report',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    sha=hashlib.sha256(a.mesh.read_bytes()).hexdigest()
    report=json.loads(a.child_report.read_text())
    if sha!=PIN or sha!=m8.PINNED_M8_SHA256 or report['mesh_sha256']!=sha or \
       report['source_cases']!=[5] or report['h_depth_limit']!=8 or \
       report['min_h_one']!=8 or report['physical_4D_FEM_approved']:
        raise ValueError('P10QS_TWO_BOUNDARY_WRONG_M8_SOURCE')
    real=tuple(i for i,t in enumerate(report['terminals']) if t['group']=='multi')
    if real!=TWO:raise ValueError('P10QS_TWO_BOUNDARY_SET_CHANGED')
    out=[]
    for idx in TWO:
        c=RayChild(report['terminals'][idx])
        if c.active!=[0,4]:raise ValueError('P10QS_WRONG_ACTIVATED_CONSTRAINTS')
        rows=[]
        for t in TEST_T:
            f,g,ef,eg=reconstruct(c,t)
            res=resultant(f,g)
            candidates,degenerate=real_roots_unit(res)
            masked=[]
            for s,rr in candidates:
                b=P.polyval(s,g[1]);cc=P.polyval(s,g[0])
                if abs(b)<1e-9:continue
                w=-cc/b
                rad,az=physical_ray(c,s,t)
                r0=float(P.polyval(w,rad))
                r1=float(P.polyval(w,az))
                if 0<w<1 and abs(r0)<5e-4 and abs(r1)<5e-5:
                    masked.append({'s':s,'w':w,'radial_residual':r0,
                                   'azimuth_residual':r1,'resultant_relative_residual':rr})
            rows.append({'t':t,'P4_transverse_interpolation_relative':ef,
                         'P2_transverse_interpolation_relative':eg,
                         'resultant_degree_before_trimming':len(res)-1,
                         'resultant_nearly_identically_zero':degenerate,
                         'raw_real_candidate_count':len(candidates),
                         'physical_masked_crossing_count':len(masked),
                         'masked_candidates':masked})
        out.append({'index':idx,'active_constraints':c.active,'fixed_t_slices':rows})
        print('P10QS_RESULTANT_CELL',idx,'physical_crossings',sum(r['physical_masked_crossing_count'] for r in rows),
              'raw_candidates',sum(r['raw_real_candidate_count'] for r in rows),flush=True)
    result={'stage':'P10QS','scope':'numerical source-only real curved two-active P4/P2 resultant feasibility preflight',
            'mesh_sha256':PIN,'axis':AXIS,'source_case':5,
            'all_seven_two_boundary_indices':list(TWO),'fixed_outer_t_test_slices':list(TEST_T),
            'resultant_formula':'Res_w(F4,b*w+c)=sum[k=0..4] F_k*(-c)^k*b^(4-k)',
            'not_all_resultant_roots_are_physically_relevant':True,
            'no_high_order_cut_quadrature_on_two_boundary_cells':True,
            'ordinary_double_roots_and_masks_not_interval_certified':True,
            'physical_4D_FEM_approved':False,'no_Gmsh_no_CAD_no_FEM_no_mesh_change':True,
            'cells':out}
    a.output.write_text(json.dumps(result,indent=2)+'\n')
    print('P10QS_TRUE_CURVED_MULTI_P4_P2_RESULTANT_PREFLIGHT_COMPLETE_NOT_CERTIFIED',flush=True)


if __name__=='__main__':main()
