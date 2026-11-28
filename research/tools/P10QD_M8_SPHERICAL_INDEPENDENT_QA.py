#!/usr/bin/env python3
"""Independent P10QD source-only audit, including SciPy-root cross-location.

P10QA geometric Bernstein brackets are *certified enclosures*. The P10QD
spherical point-sampled q-results are not: this QA explicitly preserves that
distinction and does not authorize physics.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np
from scipy.optimize import root

import P10PX_M8_CONSERVATIVE_TET10_TRIAGE as mesh
import P10QD_M8_SPHERICAL_TET10_POINT_LOCATION as qd


def independent_search(X,lo,hi,point):
    """Unaccelerated FULL-M8 Bezier AABB and independent SciPy HYBR inversion."""
    mask=((point-mesh.CENTER>=lo-2e-14)&(point-mesh.CENTER<=hi+2e-14)).all(axis=1)
    for k in np.flatnonzero(mask):
        a=np.column_stack((X[k,1]-X[k,0],X[k,2]-X[k,0],X[k,3]-X[k,0]))
        start=np.linalg.solve(a,point-X[k,0])
        def fn(v):
            n,g=mesh.tet10_shape(v)
            return n@X[k]-point
        result=root(fn,start,method='hybr',options={'xtol':1e-11,'maxfev':80})
        v=result.x
        n,_=mesh.tet10_shape(v)
        bary=np.r_[1-v.sum(),v]
        if (np.linalg.norm(n@X[k]-point)<3e-11
                and bary.min()>-1e-9 and bary.max()<1+1e-9):
            return int(k),v
    return None,None


def run_independent_points(locator,X):
    ctrl=X.copy()
    for k,(a,b) in enumerate(mesh.EDGE,start=4):
        ctrl[:,k]=2*X[:,k]-.5*(X[:,a]+X[:,b])
    lo=ctrl.min(axis=1)-mesh.CENTER
    hi=ctrl.max(axis=1)-mesh.CENTER
    rng=np.random.default_rng(20261128)
    idx=np.flatnonzero(((lo>-.0015)&(hi<.0015)).all(axis=1))
    if len(idx)<64:
        raise ValueError('not enough wholly-indexed Tet10 for inverse test')
    records=[]
    max_dist=0.
    for k in rng.choice(idx,size=64,replace=False):
        bary=rng.dirichlet([2.,2.,2.,2.]);uv=bary[1:]
        n,_=mesh.tet10_shape(uv)
        point=n@X[k]
        fast,v1=locator.locate(point)
        slow,v2=independent_search(X,lo,hi,point)
        if fast is None or slow is None:
            raise ValueError('Independent search misses known curved M8 interior')
        n1,_=mesh.tet10_shape(v1)
        n2,_=mesh.tet10_shape(v2)
        max_dist=max(max_dist,float(np.linalg.norm(n1@X[fast]-n2@X[slow])))
        if np.linalg.norm(n1@X[fast]-n2@X[slow])>3e-11:
            raise ValueError('Accelerated and independent curved inversions disagree')
        records.append((int(fast),int(slow)))
    # Inside pore far from curved wall: every such point must be excluded.
    negatives=0
    for k in range(36):
        mu=-.99+1.98*(k+.5)/36
        phi=2*math.pi*((k*19)%37)/37
        point=mesh.CENTER+.00075*np.array([
            math.sqrt(1-mu*mu)*math.cos(phi),
            math.sqrt(1-mu*mu)*math.sin(phi),mu])
        fast,_=locator.locate(point)
        slow,_=independent_search(X,lo,hi,point)
        if fast is not None or slow is not None:
            raise ValueError('Pore interior false-positive point location')
        negatives+=1
    # Second independent check: actual 4 pole bins, points of a q4 tensor rule.
    sphere_tested=0
    for ir in [0,4]:
        for im in [0,9]:
            pts,_,_,_,_=qd.sphere_points(ir,im,7,4)
            for point in pts[::8]:
                fast,_=locator.locate(point)
                slow,_=independent_search(X,lo,hi,point)
                if fast is None or slow is None:
                    raise ValueError('Independent curved M8 locate fails on exact sector')
                sphere_tested+=1
    return {'independent_solver':'scipy.optimize.root(HYBR), full-mesh Bezier broad phase',
            'random_true_curved_Tet10_point_tests':len(records),
            'pore_interior_negative_controls':negatives,
            'spherical_quadrature_points_cross_checked':sphere_tested,
            'max_fast_slow_reprojection_difference_m':max_dist}


def sample_actual_curved_pore_wall(path):
    """Sample actual physical-group-8 Tri6, not the analytic sphere.

    This gives empirical extrema only, NOT a certified continuous envelope.
    """
    nodes={};faces=[]
    with path.open(encoding='utf-8') as src:
        for raw in src:
            section=raw.strip()
            if section=='$Nodes':
                for _ in range(int(next(src))):
                    x=next(src).split()
                    nodes[int(x[0])]=np.array(list(map(float,x[1:])))
            elif section=='$Elements':
                for _ in range(int(next(src))):
                    x=list(map(int,next(src).split()))
                    if x[1]==9 and x[3]==8:
                        faces.append([nodes[k] for k in x[3+x[2]:]])
    if len(faces)!=648:
        raise ValueError('Unexpected curved physical pore wall Tri6 count')
    faces=np.array(faces)
    if faces.shape[1:]!=(6,3):
        raise ValueError('Unexpected Gmsh Tri6 boundary geometry')
    min_r=math.inf;max_r=-math.inf;samples=0;sampled_outside=0
    for i in range(21):
        for j in range(21-i):
            b=np.array([1-(i+j)/20.,i/20.,j/20.])
            shp=np.r_[b*(2*b-1),4*b[0]*b[1],4*b[1]*b[2],4*b[2]*b[0]]
            point=np.einsum('k,fkj->fj',shp,faces)
            rr=np.linalg.norm(point-mesh.CENTER,axis=1)
            min_r=min(min_r,float(rr.min()))
            max_r=max(max_r,float(rr.max()))
            samples+=len(rr)
            sampled_outside+=int((rr>mesh.PORE_R+1e-12).sum())
    return {'method':'physical-group-8 real Tri6 quadratic face interpolation, barycentric grid step 1/20',
            'curved_Tri6_faces':len(faces),'total_sample_points':samples,
            'minimum_pore_wall_radius_m':min_r,'maximum_pore_wall_radius_m':max_r,
            'max_inward_deviation_from_ideal_sphere_um':(mesh.PORE_R-min_r)*1e6,
            'sample_count_outside_ideal_sphere_by_more_than_1pm':sampled_outside,
            'limitation':'This mesh face sample DOES NOT prove wall radial containment at unsampled points.'}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--mesh',type=Path,required=True)
    p.add_argument('--spherical',type=Path,required=True)
    p.add_argument('--baseline',type=Path,required=True)
    p.add_argument('--high-q',type=Path,default=None,
                   help='optional independent four-bin q12/16/20/24 extension')
    p.add_argument('--output',type=Path,default=Path('P10QD_M8_SPHERICAL_INDEPENDENT_QA.json'))
    args=p.parse_args()
    sha=hashlib.sha256(args.mesh.read_bytes()).hexdigest()
    if sha!=mesh.PINNED_M8_SHA256:
        raise ValueError('M8 pinned SHA mismatch')
    report=json.loads(args.spherical.read_text())
    baseline=json.loads(args.baseline.read_text())
    if any(v['mesh_sha256']!=sha for v in (report,baseline)):
        raise ValueError('Incompatible prior volume enclosures')
    if len(report['bins'])!=48 or baseline['bin_count']!=48:
        raise ValueError('All 48 pole sectors required')
    baseline_by={(x['radial_bin'],x['mu_bin'],x['phi_bin']):x for x in baseline['bins']}
    record_by={(x['radial_bin'],x['mu_bin'],x['phi_bin']):x for x in report['bins']}
    expected={(r,m,p) for r in [0,4] for m in [0,9] for p in range(12)}
    if expected!=set(record_by):
        raise ValueError('Missing or duplicated 4D sectors')
    qset=set(report['bins'][0]['q_records'][k]['q'] for k in range(len(report['bins'][0]['q_records'])))
    if not {2,4,8,12,16}.issubset(qset):
        raise ValueError('Insufficient q-level sequence for convergence audit')
    node_count=0;max_linear_err=0.;max_volume_err=0.;max_bracket_width_rel=0.
    for key,b in record_by.items():
        ir,im,ip=key
        p0=mesh.PORE_R+mesh.RADIAL_LOWER_MM[ir]*.001
        p1=mesh.PORE_R+mesh.RADIAL_LOWER_MM[ir+1]*.001
        exact=(p1**3-p0**3)/3*(1./5)*(math.pi/6)
        prior=baseline_by[key]['depth_records'][-1]
        lo,hi=prior['lower_cut_volume_m3'],prior['upper_cut_volume_m3']
        max_bracket_width_rel=max(max_bracket_width_rel,(hi-lo)/exact)
        if not (lo<=exact<=hi):
            raise ValueError('Ideal analytic volume contradicts accepted M8 geometric brackets')
        for row in b['q_records']:
            if row['nodes']!=row['q']**3 or row['located']+row['not_located']!=row['nodes']:
                raise ValueError('Quadrature node accounting inconsistent')
            if row['not_located']!=0:
                raise ValueError('Not all tested ideal spherical sector nodes are in curved M8')
            if not row['between_P10QA_certified_brackets']:
                raise ValueError('Q result outside certified physical cut brackets')
            node_count+=row['nodes']
            max_volume_err=max(max_volume_err,abs(row['curved_M8_cut_volume_m3']-exact)/exact)
            max_linear_err=max(max_linear_err,row['FE_nodal_linear_vs_exact_rel'])
    if max_volume_err>1e-12 or max_linear_err>1e-12:
        raise ValueError('Constant or linear manufactured spherical integral failed')
    def changes(qlo,qhi):
        d=[];v=[]
        for b in report['bins']:
            q={x['q']:x for x in b['q_records']}
            v.append(q[qhi]['FE_nodal_cubic_moment_m3'])
            d.append(q[qhi]['FE_nodal_cubic_moment_m3']-q[qlo]['FE_nodal_cubic_moment_m3'])
        v=np.array(v);d=np.array(d)
        denom=np.abs(v).sum()
        return {'q_pair':[qlo,qhi],
                'signed_delta_m3':float(d.sum()),
                'sum_absolute_bin_deltas_m3':float(np.abs(d).sum()),
                'signed_delta_relative_to_L1_moment':float(abs(d.sum())/denom),
                'L1_delta_relative_to_L1_moment':float(np.abs(d).sum()/denom),
                'max_per_bin_delta_relative_to_abs_qhigh':float(np.max(np.abs(d)/np.abs(v))),
                'positive_bin_changes':int((d>0).sum()),
                'negative_bin_changes':int((d<0).sum()),
                'mixed_sign_cancellation_factor':float(np.abs(d).sum()/abs(d.sum())) if abs(d.sum())>1e-30 else None}
    convergences=[changes(2,4),changes(4,8),changes(8,12),changes(12,16)]
    highq=None
    if args.high_q is not None:
        high=json.loads(args.high_q.read_text())
        if high['mesh_sha256']!=sha or len(high['bins'])!=4:
            raise ValueError('Unexpected high-q four-bin input')
        pairs=[]
        for b in high['bins']:
            key=(b['radial_bin'],b['mu_bin'],b['phi_bin'])
            if key not in record_by:
                raise ValueError('High-q bin not part of 48-bin baseline')
            q={e['q']:e for e in b['q_records']}
            if set(q)!={12,16,20,24}:
                raise ValueError('High-q sequence incomplete')
            v16=next(r['FE_nodal_cubic_moment_m3']
                     for r in record_by[key]['q_records'] if r['q']==16)
            if abs(v16-q[16]['FE_nodal_cubic_moment_m3'])>3e-13*max(abs(v16),1e-30):
                raise ValueError('Two independent q16 evaluations disagree')
            for z in q.values():
                if z['nodes']!=z['q']**3 or z['not_located']!=0:
                    raise ValueError('High-q point inclusion not complete')
            pairs.append(q)
        deltas=[]
        for a,b in [(12,16),(16,20),(20,24)]:
            d=np.array([r[b]['FE_nodal_cubic_moment_m3']-
                        r[a]['FE_nodal_cubic_moment_m3'] for r in pairs])
            val=np.array([r[b]['FE_nodal_cubic_moment_m3'] for r in pairs])
            deltas.append({'q_pair':[a,b],
                           'L1_relative_to_four_bin_moment':float(np.abs(d).sum()/np.abs(val).sum()),
                           'signed_relative_to_four_bin_moment':float(abs(d.sum())/np.abs(val).sum()),
                           'max_bin_relative_change':float(np.max(np.abs(d)/np.abs(val)))})
        highq={'bins':len(pairs),'q_levels':[12,16,20,24],
               'spherical_quadrature_nodes':sum(q**3 for q in [12,16,20,24])*4,
               'q16_cross_replay_pass':True,'q_changes':deltas}
    xyz,conn,*_=mesh.parse_msh(args.mesh)
    X=xyz[conn]
    locator=qd.CurvedTet10Locator(X)
    independent=run_independent_points(locator,X)
    wall=sample_actual_curved_pore_wall(args.mesh)
    out={'stage':'P10QD','status':'PASS_48_BIN_SPHERICAL_POINT_LOCATION_AND_MANUFACTURED_MOMENTS_NOT_PHYSICS',
         'mesh_sha256':sha,'read_only':True,'fem_started':False,'gmsh_generated':False,
         'independent_point_location':independent,'bin_count':48,
         'sampled_curved_pore_wall':wall,
         'tested_q':sorted(qset),'sphere_quadrature_total_points':node_count,
         'max_ideal_volume_relative_error':max_volume_err,
         'max_FE_linear_moment_relative_error':max_linear_err,
         'max_prior_certified_bracket_width_relative_to_ideal':max_bracket_width_rel,
         'FE_interpolated_cubic_moment_q_changes':convergences,
         'high_q_four_bin_pilot':highq,
         'important_limit':'FE interpolated cubic q16 is only a q-reference, not a certified exact integral; all spheres tested numerically, inclusion not proven between points.',
         'physical_4D_FEM_approved':False}
    args.output.write_text(json.dumps(out,indent=2)+'\n')
    print(out['status'])
    for c in convergences:
        print(f'Q{c["q_pair"][0]}_Q{c["q_pair"][1]} '
              f'L1REL={c["L1_delta_relative_to_L1_moment"]:.8g} '
              f'SIGNEDREL={c["signed_delta_relative_to_L1_moment"]:.8g} '
              f'MAXBIN={c["max_per_bin_delta_relative_to_abs_qhigh"]:.8g}',flush=True)


if __name__=='__main__':
    main()
