#!/usr/bin/env python3
"""Stage3D07 LIT-08C: Q3 pointwise B6 indicator identity at r = 6 mm.

Geometry-only audit on existing MSH2 Tet10 meshes. No FEM/state/history/adjoints.
Requires numpy and adjacent lit06_b20_geometry_audit.py for verified MSH2, Q3 D.
"""
from __future__ import annotations

import argparse
import csv
import math
import sys
import time
from pathlib import Path

import numpy as np
import lit06_b20_geometry_audit as old

CENTER = np.array([0., 0., 0.03], dtype=np.float64)
R6 = 0.006
RMIN = 0.00599
RMAX = 0.00601
EDGES = ((0,1),(1,2),(2,0),(0,3),(1,3),(2,3))
EXPECTED = {
    'W4B2': {'sha': '3f6bf10717e566c5268e0b716e13c887365e0d3c61e46c156fdbe6ba1aa3d2c7',
             'qp': 6490017, 'n_inner': 6319, 'n_outer': 4779,
             'volume': 9.0058152823446181e-7},
    'W4B20': {'sha': '94ab3df693265dbb4e7e723eb3c54642f4c385a465d91a1db4436ab66adc6715',
             'qp': 8163720, 'n_inner': 6598, 'n_outer': 4711,
             'volume': 9.0058152257345157e-7},
}
COLUMNS = ['mesh','mesh_sha256','node_count','tet10_count','selected_tet10',
    'centroid_selected_Q3','radius6_selected_Q3','symmetric_difference_Q3',
    'centroid_only_Q3','radius_only_Q3','mixed_Q3_elements',
    'V_centroid_m3','V_radius6_m3','V_symdiff_m3','V_radius_minus_centroid_m3',
    'qp_inner_shell_5p99_to_6p00','qp_outer_shell_6p00_to_6p01',
    'V_inner_shell_m3','V_outer_shell_m3','min_abs_distance_to_r6_m',
    'nonpositive_detJ_Q3','wall_s']


def qp_shape_and_geometry():
    Ns = []
    for a, _ in old.GAUSS3:
        for b, _ in old.GAUSS3:
            for c, _ in old.GAUSS3:
                r = a
                s = (1-r)*b
                t = (1-r)*(1-b)*c
                L = np.array([1-r-s-t, r, s, t])
                N = np.empty(10, dtype=np.float64)
                for i in range(4):
                    N[i] = L[i]*(2*L[i]-1)
                for j, (i,k) in enumerate(EDGES):
                    N[4+j] = 4*L[i]*L[k]
                Ns.append(N)
    w, d = old.tet_quadrature()
    N = np.array(Ns, dtype=np.float64).T
    assert N.shape == (10,27) and d.shape == (10,27,3)
    if not np.allclose(N.sum(axis=0),1,atol=1e-15):
        raise AssertionError('Q3 Tet10 N partition of unity failed')
    return w, N, d


def geometry_audit(nodes, tets, chunk=1600):
    w,N,d = qp_shape_and_geometry()
    integer = ['selected_tet10','centroid_selected_Q3','radius6_selected_Q3',
               'symmetric_difference_Q3','centroid_only_Q3','radius_only_Q3',
               'mixed_Q3_elements','qp_inner_shell_5p99_to_6p00',
               'qp_outer_shell_6p00_to_6p01','nonpositive_detJ_Q3']
    volume = ['V_centroid_m3','V_radius6_m3','V_symdiff_m3',
              'V_radius_minus_centroid_m3','V_inner_shell_m3','V_outer_shell_m3']
    total = dict.fromkeys(integer,0)
    total.update(dict.fromkeys(volume,0.0))
    total['min_abs_distance_to_r6_m'] = float('inf')
    total['node_count'] = len(nodes)
    total['tet10_count'] = len(tets)
    for begin in range(0,len(tets),chunk):
        ix = tets[begin:begin+chunk]
        X = nodes[ix]
        cent = np.linalg.norm(X[:,:4,:].mean(axis=1)-CENTER,axis=1)<R6
        P = np.einsum('eic,iq->eqc', X, N,optimize=True)
        rq = np.linalg.norm(P-CENTER,axis=2)
        qsel = rq<R6
        csel = np.broadcast_to(cent[:,None],qsel.shape)
        c_only = csel & ~qsel
        q_only = qsel & ~csel
        sx = c_only | q_only
        inner = (rq>=RMIN)&(rq<R6)
        outer = (rq>=R6)&(rq<RMAX)
        total['selected_tet10'] += int(cent.sum())
        total['centroid_selected_Q3'] += int(csel.sum())
        total['radius6_selected_Q3'] += int(qsel.sum())
        total['centroid_only_Q3'] += int(c_only.sum())
        total['radius_only_Q3'] += int(q_only.sum())
        total['symmetric_difference_Q3'] += int(sx.sum())
        total['mixed_Q3_elements'] += int(np.count_nonzero(qsel.any(axis=1)&~qsel.all(axis=1)))
        total['qp_inner_shell_5p99_to_6p00'] += int(inner.sum())
        total['qp_outer_shell_6p00_to_6p01'] += int(outer.sum())
        total['min_abs_distance_to_r6_m'] = min(total['min_abs_distance_to_r6_m'],float(np.min(np.abs(rq-R6))))
        grads = [np.einsum('eic,iq->eqc',X,d[:,:,k],optimize=True) for k in range(3)]
        jac = np.einsum('eqc,eqc->eq',grads[0],np.cross(grads[1],grads[2]))
        total['nonpositive_detJ_Q3'] += int(np.count_nonzero(jac<=0))
        weights = jac*w[None,:]
        for field,which in [('V_centroid_m3',csel),('V_radius6_m3',qsel),
                ('V_symdiff_m3',sx),('V_inner_shell_m3',inner),('V_outer_shell_m3',outer)]:
            total[field] += float(np.sum(weights,where=which))
        total['V_radius_minus_centroid_m3'] += float(np.sum(weights,where=q_only)-np.sum(weights,where=c_only))
    if total['nonpositive_detJ_Q3']:
        raise ValueError('Nonpositive Q3 Jacobian detected')
    if total['centroid_only_Q3']+total['radius_only_Q3']!=total['symmetric_difference_Q3']:
        raise AssertionError('mask XOR partition mismatch')
    if total['centroid_selected_Q3'] != 27*total['selected_tet10']:
        raise AssertionError('centroid count inconsistent')
    return total


