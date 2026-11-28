#!/usr/bin/env python3
"""Independent C++20/LAPACKE/Algoim q=2..8 QA for eight curved M8 quadratics.

Cross-checks each pulled-back child against original M8, exact Bernstein
physical volume, and independently sampled signed sector membership.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

import numpy as np

import P10PX_M8_CONSERVATIVE_TET10_TRIAGE as m8
import P10PY_M8_BEZIER_ADAPTIVE_PREFILTER as py
import P10QA_M8_PHYSICAL_CUT_VOLUME_BRACKETS as vol
import P10QB_M8_LOCAL_ALGOIM_INDEPENDENT_QA as qb


LINE=re.compile(
    r'^P10QC_LOCAL_ALGOIM element=(\d+) depth=(\d+) quadratic=(\d+) q=(\d+) '
    r'cut_m3=([\deE+.-]+) full_m3=([\deE+.-]+) exact_m3=([\deE+.-]+) '
    r'full_rel=([\deE+.-]+) cut_frac=([\deE+.-]+) points=(\d+) '
    r'active_points=(\d+) min_weight=([\deE+.-]+)$'
)


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--mesh',type=Path,required=True)
    p.add_argument('--selection',type=Path,required=True)
    p.add_argument('--samples',type=Path,required=True)
    p.add_argument('--algoim-root',type=Path,required=True)
    p.add_argument('--lapacke-include',type=Path,required=True)
    p.add_argument('--lapacke-lib',type=Path,required=True)
    p.add_argument('--lapack-lib',type=Path,required=True)
    p.add_argument('--blas-lib',type=Path,required=True)
    p.add_argument('--source',type=Path,default=Path('P10QC_M8_LOCAL_QUADRATIC_ALGOIM.cpp'))
    p.add_argument('--binary',type=Path,default=Path('p10qc_m8_quadratic_pilot'))
    p.add_argument('--output',type=Path,default=Path('P10QC_M8_QUADRATIC_ALGOIM_INDEPENDENT_QA.json'))
    p.add_argument('--log',type=Path,default=Path('P10QC_M8_QUADRATIC_ALGOIM_CASE_LOG.txt'))
    args=p.parse_args()
    source=json.loads(args.selection.read_text(encoding='utf-8'))
    digest=sha(args.mesh)
    if (digest!=m8.PINNED_M8_SHA256 or source['mesh_sha256']!=digest or
        source['status']!='PASS_REAL_M8_SINGLE_QUADRATIC_SELECTION'):
        raise ValueError('M8/quadratic selection not accepted')
    if len(source['cases'])!=8:
        raise ValueError('expected eight real curved quadratic children')
    xyz,conn,ids,types,faces=m8.parse_msh(args.mesh)
    index={int(e):i for i,e in enumerate(ids)}
    X=xyz[conn]
    jac=vol.jacobian_at_reference_vertices(X)
    controls=vol.detj_bernstein_cubic_from_affine_jacobian(jac)
    for c in source['cases']:
        e=index[c['original_element_id']]
        if e!=c['mesh_tet_index']:
            raise ValueError('M8 element index mismatch')
        ref=np.array(c['reference_vertices'])
        mids=.5*(ref[py.EDGES[:,0]]+ref[py.EDGES[:,1]])
        actual=py.map_tet10_nodally(X[e],np.vstack((ref,mids))[None])[0]
        if np.max(np.abs(actual-np.array(c['physical_child_nodes_10'])))>5e-16:
            raise ValueError('not a true M8 curved restriction')
        status=c['constraints_status']
        active=c['quadratic_constraint']
        if active not in (2,4,5) or status[active]!=0 or any(
           v!=1 for k,v in enumerate(status) if k!=active):
            raise ValueError('one-active-quadratic certificate invalid')
    cmd=['g++','-std=c++20','-O2','-Wl,--gc-sections',
         '-I'+str(args.algoim_root.resolve()/'algoim'),
         '-I'+str(args.lapacke_include.resolve()),
         str(args.source.resolve()),str(args.lapacke_lib.resolve()),
         str(args.lapack_lib.resolve()),str(args.blas_lib.resolve()),
         '-lm','-o',str(args.binary.resolve())]
    build=subprocess.run(cmd,text=True,capture_output=True,timeout=120)
    if build.returncode:
        raise RuntimeError('C++20/Algoim build failed: '+build.stderr[-3000:])
    cases=[];logs=[]
    for num,c in enumerate(source['cases']):
        run=subprocess.run([str(args.binary.resolve()),str(args.samples.resolve()),
                            str(num),'8'],capture_output=True,text=True,timeout=45)
        logs.append(f'=== P10QC quadratic case {num} ===\n'+run.stdout+run.stderr)
        if run.returncode or 'P10QC_LOCAL_QUADRATIC_ALGOIM_PASS' not in run.stdout:
            raise RuntimeError(f'failed real quadratic {num}: '+(run.stdout+run.stderr)[-3500:])
        rows=[]
        for line in run.stdout.splitlines():
            m=LINE.match(line)
            if not m:continue
            eid,depth,active,q,cut,full,exact,rel,frac,points,activep,w=m.groups()
            row={'element_id':int(eid),'depth':int(depth),'quadratic_constraint':int(active),
                 'q':int(q),'cut_m3':float(cut),'full_m3':float(full),
                 'cpp_exact_full_m3':float(exact),'full_rel':float(rel),
                 'cut_fraction':float(frac),'points':int(points),
                 'active_points':int(activep),'min_weight':float(w)}
            if row['element_id']!=c['original_element_id'] or row['quadratic_constraint']!=c['quadratic_constraint']:
                raise ValueError('quadratic worker used wrong physical case')
            if row['min_weight']<=0 or row['points']>2000000:
                raise ValueError('bad quadratic scheme weights / size')
            rows.append(row)
        if [r['q'] for r in rows]!=[2,3,4,6,8]:
            raise ValueError('quadratic q-series incomplete')
        e=c['mesh_tet_index'];ref=np.array(c['reference_vertices'])
        exact=float(vol.physical_volume_of_subcells(controls[e],ref[None],c['depth'])[0])
        if abs(rows[-1]['cpp_exact_full_m3']-exact)/exact>2e-12 or rows[-1]['full_rel']>2e-8:
            raise ValueError('exact original-M8 physical Jacobian volume mismatch')
        diff=abs(rows[-1]['cut_m3']-rows[-2]['cut_m3'])/rows[-1]['cut_m3']
        if diff>1e-4:
            raise ValueError('q6→q8 local quadratic cut not stable')
        random_case={**c,'quartic_constraint':c['quadratic_constraint']}
        random_result=qb.qmc_sanity_case(random_case,X[e],jac[e],20261128+num)
        std=random_result['independent_random_cut_std_error_m3']
        delta=abs(random_result['independent_random_cut_m3']-rows[-1]['cut_m3'])
        if delta>6*std+.01*rows[-1]['cut_m3']:
            raise ValueError('independent Monte Carlo contradicts quadratic cut')
        cases.append({'sample_index':num,'original_element_id':c['original_element_id'],
                      'radial_bin':c['radial_bin'],'mu_bin':c['mu_bin'],'phi_bin':c['phi_bin'],
                      'quadratic_constraint':c['quadratic_constraint'],'depth':c['depth'],
                      'exact_child_physical_volume_m3':exact,
                      'q6_q8_relative_cut_delta':diff,'q8':rows[-1],
                      'independent_random_sanity':random_result,'q_records':rows})
        print(f'P10QC_QUADRATIC_ALGOIM_PASS {num+1}/8 '
              f'eid={c["original_element_id"]} active={c["quadratic_constraint"]} '
              f'q8_points={rows[-1]["points"]} q6q8={diff:.4g}',flush=True)
    result={'stage':'P10QC','status':'PASS_EIGHT_REAL_M8_QUADRATIC_ALGOIM_LAPACKE_PILOTS',
            'mesh_sha256':digest,'mesh_changed':False,'gmsh_generated':False,
            'fem_started':False,'selection_sha256':sha(args.selection),
            'source_sha256':sha(args.source),'cases':cases,
            'max_q':8,'num_cases':len(cases),'no_global_4D_FEM_approval':True}
    args.output.write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    args.log.write_text('\n'.join(logs),encoding='utf-8')
    print('P10QC_EIGHT_REAL_QUADRATIC_ALGOIM_QA_PASS',flush=True)


if __name__=='__main__':
    try:main()
    except (RuntimeError,ValueError,subprocess.SubprocessError,OSError) as exc:
        print('P10QC_QUADRATIC_QA_STOP',exc,file=sys.stderr)
        raise SystemExit(2)
