#!/usr/bin/env python3
"""Actual Algoim AutoMixed vs AlwaysGL on six true h-sub-Tet10 M8 cuts.

Diagnostic comparison: exact full-polynomial check is NOT a cut-integral
accuracy certificate. Each integration runs in a resource-limited subprocess.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import resource
import subprocess

from P10QK_M8_RUN_HYBRID_H_AND_Q_INDEPENDENT_QA import ORDERS,RESULT_RE

CASES=(('CASE4_H8',0),('CASE4_H8',4),('CASE4_H8',9),
       ('CASE4_H8_ONE8',25),('CASE4_H8_ONE8',35),('CASE4_H8_ONE8',37))
WORKER=Path('p10qk_m8_hybrid_algoim_pilot')


def limits():
    resource.setrlimit(resource.RLIMIT_AS,(1_800_000_000,1_800_000_000))


def run_one(input_path,index,strategy):
    try:
        p=subprocess.run([str(WORKER.resolve()),str(input_path),str(index),
                          '8',strategy],capture_output=True,text=True,
                         timeout=20,preexec_fn=limits)
    except subprocess.TimeoutExpired:
        return {'error':'20_SECOND_WATCHDOG'}
    if p.returncode!=0 or 'P10QK_HYBRID_ONE_OR_TWO_REAL_M8_ALGOIM_PASS' not in p.stdout:
        return {'error':p.stderr[-300:],'returncode':p.returncode}
    values={}
    for line in p.stdout.splitlines():
        m=RESULT_RE.fullmatch(line)
        if not m:continue
        i,q,g,v,rg,rv,n,k,w=m.groups()
        if int(i)!=index:raise ValueError('P10QK_STRATEGY_WRONG_ELEMENT')
        values[int(q)]={'cut_gradient_m3':float(g),'cut_volume_m3':float(v),
                        'full_gradient_relative':float(rg),
                        'full_volume_relative':float(rv),
                        'points':int(n),'inside':int(k),'min_weight':float(w)}
    if tuple(sorted(values))!=ORDERS:raise ValueError('P10QK_MISSING_Q_ORDER')
    g6=values[6]['cut_gradient_m3'];g8=values[8]['cut_gradient_m3']
    return {'q_series':values,'delta_q6_q8_m3':g8-g6,
            'relative_cut_delta_q6_q8':abs(g8-g6)/max(abs(g8),1e-18),
            'full_q8_gradient_relative':values[8]['full_gradient_relative'],
            'full_q8_volume_relative':values[8]['full_volume_relative'],
            'full_q8_pass_1e_minus_10':values[8]['full_gradient_relative']<=1e-10 and
                                        values[8]['full_volume_relative']<=1e-10}


def main():
    if not WORKER.is_file():raise ValueError('P10QK_WORKER_NOT_COMPILED')
    allrows=[]
    for stem,index in CASES:
        inp=Path('P10QK_M8_HYBRID_GRADIENT_'+stem+'_INPUT.txt')
        audit=json.loads(Path('P10QK_M8_HYBRID_CHILDREN_'+stem+'_QA.json').read_text())
        if audit['worker_input_sha256']!=hashlib.sha256(inp.read_bytes()).hexdigest():
            raise ValueError('P10QK_STRATEGY_INPUT_SHA_MISMATCH')
        child=audit['terminals'][index]
        row={'input':inp.name,'child_index':index,'boundary_count':sum(v==0 for v in child['status']),
             'active_boundaries':[i for i,v in enumerate(child['status']) if v==0],
             'h_depth':child['h_depth'],'exact_full_gradient_m3':child['exact_full_gradient_m3'],
             'strategies':{}}
        for strategy in ('auto','gl'):
            result=run_one(inp,index,strategy)
            row['strategies'][strategy]=result
            print('P10QK_STRATEGY',stem,index,strategy,
                  'full_q8=',result.get('full_q8_gradient_relative'),
                  'cut_d68=',result.get('relative_cut_delta_q6_q8'),
                  'error=',result.get('error'),flush=True)
        a=row['strategies']['auto'];g=row['strategies']['gl']
        if 'q_series' in a and 'q_series' in g:
            row['q8_cut_strategy_delta_m3']=(
                g['q_series'][8]['cut_gradient_m3']-a['q_series'][8]['cut_gradient_m3'])
            row['q8_cut_strategy_delta_relative']=(abs(row['q8_cut_strategy_delta_m3'])/
                  max(abs(g['q_series'][8]['cut_gradient_m3']),1e-18))
        allrows.append(row)
    result={'stage':'P10QK','scope':'Genuine M8, auto vs GL, six real cuts',
            'quadrature':'Algoim ImplicitPolyQuadrature with true linked LAPACKE',
            'strategy_comparison_is_not_an_error_certificate':True,
            'physical_FEM_approved':False,'no_mesh_change':True,'cases':allrows}
    Path('P10QK_M8_ALGOIM_STRATEGY_CROSSCHECK_QA.json').write_text(
        json.dumps(result,indent=2)+'\n')
    print('P10QK_STRATEGY_CROSSCHECK_COMPLETE_NOT_CERTIFIED',flush=True)


if __name__=='__main__':main()
