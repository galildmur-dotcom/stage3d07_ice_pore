#!/usr/bin/env python3
"""True LAPACKE/Algoim pilot and independent M8 geometry + random cut QA.

Compiles a C++20 worker with the previously audited patched Algoim headers,
then runs real curved M8 child Tet10 with one active quartic plus simplex.
Independent checks: exact child restriction, degree-3 Jacobian volume,
physical bin membership at random uniform reference-tet points, q-series.
No mesh modification, Gmsh, FEM/thermal/EDV, PowerShell or adjoint.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import subprocess
import sys
from pathlib import Path

import numpy as np

import P10PX_M8_CONSERVATIVE_TET10_TRIAGE as m8
import P10PY_M8_BEZIER_ADAPTIVE_PREFILTER as py
import P10QA_M8_PHYSICAL_CUT_VOLUME_BRACKETS as vol


LINE=re.compile(
    r'P10QB_LOCAL_ALGOIM element=(\d+) depth=(\d+) quartic=(\d+) q=(\d+) '
    r'cut_m3=([0-9.eE+-]+) full_m3=([0-9.eE+-]+) exact_full_m3=([0-9.eE+-]+) '
    r'full_rel=([0-9.eE+-]+) cut_frac=([0-9.eE+-]+) points=(\d+) '
    r'active_points=(\d+) min_weight=([0-9.eE+-]+)$'
)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def qmc_sanity_case(case,X,vertex_jac,seed,num_samples=131072):
    """Independent physical integration; rare cone slivers use importance sampling."""
    rng=np.random.default_rng(seed)
    ref=np.array(case['reference_vertices'],dtype=np.float64)
    r0=m8.PORE_R+m8.RADIAL_LOWER_MM[case['radial_bin']]/1000.
    r1=m8.PORE_R+m8.RADIAL_LOWER_MM[case['radial_bin']+1]/1000.
    ph0=-math.pi+2*math.pi*case['phi_bin']/12
    ph1=ph0+math.pi/6
    inactive=[j for j in range(6) if j!=case['quartic_constraint']]
    def integrate_sample(bary):
        parent=bary@ref
        physical=py.map_tet10_nodally(X,parent[:,None,:])[:,0,:]-m8.CENTER
        rr=(physical**2).sum(axis=1)
        status=np.column_stack([
            rr>=r0*r0,rr<=r1*r1,
            physical[:,2]>=0 if case['mu_bin']==9 else physical[:,2]<=0,
            .36*physical[:,2]**2-.64*(physical[:,0]**2+physical[:,1]**2)>=0,
            -math.sin(ph0)*physical[:,0]+math.cos(ph0)*physical[:,1]>=0,
            -math.sin(ph1)*physical[:,0]+math.cos(ph1)*physical[:,1]<=0])
        violations=int((~status[:,inactive]).sum())
        if violations:
            raise ValueError(f'certified inactive constraints violated on random M8 coordinates: {violations}')
        signed=np.column_stack([1-parent.sum(axis=1),parent])
        jac=np.einsum('nv,vij->nij',signed,vertex_jac,optimize=True)
        det=np.linalg.det(jac)
        if np.any(det<=0):
            raise ValueError('sampled nonpositive true parent Jacobian')
        return status.all(axis=1), (2.**(-case['depth'])/6.)*det

    bary=rng.dirichlet(np.ones(4),size=num_samples)
    inside,weight=integrate_sample(bary)
    full_mean=float(weight.mean())
    full_stderr=float(weight.std(ddof=1)/math.sqrt(num_samples))
    partial=weight*inside
    sampling_method='uniform_dirichlet'
    if int(inside.sum()) < 30 and case['quartic_constraint']==3:
        # A polar-cone intersection can occupy ~10^-6 of a subcell: plain
        # Monte Carlo would almost surely miss it even at 2^17 points.
        # Bias samples towards the *known positive* reference vertex, then
        # apply exact Dirichlet density ratios, so the estimator remains
        # unbiased for the true uniform-tetra physical cut integral.
        positive=int(np.argmax(case['true_boundary_vertex_and_center_values'][:4]))
        alpha=np.full(4,.3,dtype=np.float64)
        alpha[positive]=1.
        bary_imp=rng.dirichlet(alpha,size=262144)
        inside_imp,weight_imp=integrate_sample(bary_imp)
        log_ratio=(math.lgamma(4)-math.lgamma(float(alpha.sum()))
                   +sum(math.lgamma(float(a)) for a in alpha)
                   -np.sum((alpha[None,:]-1)*np.log(bary_imp),axis=1))
        weighted=weight_imp*inside_imp*np.exp(log_ratio)
        partial=weighted
        sampling_method='importance_dirichlet_vertex_'+str(positive)
        inside=inside_imp
    return {'points':num_samples,'cut_sampling_points':len(inside),
            'sampling_method':sampling_method,
            'inside_sample_count':int(inside.sum()),
            'inactive_boundary_violations':0,
            'independent_random_cut_m3':float(partial.mean()),
            'independent_random_cut_std_error_m3':float(partial.std(ddof=1)/math.sqrt(len(partial))),
            'independent_random_full_m3':full_mean,
            'independent_random_full_std_error_m3':full_stderr}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--mesh',type=Path,required=True)
    p.add_argument('--selection-json',type=Path,required=True)
    p.add_argument('--samples',type=Path,required=True)
    p.add_argument('--algoim-root',type=Path,required=True)
    p.add_argument('--lapacke-include',type=Path,required=True)
    p.add_argument('--lapacke-lib',type=Path,required=True)
    p.add_argument('--lapack-lib',type=Path,required=True)
    p.add_argument('--blas-lib',type=Path,required=True)
    p.add_argument('--source',type=Path,default=Path('P10QB_M8_LOCAL_SINGLE_QUARTIC_ALGOIM.cpp'))
    p.add_argument('--binary',type=Path,default=Path('p10qb_m8_algoim_pilot'))
    p.add_argument('--output',type=Path,default=Path('P10QB_M8_LOCAL_ALGOIM_INDEPENDENT_QA.json'))
    p.add_argument('--log',type=Path,default=Path('P10QB_M8_LOCAL_ALGOIM_CASE_LOG.txt'))
    args=p.parse_args()
    if sha(args.mesh)!=m8.PINNED_M8_SHA256:
        raise SystemExit('P10QB_QA_STOP_M8_NOT_PINNED')
    selection=json.loads(args.selection_json.read_text(encoding='utf-8'))
    if selection['status']!='PASS_REAL_M8_SINGLE_QUARTIC_SELECTION' or selection['mesh_sha256']!=m8.PINNED_M8_SHA256:
        raise ValueError('unsafe sample selection')
    xyz,conn,ids,types,faces=m8.parse_msh(args.mesh)
    lookup={int(e):i for i,e in enumerate(ids)}
    cases=selection['cases']
    if len(cases)!=8:
        raise ValueError('expected eight genuine single-quartic cases')
    for c in cases:
        idx=lookup[c['original_element_id']]
        if idx!=c['mesh_tet_index']:
            raise ValueError('case original M8 element index inconsistent')
        ref=np.array(c['reference_vertices'])
        mids=.5*(ref[py.EDGES[:,0]]+ref[py.EDGES[:,1]])
        true_child=py.map_tet10_nodally(xyz[conn[idx]],np.concatenate((ref,mids))[None])[0]
        if np.max(np.abs(true_child-np.array(c['physical_child_nodes_10'])))>5e-16:
            raise ValueError('sampled child is not exact isoparametric restriction')
        status=c['constraints_status']
        if sum(v==0 for v in status)!=1 or status[c['quartic_constraint']]!=0 or any(
            v!=1 for j,v in enumerate(status) if j!=c['quartic_constraint']):
            raise ValueError('more than one boundary remains active')
    cmd=['g++','-std=c++20','-O2','-Wl,--gc-sections',
         '-I'+str(args.algoim_root.resolve()/'algoim'),
         '-I'+str(args.lapacke_include.resolve()),
         str(args.source.resolve()),str(args.lapacke_lib.resolve()),
         str(args.lapack_lib.resolve()),str(args.blas_lib.resolve()),
         '-lm','-o',str(args.binary.resolve())]
    build=subprocess.run(cmd,text=True,capture_output=True,timeout=120)
    if build.returncode:
        raise RuntimeError('C++20 real LAPACKE/Algoim build failed: '+build.stderr[-4000:])
    parent_jac=vol.jacobian_at_reference_vertices(xyz[conn])
    detc=vol.detj_bernstein_cubic_from_affine_jacobian(parent_jac)
    result=[]
    logs=[]
    for sample_index,c in enumerate(cases):
        proc=subprocess.run([str(args.binary.resolve()),str(args.samples.resolve()),
                             str(sample_index),'8'],capture_output=True,text=True,timeout=60)
        logs.append(f'=== P10QB CASE {sample_index} element={c["original_element_id"]} ===\n'+
                    proc.stdout+proc.stderr)
        if proc.returncode or 'P10QB_LOCAL_ALGOIM_PASS' not in proc.stdout:
            raise RuntimeError(f'true Algoim failed case {sample_index}: '+(proc.stdout+proc.stderr)[-4000:])
        records=[]
        for line in proc.stdout.splitlines():
            parsed=LINE.fullmatch(line)
            if parsed:
                eid,depth,which,q,cut,full,exact,rel,frac,points,active,weight=parsed.groups()
                rec={'element_id':int(eid),'depth':int(depth),'quartic':int(which),
                     'q':int(q),'cut_m3':float(cut),'full_m3':float(full),
                     'cpp_q4_full_m3':float(exact),'full_rel':float(rel),
                     'cut_fraction':float(frac),'points':int(points),
                     'active_points':int(active),'minimum_weight':float(weight)}
                if rec['element_id']!=c['original_element_id'] or rec['depth']!=c['depth'] or rec['quartic']!=c['quartic_constraint']:
                    raise ValueError('C++ worker not on chosen exact M8 child')
                if not 0<rec['cut_m3']<rec['cpp_q4_full_m3'] or rec['minimum_weight']<=0 or rec['points']>4000000:
                    raise ValueError('bad Algoim cut volume / weight / node count')
                records.append(rec)
        if [r['q'] for r in records]!=[2,3,4,6,8]:
            raise ValueError(f'incomplete q series for case {sample_index}')
        idx=c['mesh_tet_index']
        ref=np.array(c['reference_vertices'])
        geom_exact=float(vol.physical_volume_of_subcells(detc[idx],ref[None],c['depth'])[0])
        if abs(geom_exact-records[-1]['cpp_q4_full_m3'])/geom_exact>=2e-12:
            raise ValueError('independent exact child physical volume not reproduced')
        if records[-1]['full_rel']>=2e-8:
            raise ValueError('Algoim q8 failed to integrate full curved Tet10 subvolume')
        cut_delta=abs(records[-1]['cut_m3']-records[-2]['cut_m3'])/records[-1]['cut_m3']
        if cut_delta>=1e-3:
            raise ValueError('real cut volume q6/q8 not converged in pilot')
        rng=qmc_sanity_case(c,xyz[conn[idx]],parent_jac[idx],20261128+sample_index)
        cut_diff=abs(rng['independent_random_cut_m3']-records[-1]['cut_m3'])
        if cut_diff>6*rng['independent_random_cut_std_error_m3']+0.01*records[-1]['cut_m3']:
            raise ValueError('independent physical Monte Carlo contradicts real Algoim cut')
        if abs(rng['independent_random_full_m3']-geom_exact)>6*rng['independent_random_full_std_error_m3']+1e-4*geom_exact:
            raise ValueError('independent physical Monte Carlo full volume mismatch')
        case={'sample_index':sample_index,'original_element_id':c['original_element_id'],
              'radial_bin':c['radial_bin'],'mu_bin':c['mu_bin'],'phi_bin':c['phi_bin'],
              'quartic_constraint':c['quartic_constraint'],'depth':c['depth'],
              'exact_child_physical_volume_m3':geom_exact,
              'q6_q8_relative_cut_delta':cut_delta,'q8':records[-1],
              'independent_random_sanity':rng,'q_records':records}
        result.append(case)
        print(f'P10QB_REAL_M8_LOCAL_ALGOIM_CASE_PASS {sample_index+1}/8 '
              f'eid={c["original_element_id"]} quartic={c["quartic_constraint"]} '
              f'points_q8={records[-1]["points"]} q6_q8_rel={cut_delta:.6g}',flush=True)
    summary={'stage':'P10QB','status':'PASS_REAL_ALGOIM_LAPACKE_EIGHT_M8_SINGLE_QUARTIC_PILOTS',
             'mesh_sha256':sha(args.mesh),'mesh_changed':False,'fem_started':False,
             'gmsh_generated':False,'num_cases':len(result),
             'source_sha256':sha(args.source),'selection_sha256':sha(args.selection_json),
             'sample_txt_sha256':sha(args.samples),
             'algorithm':'Algoim ImplicitPolyQuadrature<3> one active physical quartic + affine reference simplex',
             'max_q':8,'independent_reference':'true original M8 cubic Bernstein detJ exact physical subvolume and random Dirichlet-sample cut check',
             'cases':result,'physical_4D_FEM_approved':False}
    args.output.write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    args.log.write_text('\n'.join(logs),encoding='utf-8')
    print('P10QB_REAL_M8_SINGLE_QUARTIC_ALGOIM_QA_PASS',flush=True)


if __name__=='__main__':
    try:
        main()
    except (RuntimeError,ValueError,subprocess.SubprocessError,OSError) as exc:
        print('P10QB_INDEPENDENT_QA_STOP',str(exc),file=sys.stderr)
        raise SystemExit(2)
