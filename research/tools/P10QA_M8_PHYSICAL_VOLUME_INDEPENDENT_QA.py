#!/usr/bin/env python3
"""Independent Stage3D07 P10QA physical cut-volume and Jacobian audit.

Checks the 48-by-13 [lower,upper] physical-volume brackets and independently
integrates selected true curved Tet10 with Duffy tensor-Gauss q=2,3,4.
Also reproduces detJ at direct nodal quadrature locations, independently of
the degree-three polynomial Bernstein coefficient construction.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np

import P10PX_M8_CONSERVATIVE_TET10_TRIAGE as m8
import P10PY_M8_BEZIER_ADAPTIVE_PREFILTER as py
import P10QA_M8_PHYSICAL_CUT_VOLUME_BRACKETS as qa


def independent_duffy(X, tet, q):
    """Reference→parent→physical map, independent tensor-Gauss implementation."""
    abscissa, wg = np.polynomial.legendre.leggauss(q)
    abscissa = (abscissa+1.)/2.
    wg=wg/2.
    A=np.column_stack((tet[1]-tet[0],tet[2]-tet[0],tet[3]-tet[0]))
    value=0.
    for i,u in enumerate(abscissa):
        for j,v in enumerate(abscissa):
            for k,w in enumerate(abscissa):
                ref=np.array([u,(1-u)*v,(1-u)*(1-v)*w])
                ancestor=tet[0]+A@ref
                _,grad=m8.tet10_shape(ancestor)
                physical_jacobian=X.T@grad@A
                value+=wg[i]*wg[j]*wg[k]*(1-u)**2*(1-v)*np.linalg.det(physical_jacobian)
    return float(value)


def pointwise_jacobian_audit(X, coeff):
    rng=np.random.default_rng(20261128)
    max_relative=0.
    for _ in range(40):
        bary=rng.dirichlet(np.ones(4))
        uvw=bary[1:]
        _,grad=m8.tet10_shape(uvw)
        actual=np.linalg.det(X.T@grad)
        polynomial=0.
        for i,alpha in enumerate(qa.ALPHA3):
            term=math.factorial(3)
            for k,n in enumerate(alpha):
                term*=float(bary[k])**n / math.factorial(n)
            polynomial+=coeff[i]*term
        max_relative=max(max_relative,abs(actual-polynomial)/max(abs(actual),1e-17))
    return max_relative


def exact_jacobian_volume_audit(xyz,conn):
    sample_idx=[0,len(conn)//13,len(conn)//7,len(conn)//3,len(conn)//2,
                2*len(conn)//3,11*len(conn)//13,len(conn)-1]
    X=xyz[conn[sample_idx]]
    controls=qa.detj_bernstein_cubic_from_affine_jacobian(qa.jacobian_at_reference_vertices(X))
    max_pointwise=0.
    max_q3_q4=0.
    max_bern_q4=0.
    max_q2_q4=0.
    min_volume=math.inf
    tested=0
    for i,original in enumerate(X):
        max_pointwise=max(max_pointwise,pointwise_jacobian_audit(original,controls[i]))
        children=py.REF_TET[None].copy()
        for depth in range(4):
            for child in children:
                new=float(qa.physical_volume_of_subcells(controls[i],child[None],depth)[0])
                q2=independent_duffy(original,child,2)
                q3=independent_duffy(original,child,3)
                q4=independent_duffy(original,child,4)
                if min(new,q2,q3,q4)<=0:
                    raise ValueError("nonpositive integrated subcell volume")
                scale=max(abs(q4),1e-21)
                max_q3_q4=max(max_q3_q4,abs(q3-q4)/scale)
                max_bern_q4=max(max_bern_q4,abs(new-q4)/scale)
                max_q2_q4=max(max_q2_q4,abs(q2-q4)/scale)
                min_volume=min(min_volume,q4)
                tested+=1
            if depth<3:
                _, _, physical=py.subcell_envelopes(original,children)
                children=py.bisect_longest_curved_edge(children,physical)
    if max_pointwise>3e-12 or max_q3_q4>2e-12 or max_bern_q4>2e-12:
        raise ValueError("independent geometric determinant integration did not match")
    return {"selected_parent_Tet10":len(X),"selected_parent_and_children":tested,
            "max_pointwise_bernstein_vs_direct_detj_rel":float(max_pointwise),
            "max_degree3_rule_vs_duffy_q4_rel":float(max_bern_q4),
            "max_duffy_q3_vs_q4_rel":float(max_q3_q4),
            "max_duffy_q2_vs_q4_rel":float(max_q2_q4),
            "minimum_sampled_subcell_volume_m3":float(min_volume)}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mesh',type=Path,required=True)
    parser.add_argument('--baseline',type=Path,required=True)
    parser.add_argument('--candidate',type=Path,required=True)
    parser.add_argument('--output',type=Path,default=Path('P10QA_M8_PHYSICAL_VOLUME_SUMMARY_QA.json'))
    parser.add_argument('--csv',type=Path,default=Path('P10QA_M8_PHYSICAL_BRACKET_CONVERGENCE.csv'))
    args=parser.parse_args()
    digest=hashlib.sha256(args.mesh.read_bytes()).hexdigest()
    old=json.loads(args.baseline.read_text(encoding='utf-8'))
    new=json.loads(args.candidate.read_text(encoding='utf-8'))
    if digest!=m8.PINNED_M8_SHA256 or old['mesh_sha256']!=digest or new['mesh_sha256']!=digest:
        raise SystemExit('P10QA_INDEPENDENT_STOP_SHA_MISMATCH')
    if new['status']!='PASS_CURVED_M8_PHYSICAL_CUT_VOLUME_BRACKETS_SOURCE_ONLY':
        raise ValueError('unfinished physical cut-volume stage')
    if new['mesh_changed'] or new['fem_started'] or new['gmsh_generated']:
        raise ValueError('unexpected operation')
    if old['bin_count']!=48 or new['bin_count']!=48 or new['max_depth']!=12:
        raise ValueError('incomplete polar bin x depth audit')
    xyz,conn,ids,types,faces=m8.parse_msh(args.mesh)
    if len(conn)!=new['detj_certified_positive_tet10'] or len(conn)!=12546:
        raise ValueError('global cubic Jacobian sign proof incomplete')
    integration=exact_jacobian_volume_audit(xyz,conn)
    rows=[]
    final=[]
    for ob,nb in zip(old['bins'],new['bins']):
        key=tuple(ob[f] for f in ('radial_bin','mu_bin','phi_bin'))
        if key!=tuple(nb[f] for f in ('radial_bin','mu_bin','phi_bin')):
            raise ValueError('bin identities changed')
        if ob['original_possible_Tet10']!=nb['candidate_count']:
            raise ValueError('original candidates changed')
        root=nb['candidate_total_physical_m3']
        previous_lower=-1e-40
        previous_upper=root+1e-40
        for depth,(a,b) in enumerate(zip(ob['depth_records'],nb['depth_records'])):
            if a['depth']!=depth or b['depth']!=depth:
                raise ValueError('depth sequence changed')
            if a['uncertain_leaves']!=b['unresolved_leaves']:
                raise ValueError('P10PZ/P10QA geometry classifications differ')
            lower,upper=b['lower_cut_volume_m3'],b['upper_cut_volume_m3']
            width=upper-lower
            tol=1e-12*max(root,1e-22)
            if lower<-tol or upper>root+tol or lower>upper+tol:
                raise ValueError('invalid physical-volume bracket')
            if lower<previous_lower-tol or upper>previous_upper+tol:
                raise ValueError('physical-volume bracket is not nested by h')
            if abs(width-b['unresolved_physical_volume_upper_m3'])>tol:
                raise ValueError('physical interval width inconsistent')
            if abs(lower+b['certified_outside_m3']+width-root)>tol:
                raise ValueError('parent physical mass not conserved')
            rows.append((key[0],key[1],key[2],depth,root,lower,upper,width,
                         width/root,b['unresolved_leaves']))
            previous_lower,previous_upper=lower,upper
        if len(nb['depth_records'])!=13:
            raise ValueError('missing depth records')
        f=nb['depth_records'][-1]
        # Ideal CAD-sphere sector is an *external* analytic sanity benchmark.
        # It need not equal the curved Tet10 discrete domain exactly.
        r0=m8.PORE_R+m8.RADIAL_LOWER_MM[key[0]]/1000.
        r1=m8.PORE_R+m8.RADIAL_LOWER_MM[key[0]+1]/1000.
        ideal_sector=(r1**3-r0**3)/3. * .2 * (math.pi/6.)
        ideal_inside=f['lower_cut_volume_m3'] <= ideal_sector <= f['upper_cut_volume_m3']
        final.append({'radial_bin':key[0],'mu_bin':key[1],'phi_bin':key[2],
                      'candidate_total_m3':root,
                      'lower_cut_volume_m3':f['lower_cut_volume_m3'],
                      'upper_cut_volume_m3':f['upper_cut_volume_m3'],
                      'ideal_spherical_sector_volume_m3':ideal_sector,
                      'ideal_sector_inside_discrete_bracket':ideal_inside,
                      'midpoint_rel_difference_to_ideal_sector':
                         (f['midpoint_cut_volume_m3']-ideal_sector)/ideal_sector,
                      'relative_interval_width_to_candidates':f['width_relative_to_candidate_physical_volume'],
                      'relative_interval_width_to_midpoint':f['interval_width_m3']/max(f['midpoint_cut_volume_m3'],1e-30)})
    if len(rows)!=48*13:
        raise ValueError('not 48x13 recorded physical brackets')
    group_summary={}
    for ir,im in [(0,0),(0,9),(4,0),(4,9)]:
        items=[a for a in final if a['radial_bin']==ir and a['mu_bin']==im]
        lo=sum(a['lower_cut_volume_m3'] for a in items)
        hi=sum(a['upper_cut_volume_m3'] for a in items)
        candidates=sum(a['candidate_total_m3'] for a in items)
        group_summary[f'r{ir}_mu{im}']={
            'bin_count':len(items),'lower_sum_m3':lo,'upper_sum_m3':hi,
            'interval_width_sum_m3':hi-lo,'candidate_total_m3':candidates,
            'width_relative_to_candidates':(hi-lo)/candidates,
            'width_relative_to_cut_midpoint':(hi-lo)/max(.5*(hi+lo),1e-30),
            'midpoint_estimate_m3':.5*(hi+lo)}
    csv_header='radial_bin,mu_bin,phi_bin,depth,candidate_physical_m3,lower_m3,upper_m3,width_m3,width_fraction_candidates,unresolved_leaves'
    args.csv.write_text(csv_header+'\n'+'\n'.join(','.join(f'{v:.17g}' if isinstance(v,float) else str(v) for v in row)
                                   for row in rows)+'\n',encoding='utf-8')
    report={'stage':'P10QA', 'status':'PASS_INDEPENDENT_PHYSICAL_BRACKETS_48x13',
            'mesh_sha256':digest,'mesh_changed':False,'fem_started':False,
            'independent_curved_volume_tests':integration,
            'groups':group_summary,'bin_final_brackets':final,
            'ideal_spherical_sector_inside_discrete_brackets':sum(int(a['ideal_sector_inside_discrete_bracket']) for a in final),
            'analytic_geometry_warning':'Ideal sphere benchmark is not identically the curved Tet10 geometry.',
            'total_bin_depth_records':len(rows),
            'warning':'Physical cut-volume bound, not a cut-cell quadrature point estimate or physical 4D FEM derivative.'}
    args.output.write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print('P10QA_INDEPENDENT_PHYSICAL_VOLUME_QA_PASS',json.dumps(integration),flush=True)


if __name__=='__main__':
    main()