def selftest():
    old.selftest()
    base=np.array([[.002,0,.03],[.0021,0,.03],[.002,.0001,.03],[.002,0,.0301]],float)
    X=np.vstack([base,[(base[i]+base[k])/2 for i,k in EDGES]])
    t=np.array([np.arange(10)],np.int32)
    a=geometry_audit(X,t)
    assert a['selected_tet10']==1 and a['centroid_selected_Q3']==27
    assert a['radius6_selected_Q3']==27 and a['symmetric_difference_Q3']==0
    assert abs(a['V_centroid_m3']-1e-12/6)<1e-23
    B=X+np.array([.00395,0.,0.])
    b=geometry_audit(B,t)
    assert b['symmetric_difference_Q3']>0 and b['nonpositive_detJ_Q3']==0,b
    assert b['symmetric_difference_Q3']==b['centroid_only_Q3']+b['radius_only_Q3']
    print('LIT08C_SELFTEST_OK exact_mask_identity=1 crossing_mask_XOR=1 volume_Q3=1',flush=True)


def main():
    p=argparse.ArgumentParser(description='LIT08C: geometric comparison of centroid-B6 and radius-Q3 B6 indicators, no FEM')
    p.add_argument('--repo',default=r'G:\ildar\Stage3D07')
    p.add_argument('--out',default=None)
    p.add_argument('--selftest',action='store_true')
    opt=p.parse_args()
    selftest()
    if opt.selftest:return
    repo=Path(opt.repo)
    meshes={k:repo/'P10M_MESHES'/v for k,v in [('W4B2','H4W4B2.msh'),('W4B20','H4W4B20_P10AB.msh')]}
    for k,pth in meshes.items():
        if not pth.is_file():raise FileNotFoundError(f'Mesh missing: {k}: {pth}')
    out=Path(opt.out) if opt.out else (repo/'LOCAL_RUNS'/'LIT08C_B6_MASK_IDENTITY_20261116')
    if out.exists():raise FileExistsError(f'Choose a NEW output folder: {out}')
    results=[]
    for k,pth in meshes.items():
        start=time.perf_counter()
        digest=old.sha256(pth)
        if digest!=EXPECTED[k]['sha']:
            raise ValueError(f'{k} mesh SHA256 mismatch: {digest}; expected {EXPECTED[k]["sha"]}')
        x,t,f=old.read_msh2(pth)
        result=geometry_audit(x,t)
        result.update(mesh=k,mesh_sha256=digest,wall_s=round(time.perf_counter()-start,3))
        expect=EXPECTED[k]
        for nm,v in [('centroid_selected_Q3',expect['qp']),('qp_inner_shell_5p99_to_6p00',expect['n_inner']),('qp_outer_shell_6p00_to_6p01',expect['n_outer'])]:
            if result[nm]!=v:raise ValueError(f'{k} {nm}: {result[nm]}, expected {v}')
        if abs(result['V_centroid_m3']-expect['volume'])>1e-11*expect['volume']:
            raise ValueError(f'{k} baseline B6 Q3 volume mismatch: {result["V_centroid_m3"]}, expected {expect["volume"]}')
        results.append(result)
        print('LIT08C_MESH_OK',k,'centroid_QP',result['centroid_selected_Q3'],
              'qp_radius_QP',result['radius6_selected_Q3'],
              'xor_QP',result['symmetric_difference_Q3'],
              'xor_volume_m3',result['V_symdiff_m3'],
              'wall_s',result['wall_s'],flush=True)
    out.mkdir(parents=True,exist_ok=False)
    path=out/'LIT08C_B6_MASK_IDENTITY.csv'
    with open(path,'w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=['mesh','mesh_sha256','node_count','tet10_count',*COLUMNS[4:]])
        w.writeheader();w.writerows(results)
    print('LIT08C_MASK_IDENTITY_OK file='+str(path),flush=True)

if __name__=='__main__':
    try:main()
    except Exception as ex:
        print('LIT08C_STOP',type(ex).__name__,str(ex),file=sys.stderr)
        sys.exit(2)
