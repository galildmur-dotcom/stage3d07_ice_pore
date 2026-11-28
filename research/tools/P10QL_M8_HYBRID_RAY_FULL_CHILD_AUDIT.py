#!/usr/bin/env python3
"""P10QL: same true h=8 partition; sum independent ray-cut moments, L1 and signed.

Use no Algoim for the new moments. Algoim q8 from P10QK is a comparison
only. All true fully-inside P2/Tet10 contributions remain exact polynomials.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import time

from P10QL_M8_INDEPENDENT_RAY_CUT_QUADRATURE import RayChild
import P10PX_M8_CONSERVATIVE_TET10_TRIAGE as m8


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--mesh',type=Path,required=True)
    p.add_argument('--child-report',type=Path,required=True)
    p.add_argument('--algoim-report',type=Path,required=True)
    p.add_argument('--axis',type=int,default=2)
    p.add_argument('--orders',type=int,nargs='+',default=[16,32,64])
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    sha=hashlib.sha256(a.mesh.read_bytes()).hexdigest()
    h=json.loads(a.child_report.read_text())
    gl=json.loads(a.algoim_report.read_text())
    if sha!=m8.PINNED_M8_SHA256 or h['mesh_sha256']!=sha or gl['mesh_sha256']!=sha or \
       h['min_h_one']!=8 or gl['quadrature_strategy']!='gl' or \
       a.axis not in (0,1,2) or a.orders!=sorted(set(a.orders)) or \
       any(q<4 or q>256 for q in a.orders) or len(a.orders)<2:
        raise ValueError('P10QL_FULL_CHILD_WRONG_PIN_H_ORDER_OR_GL')
    ref=[p for p in gl['partitions'] if p['min_h_one']==8]
    if len(ref)!=1 or len(ref[0]['terminals'])!=len(h['terminals']):
        raise ValueError('P10QL_SOURCE_CELLS_NOT_SAME_H8_PARTITION')
    exact_inside=0.;ray_rows=[];gl8_total=ref[0]['q_total_gradient_m3_by_order']['8']
    order_sum={n:0. for n in a.orders}
    for i,(term,base) in enumerate(zip(h['terminals'],ref[0]['terminals'])):
        if term['group']!=base['group'] or term['h_depth']!=base['h_depth'] or base['index']!=i:
            raise ValueError('P10QL_MISMATCHED_ALGOIM_REAL_CHILD')
        if term['group']=='inside':
            exact_inside+=term['exact_full_gradient_m3'];continue
        ray=RayChild(term)
        row={'index':i,'group':term['group'],'h_depth':term['h_depth'],
             'active_boundaries':ray.active,
             'algoim_gl_q8_gradient_m3':base['q']['8']['cut_gradient_m3'],
             'orders':{}}
        full=ray.integrate(a.axis,8,cut=False)
        fullg=abs(full['cut_gradient_m3']-ray.exact_full_gradient)/max(abs(ray.exact_full_gradient),1e-25)
        fullv=abs(full['cut_volume_m3']-ray.exact_full_volume)/ray.exact_full_volume
        if max(fullg,fullv)>1e-10:
            raise ValueError('P10QL_FAILED_INDEPENDENT_FULL_CUBIC_GAUSS_CHECK')
        for n in a.orders:
            t0=time.monotonic();v=ray.integrate(a.axis,n)
            if v['cut_volume_m3']<-1e-25 or v['cut_volume_m3']>1.000000001*ray.exact_full_volume:
                raise ValueError('P10QL_RAY_CUT_VOLUME_INVALID')
            v['seconds']=time.monotonic()-t0
            row['orders'][str(n)]=v
            order_sum[n]+=v['cut_gradient_m3']
        ray_rows.append(row)
        if (len(ray_rows)%5==0) or i==len(h['terminals'])-1:
            print('P10QL_H8_PROGRESS cut=',len(ray_rows),'/',
                  ref[0]['group_counts']['one']+ref[0]['group_counts']['multi'],
                  'last_cell=',i,flush=True,sep='')
    qprev,qlast=a.orders[-2:]
    old=[];new=[];new_gl=[]
    for r in ray_rows:
        old.append(r['orders'][str(qprev)]['cut_gradient_m3'])
        new.append(r['orders'][str(qlast)]['cut_gradient_m3'])
        new_gl.append(r['algoim_gl_q8_gradient_m3'])
    dif=[b-a for a,b in zip(old,new)]
    contrast=[b-c for b,c in zip(new,new_gl)]
    final=exact_inside+sum(new)
    output={'stage':'P10QL','mesh_sha256':sha,'case4_original_element_id':6008,
            'status':'PILOT_INDEPENDENT_REAL_H8_RAY_CUT_Q_EXPERIMENT_NOT_CERTIFIED',
            'axis':a.axis,'transverse_Gauss_orders':a.orders,
            'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'ray_source_sha256':hashlib.sha256(Path('P10QL_M8_INDEPENDENT_RAY_CUT_QUADRATURE.py').read_bytes()).hexdigest(),
            'fully_inside_exact_gradient_m3':exact_inside,
            'ray_hybrid_gradient_m3_by_order':{str(n):exact_inside+order_sum[n] for n in a.orders},
            'algoim_gl_q8_hybrid_gradient_m3':gl8_total,
            'ray_last_order_vs_gl_q8_signed_m3':final-gl8_total,
            'ray_last_order_vs_gl_q8_L1_m3':sum(abs(x) for x in contrast),
            'ray_last_order_vs_gl_q8_L1_relative_to_ray_hybrid':sum(abs(x) for x in contrast)/max(abs(final),1e-25),
            'ray_q_previous_to_last_signed_m3':sum(dif),
            'ray_q_previous_to_last_L1_m3':sum(abs(x) for x in dif),
            'ray_q_previous_to_last_L1_relative_to_hybrid':sum(abs(x) for x in dif)/max(abs(final),1e-25),
            'geometric_multi_uncertainty_bernstein_m3':ref[0]['residual_multi_bernstein_enclosure_m3'],
            'q_changes_are_not_rigorous_error_bounds':True,
            'cut_full_4D_FEM_ready':False,'CAD_or_Gmsh_or_FEM_executed':False,
            'cells':ray_rows}
    a.output.write_text(json.dumps(output,indent=2)+'\n')
    print('P10QL_INDEPENDENT_FULL_H8_RAY_AUDIT_COMPLETE_NOT_CERTIFIED',flush=True)


if __name__=='__main__':main()
