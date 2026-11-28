#!/usr/bin/env python3
"""P10QJ: resource-capped, independent real M8 two-boundary Algoim test.

True quartic + quadratic + simplex, actual parent-FE piecewise gradient.
Each subprocess has a 20 s wall-clock cap and a 1.8 GiB address cap.
Source-only, no Gmsh/mesh edits/FEM/EDV/adjoint, no PowerShell.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import resource
import subprocess
import time

import numpy as np

import P10PX_M8_CONSERVATIVE_TET10_TRIAGE as m8
import P10QI_M8_REFERENCE_GRADIENT_POLYNOMIAL_PREFLIGHT as qi

LINE=re.compile(r'P10QJ_DOUBLE_CUT sample=(\d+) q=(\d+) '
                r'cut_gradient_m3=([0-9.eE+-]+) cut_volume_m3=([0-9.eE+-]+) '
                r'full_gradient_relative=([0-9.eE+-]+) full_volume_relative=([0-9.eE+-]+) '
                r'total_points=(\d+) active_points=(\d+) min_weight=([0-9.eE+-]+)$')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def direct_random_integral(case,rng,n=131072):
    """Independent true physical six-constraint classification of qmc nodes."""
    X=np.array(case['physical_child_nodes_10'],dtype=float)
    field=np.array(case['restricted_parent_FE_P2_nodal_values'],dtype=float)
    grid=np.array([[i/3,j/3,k/3] for i in range(4)
                   for j in range(4-i) for k in range(4-i-j)])
    vals=np.array([qi.mapped_and_numerator(X,field,u)[1] for u in grid])
    coeff=np.linalg.solve(qi.mono_matrix(grid),vals)
    r=case['radial_bin'];m=case['mu_bin'];ip=case['phi_bin']
    radial_lo=m8.PORE_R+m8.RADIAL_LOWER_MM[r]/1000.
    radial_hi=m8.PORE_R+m8.RADIAL_LOWER_MM[r+1]/1000.
    angle=-math.pi+2*math.pi*ip/12

    def take(bary,importance_weight=None):
        u=bary[:,1:]
        pos=qi.shape_at(u)@X-m8.CENTER
        rr=np.einsum('ij,ij->i',pos,pos)
        signs=np.column_stack((rr>=radial_lo**2,rr<=radial_hi**2,
             pos[:,2]>=0 if m==9 else pos[:,2]<=0,
             .36*pos[:,2]**2-.64*(pos[:,0]**2+pos[:,1]**2)>=0,
             -math.sin(angle)*pos[:,0]+math.cos(angle)*pos[:,1]>=0,
             -math.sin(angle+math.pi/6)*pos[:,0]+math.cos(angle+math.pi/6)*pos[:,1]<=0))
        bound_indices=[case['quartic_constraint'],case['quadratic_constraint']]
        active=signs[:,bound_indices].all(axis=1)
        if not np.array_equal(active,signs.all(axis=1)):
            raise ValueError('P10QJ_INACTIVE_BOUNDARY_ACTUALLY_INTERSECTS_REAL_CHILD')
        nume=qi.mono_matrix(u)@coeff
        weighted=nume*active/6.
        if importance_weight is not None:
            weighted=weighted*importance_weight
        return weighted,int(np.count_nonzero(active))

    bary=rng.dirichlet(np.ones(4),size=n)
    v,inside=take(bary)
    method='iid_uniform_reference_tetra'
    count=n
    if inside<25:
        # Rare-event backup: emphasize a vertex with both cut conditions
        # inside, using the exact proposal-to-uniform Dirichlet density ratio.
        phase=np.array(case['lattice_sign_phase_counts'])
        if phase[-1]<2:
            raise ValueError('P10QJ_NO_REAL_TWO_BOUNDARY_POSITIVE_PHASE')
        # Symmetric corner enrichment keeps all four physical phases alive.
        alpha=np.full(4,.5)
        bary=rng.dirichlet(alpha,size=262144)
        logratio=(math.lgamma(4)-math.lgamma(float(alpha.sum()))+
                  sum(math.lgamma(float(a)) for a in alpha)-
                  np.sum((alpha[None,:]-1)*np.log(bary),axis=1))
        v,inside=take(bary,np.exp(logratio))
        method='importance_symmetric_dirichlet_half'
        count=len(bary)
    err=float(np.std(v,ddof=1)/math.sqrt(len(v)))
    return {'sampling_method':method,'points':count,'inside_points':inside,
            'estimate_cut_gradient_m3':float(np.mean(v)),
            'estimated_standard_error_m3':err}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('mesh','selection','worker-input','source','prior-qi-source',
                 'algoim-root','lapacke-include','lapacke-lib',
                 'lapack-lib','blas-lib','binary','output','log'):
        p.add_argument('--'+name,required=True,type=Path)
    p.add_argument('--qmax',type=int,default=8)
    p.add_argument('--wall-timeout-s',type=int,default=20)
    p.add_argument('--memory-bytes',type=int,default=1800000000)
    args=p.parse_args()
    start=time.monotonic()
    selected=json.loads(args.selection.read_text())
    if (sha(args.mesh)!=m8.PINNED_M8_SHA256 or
        selected['mesh_sha256']!=m8.PINNED_M8_SHA256 or
        sha(args.worker_input)!=selected['worker_input_sha256'] or
        len(selected['cases'])!=8 or args.wall_timeout_s>40 or args.memory_bytes>2500000000):
        raise ValueError('P10QJ_M8_INVALID_PIN_SELECTION_OR_EXECUTION_LIMIT')
    build=['g++','-std=c++20','-O2','-Wl,--gc-sections',
           '-I'+str((args.algoim_root/'algoim').resolve()),
           '-I'+str(args.lapacke_include.resolve()),str(args.source.resolve()),
           str(args.lapacke_lib.resolve()),str(args.lapack_lib.resolve()),
           str(args.blas_lib.resolve()),'-lm','-o',str(args.binary.resolve())]
    built=subprocess.run(build,capture_output=True,text=True,timeout=120)
    if built.returncode:
        raise RuntimeError('P10QJ_COMPILATION_FAILED '+built.stderr[-1000:])
    def limit_memory():
        resource.setrlimit(resource.RLIMIT_AS,(args.memory_bytes,args.memory_bytes))
    cases=[];logs=[];rng=np.random.default_rng(20261128)
    for k,case in enumerate(selected['cases']):
        begin=time.monotonic()
        try:
            run=subprocess.run([str(args.binary.resolve()),str(args.worker_input.resolve()),
                                str(k),str(args.qmax)],capture_output=True,text=True,
                               timeout=args.wall_timeout_s,preexec_fn=limit_memory)
        except subprocess.TimeoutExpired as exc:
            logs.append(f'=== CASE {k} TIMEOUT {args.wall_timeout_s} s ===\n'+
                        str(exc.stdout or '')+str(exc.stderr or ''))
            args.log.write_text('\n'.join(logs)+'\n')
            raise RuntimeError(f'P10QJ_FAIL_CLOSED_TIMEOUT_CASE_{k}') from exc
        logs.append(f'=== CASE {k} TRUE M8 TWO SURFACE ===\n'+run.stdout+run.stderr)
        if run.returncode or 'P10QJ_TRUE_REAL_M8_TWO_BOUNDARY_ALGOIM_PASS' not in run.stdout:
            args.log.write_text('\n'.join(logs)+'\n')
            raise RuntimeError(f'P10QJ_FAIL_CLOSED_ALGOIM_CASE_{k}: '+(run.stdout+run.stderr)[-1200:])
        q_records=[]
        for line in run.stdout.splitlines():
            m=LINE.fullmatch(line)
            if m:
                index,q,grad,vol,gfull,vfull,points,active,weight=m.groups()
                q_records.append({'q':int(q),'cut_gradient_m3':float(grad),
                    'cut_volume_m3':float(vol),'full_gradient_relative':float(gfull),
                    'full_volume_relative':float(vfull),'total_points':int(points),
                    'active_points':int(active),'min_weight':float(weight)})
                if int(index)!=k:
                    raise ValueError('P10QJ_CASE_LABEL_MISMATCH')
        if [x['q'] for x in q_records]!=[2,3,4,6,8][:len(q_records)] or not q_records:
            raise ValueError('P10QJ_PARTIAL_Q_SERIES')
        for r in q_records:
            if r['total_points']>2000000 or r['active_points']<=0 or r['min_weight']<=0:
                raise ValueError('P10QJ_ALGOIM_POINT_OR_WEIGHT_GUARD')
        independent=direct_random_integral(case,rng)
        latest=q_records[-1]['cut_gradient_m3']
        z=abs(latest-independent['estimate_cut_gradient_m3'])/max(independent['estimated_standard_error_m3'],1e-30)
        if independent['inside_points']>=30 and z>8:
            raise ValueError(f'P10QJ_DOUBLE_CUT_QMC_REJECTS_ALGOIM_CASE_{k} z={z}')
        cases.append({'sample_index':k,'element_id':case['original_element_id'],
            'radial_bin':case['radial_bin'],'mu_bin':case['mu_bin'],'phi_bin':case['phi_bin'],
            'quartic_constraint':case['quartic_constraint'],
            'quadratic_constraint':case['quadratic_constraint'],
            'depth':case['depth'],'q_records':q_records,
            'q8_exact_full_moment_test_pass_1e_minus_10':
                (q_records[-1]['full_gradient_relative']<=1e-10 and
                 q_records[-1]['full_volume_relative']<=1e-10),
            'independent_physical_six_condition_sampling':independent,
            'QMC_difference_in_standard_errors':z,'elapsed_s':time.monotonic()-begin})
        print(f'P10QJ_ALGOIM_REAL_TWO_CUT_CASE_{k+1}/8 qmax={q_records[-1]["q"]} '
              f'points={q_records[-1]["total_points"]} '
              f'full_moment_error={q_records[-1]["full_gradient_relative"]:.3g} '
              f'physical_volume={q_records[-1]["cut_volume_m3"]:.10g} '
              f'qmc_z={z:.3g}',flush=True)
    args.log.write_text('\n'.join(logs)+'\n')
    def deltas(a,b):
        later=np.array([next(rec['cut_gradient_m3'] for rec in case['q_records'] if rec['q']==b)
                        for case in cases])
        earlier=np.array([next(rec['cut_gradient_m3'] for rec in case['q_records'] if rec['q']==a)
                          for case in cases])
        d=later-earlier
        return {'q_pair':[a,b],
                'L1_abs_relative':float(np.sum(abs(d))/np.sum(abs(later))),
                'signed_abs_relative':float(abs(np.sum(d))/np.sum(abs(later))),
                'positive_deltas':int(np.sum(d>0)),'negative_deltas':int(np.sum(d<0))}
    levels=[2,3,4,6,8][:len(cases[0]['q_records'])]
    qchanges=[deltas(a,b) for a,b in zip(levels[:-1],levels[1:])]
    passed=sum(c['q8_exact_full_moment_test_pass_1e_minus_10'] for c in cases)
    status=('PASS_REAL_M8_TWO_ACTIVE_GRADIENT_AND_FULL_MOMENT_STABILITY' if passed==len(cases)
            else 'FAIL_Q8_FULL_TET10_MOMENT_CONVERGENCE_ON_REAL_TWO_BOUNDARY_CELLS')
    out={'stage':'P10QJ','status':status,
         'mesh_sha256':m8.PINNED_M8_SHA256,'mesh_changed':False,
         'Gmsh_run':False,'physical_FEM_run':False,
         'genuine_original_Algoim_and_LAPACKE':True,'q_levels':levels,
         'per_case_wall_s':args.wall_timeout_s,'per_case_address_bytes':args.memory_bytes,
         'per_case_max_nodes':2000000,'case_count':len(cases),
         'q8_full_Tet10_exact_moment_threshold_relative':1e-10,
         'q8_full_Tet10_exact_moment_passed_cases':passed,
         'q8_full_Tet10_exact_moment_failed_cases':len(cases)-passed,
         'max_q8_full_gradient_relative':max(c['q_records'][-1]['full_gradient_relative'] for c in cases),
         'max_q8_full_volume_relative':max(c['q_records'][-1]['full_volume_relative'] for c in cases),
         'CXX_source_sha256':sha(args.source),
         'pinned_P10QI_dependency_sha256':sha(args.prior_qi_source),
         'total_last_q_nodes':sum(c['q_records'][-1]['total_points'] for c in cases),
         'q_convergence_signed_and_L1':qchanges,'cases':cases,
         'elapsed_s':time.monotonic()-start,
         'absolute_cut_integration_error_certified':False,
         'all_48_bins_integrated':False,'physical_4D_FEM_approved':False}
    args.output.write_text(json.dumps(out,indent=2)+'\n')
    print('P10QJ_REAL_TWO_ACTIVE_ALGOIM_INDEPENDENT_QA_PASS',flush=True)


if __name__=='__main__':
    main()
