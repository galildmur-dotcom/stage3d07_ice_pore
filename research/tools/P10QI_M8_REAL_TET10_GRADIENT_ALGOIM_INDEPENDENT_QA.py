#!/usr/bin/env python3
"""P10QI independent audit of true M8 Tet10 polynomial-gradient cut quadrature.

Build original Algoim with genuine LAPACKE and run eight pinned one-quartic
M8 curved children. Compare q2/3/4/6/8 with full-child exact degree-3
moments, preceding P10QB cut volumes and *independent* randomized direct
physical membership using exact polynomial numerator. QMC is sanity only,
not an error certificate. No Gmsh, mesh edits, physical FEM or PowerShell.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess
import time

import numpy as np

import P10PX_M8_CONSERVATIVE_TET10_TRIAGE as m8
import P10QI_M8_REFERENCE_GRADIENT_POLYNOMIAL_PREFLIGHT as qi


PATTERN=re.compile(
    r'P10QI_REAL_GRADIENT case=(\d+) q=(\d+) '
    r'cut_gradient_m3=([0-9.eE+-]+) full_gradient_m3=([0-9.eE+-]+) '
    r'exact_full_gradient_m3=([0-9.eE+-]+) full_gradient_rel=([0-9.eE+-]+) '
    r'cut_volume_m3=([0-9.eE+-]+) full_volume_rel=([0-9.eE+-]+) '
    r'points=(\d+) active=(\d+) min_weight=([0-9.eE+-]+)$'
)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def random_cut_integral(case,source,rng,num=131072):
    """Completely independent physical points and analytic cubic numerator."""
    nodes=np.array(source['physical_child_nodes_10'],dtype=float)
    coefficients=np.array(case['child_polynomial_monomial_coefficients'],dtype=float)
    radial=case['radial_bin'];polar=case['mu_bin'];az=case['phi_bin']
    rho_lo=m8.PORE_R+m8.RADIAL_LOWER_MM[radial]/1000
    rho_hi=m8.PORE_R+m8.RADIAL_LOWER_MM[radial+1]/1000
    angle=-math.pi+2*math.pi*az/12

    def process(bary,ratios=None):
        u=bary[:,1:]
        mapped=qi.shape_at(u)@nodes-m8.CENTER
        rr=np.sum(mapped*mapped,axis=1)
        bounds=np.column_stack((rr>=rho_lo**2,rr<=rho_hi**2,
             mapped[:,2]>=0 if polar==9 else mapped[:,2]<=0,
             .36*mapped[:,2]**2-.64*(mapped[:,0]**2+mapped[:,1]**2)>=0,
             -math.sin(angle)*mapped[:,0]+math.cos(angle)*mapped[:,1]>=0,
             -math.sin(angle+math.pi/6)*mapped[:,0]+math.cos(angle+math.pi/6)*mapped[:,1]<=0))
        if not np.array_equal(np.all(bounds,axis=1),bounds[:,case['active_quartic']]):
            raise ValueError('P10QI_INACTIVE_REAL_PHYSICAL_SECTOR_CONSTRAINT_VIOLATION')
        nume=qi.mono_matrix(u)@coefficients
        if ratios is not None:
            nume=nume*ratios
        vals=nume*bounds[:,case['active_quartic']]/6.
        return vals,int(np.count_nonzero(bounds[:,case['active_quartic']]))

    bary=rng.dirichlet(np.ones(4),size=num)
    vals,inside=process(bary)
    method='uniform_dirichlet'
    sample_count=num
    if inside<30:
        reference=source['true_boundary_vertex_and_center_values'][:4]
        preferred=int(np.argmax(reference))
        alpha=np.full(4,.3);alpha[preferred]=1.
        bary=rng.dirichlet(alpha,size=262144)
        log_ratio=(math.lgamma(4)-math.lgamma(float(np.sum(alpha)))+
                    sum(math.lgamma(float(a)) for a in alpha)-
                    np.sum((alpha[None,:]-1)*np.log(bary),axis=1))
        vals,inside=process(bary,np.exp(log_ratio))
        sample_count=len(bary)
        method='importance_dirichlet_at_vertex_'+str(preferred)
    stderr=float(np.std(vals,ddof=1)/math.sqrt(len(vals)))
    return {'method':method,'points':sample_count,'points_in_cut':inside,
            'manufactured_gradient_cut_estimate_m3':float(np.mean(vals)),
            'statistical_standard_error_m3':stderr}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('mesh','preflight','worker-input','prior-qb','selection','source',
                 'algoim-root','lapacke-include','lapacke-lib','lapack-lib','blas-lib',
                 'binary','output','log'):
        p.add_argument('--'+name,type=Path,required=True)
    args=p.parse_args()
    begin=time.monotonic()
    data=json.loads(args.preflight.read_text());old=json.loads(args.prior_qb.read_text())
    selection=json.loads(args.selection.read_text())
    if (sha(args.mesh)!=m8.PINNED_M8_SHA256 or data['mesh_sha256']!=m8.PINNED_M8_SHA256
        or old['mesh_sha256']!=m8.PINNED_M8_SHA256 or
        selection['mesh_sha256']!=m8.PINNED_M8_SHA256 or
        data['worker_input_sha256']!=sha(args.worker_input) or
        len(data['cases'])!=8 or len(old['cases'])!=8):
        raise ValueError('P10QI_INDEPENDENT_PIN_PREFLIGHT_OR_BASELINE_MISMATCH')
    build=['g++','-std=c++20','-O2','-Wl,--gc-sections',
           '-I'+str((args.algoim_root/'algoim').resolve()),
           '-I'+str(args.lapacke_include.resolve()),str(args.source.resolve()),
           str(args.lapacke_lib.resolve()),str(args.lapack_lib.resolve()),
           str(args.blas_lib.resolve()),'-lm','-o',str(args.binary.resolve())]
    compiled=subprocess.run(build,capture_output=True,text=True,timeout=120)
    if compiled.returncode:
        raise RuntimeError('P10QI_ACTUAL_CXX20_LAPACKE_BUILD_FAILED '+compiled.stderr[-1800:])
    logs=[];cases=[]
    rng=np.random.default_rng(20261128)
    for k,(case,baseline,sourcerec) in enumerate(zip(data['cases'],old['cases'],selection['cases'])):
        if (case['original_element_id']!=baseline['original_element_id'] or
            case['original_element_id']!=sourcerec['original_element_id']):
            raise ValueError('P10QI_CHILD_PROVENANCE_MISMATCH')
        started=time.monotonic()
        run=subprocess.run([str(args.binary.resolve()),str(args.worker_input.resolve()),
                            str(k),'8'],capture_output=True,text=True,timeout=45)
        logs.append('=== P10QI ACTUAL M8 CHILD '+str(k)+' ===\n'+run.stdout+run.stderr)
        if run.returncode or 'P10QI_REAL_TET10_GRADIENT_ALGOIM_PASS' not in run.stdout:
            raise RuntimeError('P10QI_ALGOIM_FAIL_CLOSED_CASE_'+str(k)+' '+(run.stdout+run.stderr)[-1000:])
        found=[]
        for line in run.stdout.splitlines():
            match=PATTERN.fullmatch(line)
            if match:
                j,q,cut,full,exact,eg,volume,ev,points,active,minimum=match.groups()
                found.append({'case':int(j),'q':int(q),'cut_gradient_m3':float(cut),
                              'full_gradient_m3':float(full),'exact_full_gradient_m3':float(exact),
                              'full_gradient_rel':float(eg),'cut_volume_m3':float(volume),
                              'full_volume_rel':float(ev),'points':int(points),
                              'active':int(active),'minimum_weight':float(minimum)})
        if [x['q'] for x in found]!=[2,3,4,6,8] or any(x['case']!=k for x in found):
            raise ValueError('P10QI_MISSING_Q_SERIES_OR_BAD_CASE')
        prior_q={r['q']:r for r in baseline['q_records']}
        for record in found:
            qq=record['q'];oldvol=prior_q[qq]['cut_m3']
            # Algoim's internal subdivision can be sensitive to the last
            # floating bits of an equivalent curved-Tet10 map. Reproducing
            # the physical cut *integral* is mandatory, but requiring the
            # exact same generated point count would be mathematically wrong.
            if (not record['minimum_weight']>0 or not record['points']>0 or
                not record['active']>0 or
                (qq>=3 and abs(record['cut_volume_m3']-oldvol)/
                 max(abs(oldvol),1e-30)>1e-9)):
                raise ValueError('P10QI_REAL_ALGOIM_VOLUME_BUDGET_PARITY_FAILED')
            if qq>=3 and (record['full_gradient_rel']>1e-10 or
                          record['full_volume_rel']>1e-10):
                raise ValueError('P10QI_CUBIC_FULL_TET10_MOMENT_NOT_EXACT')
        high=found[-1]['cut_gradient_m3'];low=found[-2]['cut_gradient_m3']
        randomized=random_cut_integral(case,sourcerec,rng)
        error=abs(randomized['manufactured_gradient_cut_estimate_m3']-high)
        z=error/max(randomized['statistical_standard_error_m3'],1e-30)
        if randomized['points_in_cut']>=30 and z>8:
            raise ValueError(f'P10QI_DIRECT_PHYSICAL_RANDOM_CUT_NOT_COMPATIBLE case={k} z={z}')
        result={'sample_index':k,'element_id':case['original_element_id'],
                'radial_bin':case['radial_bin'],'mu_bin':case['mu_bin'],
                'phi_bin':case['phi_bin'],'quartic':case['active_quartic'],
                'depth':case['depth'],'q_records':found,
                'q8_cut_gradient_m3':high,
                'q6_to_q8_absolute_relative_cut_gradient':abs(high-low)/max(abs(high),1e-30),
                'q3_to_q8_absolute_relative_cut_gradient':abs(high-found[1]['cut_gradient_m3'])/max(abs(high),1e-30),
                'q8_nodes_previous_volume_only_algoim':prior_q[8]['points'],
                'q8_nodes_relative_difference_vs_previous':
                    (found[-1]['points']-prior_q[8]['points'])/prior_q[8]['points'],
                'independent_direct_physical_random_cut':randomized,
                'difference_to_QMC_in_standard_errors':z,
                'elapsed_s':time.monotonic()-started}
        cases.append(result)
        print(f'P10QI_ALGOIM_GRADIENT_CASE_{k+1}/8 q3_q8_rel={result["q3_to_q8_absolute_relative_cut_gradient"]:.4g} '
              f'q6_q8_rel={result["q6_to_q8_absolute_relative_cut_gradient"]:.4g} '
              f'full_exact={found[-1]["full_gradient_rel"]:.3g} '
              f'qmc_sigma={z:.2f}',flush=True)
    args.log.write_text('\n'.join(logs)+'\n')
    def changes(a,b):
        deltas=np.array([next(x['cut_gradient_m3'] for x in c['q_records'] if x['q']==b)-
                         next(x['cut_gradient_m3'] for x in c['q_records'] if x['q']==a)
                         for c in cases])
        current=np.array([next(x['cut_gradient_m3'] for x in c['q_records'] if x['q']==b)
                          for c in cases])
        return {'q_pair':[a,b],
                'L1_abs_deltas_relative_to_L1_moment':float(np.sum(abs(deltas))/np.sum(abs(current))),
                'signed_abs_delta_relative_to_L1_moment':float(abs(np.sum(deltas))/np.sum(abs(current))),
                'positive_deltas':int(np.count_nonzero(deltas>0)),
                'negative_deltas':int(np.count_nonzero(deltas<0))}
    result={'stage':'P10QI','status':'PASS_TRUE_ALGOIM_LAPACKE_M8_PIECEWISE_TET10_GRADIENT_CUT_PILOTS',
            'mesh_sha256':m8.PINNED_M8_SHA256,'mesh_changed':False,
            'gmsh_generated':False,'physical_FEM_started':False,
            'original_algoim_root':str(args.algoim_root),'original_lapacke_library':str(args.lapacke_lib),
            'true_LAPACKE_symbols_used':['LAPACKE_dgesvd','LAPACKE_dggevx'],
            'cxx20_source_sha256':sha(args.source),
            'algoim_call':'ImplicitPolyQuadrature<3>::build + integrate(AutoMixed)',
            'case_count':len(cases),'q_levels':[2,3,4,6,8],
            'full_reference_Tet10_cubic_gradient_moment_is_exact':True,
            'cut_gradient_q8_is_exact':False,
            'QMC_is_exact':False,
            'all_cut_geometries_single_active_quartic_only':True,
            'global_48_bin_integration_approved':False,
            'q_delta_signed_and_L1':[
                changes(a,b) for a,b in ((2,3),(3,4),(4,6),(6,8),(3,8))],
            'max_q3_to_q8_cut_gradient_rel':max(x['q3_to_q8_absolute_relative_cut_gradient'] for x in cases),
            'max_q6_to_q8_cut_gradient_rel':max(x['q6_to_q8_absolute_relative_cut_gradient'] for x in cases),
            'total_q8_quadrature_points':sum(c['q_records'][-1]['points'] for c in cases),
            'elapsed_s':time.monotonic()-begin,'cases':cases,
            'absolute_cut_integration_error_certified':False,
            'physical_4D_FEM_approved':False}
    args.output.write_text(json.dumps(result,indent=2)+'\n')
    print('P10QI_TRUE_ALGOIM_LAPACKE_GRADIENT_INDEPENDENT_QA_PASS',flush=True)


if __name__=='__main__':
    main()
